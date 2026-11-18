defmodule Api.Boreholes.Checks do
  @moduledoc """
  Plausibility checks of a borehole (ADR-0006), run after create and after every edit.

  `sync/1` keeps the open `origin: "rule"` flags of its own codes (below) in line with what is
  wrong now: it opens flags for new findings, resolves (`resolved_by: "rule"`) those that no
  longer apply and leaves still-firing ones alone. Flags of other origins or codes (e.g.
  `epsg_guessed` from the pipeline) are never touched. A finding a human confirmed
  (`POST /api/flags/:id/resolve`) is not reopened until that value is edited again.

  Codes: `no_layers`, `layer_gap`, `layer_overlap`, `total_depth_mismatch`,
  `groundwater_below_bottom`, `missing_elevation`, `missing_location`, `missing_petrography`.
  """

  import Ecto.Query

  alias Api.Boreholes.{Borehole, BoreholeLayer, FieldEdit, FieldFlag}
  alias Api.Repo

  @codes ~w(no_layers layer_gap layer_overlap total_depth_mismatch groundwater_below_bottom
            missing_elevation missing_location missing_petrography)
  # metres: gaps and overlaps below this are rounding, 5 cm for the total depth
  @tolerance 0.01
  @depth_tolerance 0.05

  @doc "The codes this module keeps in sync."
  def codes, do: @codes

  @doc "Syncs the rule flags of one borehole (see the moduledoc)."
  def sync(borehole_id) do
    borehole = Repo.get!(Borehole, borehole_id)

    layers =
      from(l in BoreholeLayer,
        where: l.borehole_id == ^borehole_id,
        order_by: [asc: l.depth_from_m, asc: l.depth_to_m, asc: l.id]
      )
      |> Repo.all()

    findings = borehole |> findings(layers) |> Map.new(&{key(&1), &1})

    flags =
      from(f in FieldFlag,
        where: f.borehole_id == ^borehole_id and f.origin == "rule" and f.code in ^@codes
      )
      |> Repo.all()

    {open, resolved} = Enum.split_with(flags, &is_nil(&1.resolved_at))
    open_keys = MapSet.new(open, &key/1)
    suppressed = suppressed_keys(borehole_id, resolved)

    stale = for f <- open, not Map.has_key?(findings, key(f)), do: f.id
    now = DateTime.utc_now()

    if stale != [] do
      from(f in FieldFlag, where: f.id in ^stale)
      |> Repo.update_all(set: [resolved_at: now, resolved_by: "rule", updated_at: now])
    end

    rows =
      for {key, finding} <- findings,
          not MapSet.member?(open_keys, key),
          not MapSet.member?(suppressed, key) do
        Map.merge(finding, %{
          id: Ecto.UUID.generate(),
          borehole_id: borehole_id,
          origin: "rule",
          inserted_at: now,
          updated_at: now
        })
      end

    Repo.insert_all(FieldFlag, rows)
    :ok
  end

  defp key(%{code: code, layer_id: layer_id, field: field}), do: {code, layer_id, field}

  # Keys a human confirmed and nobody edited since.
  defp suppressed_keys(borehole_id, resolved) do
    confirmed = Enum.filter(resolved, &(&1.resolved_by == "human"))

    if confirmed == [] do
      MapSet.new()
    else
      last_edit =
        from(e in FieldEdit,
          where: e.borehole_id == ^borehole_id,
          group_by: [e.layer_id, e.field],
          select: {{e.layer_id, e.field}, max(e.inserted_at)}
        )
        |> Repo.all()
        |> Map.new()

      confirmed
      |> Enum.filter(fn f ->
        edited = Map.get(last_edit, {f.layer_id, f.field})
        is_nil(edited) or DateTime.compare(edited, f.resolved_at) != :gt
      end)
      |> MapSet.new(&key/1)
    end
  end

  defp findings(borehole, layers) do
    total = number(borehole.total_depth_m)
    bottom = layers |> Enum.map(&number(&1.depth_to_m)) |> Enum.max(fn -> nil end)

    ([
       if(layers == [],
         do: finding("no_layers", "layer", nil, "error", "The borehole has no layers")
       ),
       if(is_nil(borehole.elevation_m),
         do: finding("missing_elevation", "elevation_m", nil, "warning", "Elevation is missing")
       ),
       if(is_nil(borehole.location),
         do: finding("missing_location", "location", nil, "warning", "Location is missing")
       ),
       if(total && bottom && abs(total - bottom) > @depth_tolerance,
         do:
           finding(
             "total_depth_mismatch",
             "total_depth_m",
             nil,
             "warning",
             "Total depth #{total} m differs from the bottom of the last layer (#{bottom} m)"
           )
       ),
       groundwater_finding(number(borehole.groundwater_level_m), total || bottom)
     ] ++
       layer_pair_findings(layers) ++
       Enum.flat_map(layers, &petrography_finding/1))
    |> Enum.reject(&is_nil/1)
  end

  defp groundwater_finding(level, bottom) when is_number(level) and is_number(bottom) do
    if level > bottom,
      do:
        finding(
          "groundwater_below_bottom",
          "groundwater_level_m",
          nil,
          "error",
          "Groundwater level #{level} m is below the bottom of the borehole (#{bottom} m)"
        )
  end

  defp groundwater_finding(_level, _bottom), do: nil

  defp layer_pair_findings(layers) do
    layers
    |> Enum.chunk_every(2, 1, :discard)
    |> Enum.map(fn [above, below] ->
      gap = number(below.depth_from_m) - number(above.depth_to_m)

      cond do
        gap > @tolerance ->
          finding(
            "layer_gap",
            "depth_from_m",
            below.id,
            "warning",
            "Gap of #{Float.round(gap, 2)} m above this layer (previous layer ends at #{number(above.depth_to_m)} m)"
          )

        gap < -@tolerance ->
          finding(
            "layer_overlap",
            "depth_from_m",
            below.id,
            "error",
            "Overlaps the layer above by #{Float.round(-gap, 2)} m (it ends at #{number(above.depth_to_m)} m)"
          )

        true ->
          nil
      end
    end)
  end

  defp petrography_finding(%BoreholeLayer{petrography: nil} = layer) do
    original = layer.metadata["petrography_original"]
    suffix = if original, do: ", the document says #{inspect(original)}", else: ""

    [
      finding(
        "missing_petrography",
        "petrography",
        layer.id,
        "warning",
        "Petrography is missing#{suffix}"
      )
    ]
  end

  defp petrography_finding(_layer), do: []

  defp finding(code, field, layer_id, severity, message),
    do: %{code: code, field: field, layer_id: layer_id, severity: severity, message: message}

  defp number(nil), do: nil
  defp number(%Decimal{} = d), do: Decimal.to_float(d)
  defp number(n) when is_number(n), do: n
end
