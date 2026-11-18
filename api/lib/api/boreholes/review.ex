defmodule Api.Boreholes.Review do
  @moduledoc """
  Editing and review of boreholes (ADR-0006): human edits with their history, revert, flags
  and verification, plus the flags/edits a pipeline run posts with a new borehole.

  Every write runs in one transaction and ends the same way: layer positions are renumbered by
  depth, `Api.Boreholes.Checks.sync/1` runs, and the result is the borehole like
  `Api.Boreholes.get_borehole/1`. A human edit writes one `field_edits` row per field that
  actually changed and resolves the open flags on that field first.

  History values: decimals are numbers, dates ISO 8601 strings, `location` a
  `{"x", "y", "epsg"}` (what was written, in the source CRS; the old location of a first edit is
  `epsg` 4326), `layer` a map of the layer's fields (no id, no position).
  """

  import Ecto.Query

  alias Api.Boreholes
  alias Api.Boreholes.{Borehole, BoreholeLayer, Checks, FieldEdit, FieldFlag}
  alias Api.Repo

  @type result :: {:ok, Borehole.t()} | {:error, :not_found | String.t() | Ecto.Changeset.t()}

  @layer_snapshot [:metadata, :source | BoreholeLayer.editable()]

  # -- Human edits ---------------------------------------------------------------------------

  @doc """
  Edits borehole fields (`Api.Boreholes.Borehole.editable/0`). `x`, `y` and `epsg` together
  replace the location like on create.
  """
  @spec update_borehole(String.t(), map()) :: result()
  def update_borehole(id, attrs) do
    attrs = stringify(attrs)

    write(id, fn borehole ->
      changeset = Borehole.edit_changeset(borehole, attrs)

      with :ok <- check_coordinates(attrs),
           {:ok, _} <- Repo.update(changeset) do
        edits =
          for {field, new} <- changeset.changes,
              do: {Atom.to_string(field), json(Map.get(borehole, field)), json(new)}

        Boreholes.set_location(borehole, attrs)
        new_value = Map.new(~w(x y epsg), &{&1, attrs[&1]})
        location = current_location(borehole.id)

        record(borehole.id, nil, edits ++ location_edit(borehole.location, location, new_value))
      else
        {:error, %Ecto.Changeset{} = changeset} -> {:error, changeset}
        {:error, message} -> {:error, message}
      end
    end)
  end

  @doc "Adds a layer (`depth_from_m`, `depth_to_m` and optionally the other layer fields)."
  @spec create_layer(String.t(), map()) :: result()
  def create_layer(id, attrs), do: write(id, &insert_layer(&1, nil, attrs))

  @doc "Edits layer fields (`Api.Boreholes.BoreholeLayer.editable/0`)."
  @spec update_layer(String.t(), String.t(), map()) :: result()
  def update_layer(id, layer_id, attrs) do
    write(id, fn borehole ->
      with {:ok, layer} <- fetch_layer(borehole, layer_id) do
        changeset = BoreholeLayer.edit_changeset(layer, stringify(attrs))

        with {:ok, _} <- Repo.update(changeset) do
          record(
            borehole.id,
            layer.id,
            for(
              {field, new} <- changeset.changes,
              do: {Atom.to_string(field), json(Map.get(layer, field)), json(new)}
            )
          )
        end
      end
    end)
  end

  @doc "Deletes a layer; its open flags go with it."
  @spec delete_layer(String.t(), String.t()) :: result()
  def delete_layer(id, layer_id) do
    write(id, fn borehole ->
      with {:ok, layer} <- fetch_layer(borehole, layer_id) do
        Repo.delete!(layer)
        record(borehole.id, layer.id, [{"layer", snapshot(layer), nil}])
      end
    end)
  end

  @doc """
  Undoes an edit by writing its `old_value` back as a new human edit. A deleted layer is
  re-inserted with its old id, a created layer is deleted again.
  """
  @spec revert_edit(String.t(), String.t()) :: result()
  def revert_edit(id, edit_id) do
    write(id, fn borehole ->
      with {:ok, edit} <- fetch_edit(borehole, edit_id) do
        revert(borehole, edit)
      end
    end)
  end

  defp revert(borehole, %FieldEdit{field: "layer", old_value: old, layer_id: layer_id} = edit)
       when is_map(old) do
    if is_nil(edit.new_value),
      do: insert_layer(borehole, layer_id, old),
      else: {:error, "this layer edit cannot be reverted"}
  end

  defp revert(borehole, %FieldEdit{field: "layer", layer_id: layer_id}) do
    with {:ok, layer} <- fetch_layer(borehole, layer_id) do
      Repo.delete!(layer)
      record(borehole.id, layer.id, [{"layer", snapshot(layer), nil}])
    end
  end

  defp revert(borehole, %FieldEdit{field: "location", old_value: old}) do
    case old do
      %{"x" => _, "y" => _, "epsg" => _} -> Boreholes.set_location(borehole, old)
      _ -> Repo.update_all(from(b in Borehole, where: b.id == ^borehole.id), set: [location: nil])
    end

    record(borehole.id, nil, location_edit(borehole.location, current_location(borehole.id), old))
  end

  defp revert(borehole, %FieldEdit{layer_id: nil, field: field, old_value: old}),
    do: apply_edit(borehole, nil, field, old)

  defp revert(borehole, %FieldEdit{layer_id: layer_id, field: field, old_value: old}) do
    with {:ok, layer} <- fetch_layer(borehole, layer_id),
         do: apply_edit(layer, layer_id, field, old)
  end

  # the one field of a borehole or layer, through the same changeset as a plain edit
  defp apply_edit(%Borehole{} = borehole, nil, field, value) do
    changeset = Borehole.edit_changeset(borehole, %{field => value})
    save_edit(changeset, borehole, borehole.id, nil)
  end

  defp apply_edit(%BoreholeLayer{} = layer, layer_id, field, value) do
    changeset = BoreholeLayer.edit_changeset(layer, %{field => value})
    save_edit(changeset, layer, layer.borehole_id, layer_id)
  end

  defp save_edit(changeset, current, borehole_id, layer_id) do
    with {:ok, _} <- Repo.update(changeset) do
      record(
        borehole_id,
        layer_id,
        for(
          {field, new} <- changeset.changes,
          do: {Atom.to_string(field), json(Map.get(current, field)), json(new)}
        )
      )
    end
  end

  defp insert_layer(borehole, id, attrs) do
    attrs = attrs |> stringify() |> Map.put("position", 0)

    changeset =
      %BoreholeLayer{id: id, borehole_id: borehole.id}
      |> BoreholeLayer.changeset(attrs)
      |> Ecto.Changeset.unique_constraint(:id, name: :borehole_layers_pkey)

    with {:ok, layer} <- Repo.insert(changeset) do
      record(borehole.id, layer.id, [{"layer", nil, snapshot(layer)}])
    end
  end

  # -- Flags and verification ----------------------------------------------------------------

  @doc "A human confirms the value of an open flag (\"looks right\"). `nil` if there is no such open flag."
  @spec resolve_flag(String.t()) :: result()
  def resolve_flag(flag_id) do
    with {:ok, uuid} <- Ecto.UUID.cast(flag_id),
         %FieldFlag{resolved_at: nil} = flag <- Repo.get(FieldFlag, uuid) do
      resolve(flag)
      {:ok, Boreholes.get_borehole(flag.borehole_id)}
    else
      %FieldFlag{} -> {:error, {:conflict, "the flag is already resolved"}}
      _ -> {:error, :not_found}
    end
  end

  defp resolve(%FieldFlag{id: id}) do
    now = DateTime.utc_now()

    from(f in FieldFlag, where: f.id == ^id)
    |> Repo.update_all(set: [resolved_at: now, resolved_by: "human", updated_at: now])
  end

  @doc "Sets (`true`) or clears (`false`) the verification of a borehole."
  @spec set_verified(String.t(), boolean()) :: result()
  def set_verified(id, verified) when is_boolean(verified) do
    with {:ok, borehole} <- fetch_borehole(id) do
      verified_at = if verified, do: DateTime.utc_now(:second)

      borehole
      |> Ecto.Changeset.change(verified: verified, verified_at: verified_at)
      |> Repo.update!()

      {:ok, Boreholes.get_borehole(borehole.id)}
    end
  end

  # -- Pipeline: flags and validator edits of a new borehole ----------------------------------

  @doc """
  Stores the `flags` and `edits` (validator corrections) a pipeline run posts with a new
  borehole. `layers` are the inserted layers; items refer to them by `layer_position`
  (`nil` or absent: a borehole-level field).
  """
  @spec insert_pipeline_extras(Borehole.t(), [BoreholeLayer.t()], term(), term()) ::
          :ok | {:error, String.t() | Ecto.Changeset.t()}
  def insert_pipeline_extras(borehole, layers, flags, edits) do
    by_position = Map.new(layers, &{&1.position, &1.id})

    with :ok <-
           insert_each(flags, "flags", by_position, fn item, layer_id ->
             FieldFlag.changeset(%FieldFlag{borehole_id: borehole.id, layer_id: layer_id}, item)
           end) do
      insert_each(edits, "edits", by_position, fn item, layer_id ->
        FieldEdit.changeset(
          %FieldEdit{borehole_id: borehole.id, layer_id: layer_id, source: "validator"},
          item
        )
      end)
    end
  end

  defp insert_each(nil, _name, _by_position, _build), do: :ok

  defp insert_each(items, name, by_position, build) when is_list(items) do
    items
    |> Enum.with_index()
    |> Enum.reduce_while(:ok, fn {item, index}, :ok ->
      with true <- is_map(item) or {:error, "#{name}[#{index}] must be an object"},
           {:ok, layer_id} <- layer_id(item["layer_position"], by_position, "#{name}[#{index}]"),
           {:ok, _} <- Repo.insert(build.(item, layer_id)) do
        {:cont, :ok}
      else
        {:error, _} = error -> {:halt, error}
      end
    end)
  end

  defp insert_each(_items, name, _by_position, _build), do: {:error, "#{name} must be a list"}

  defp layer_id(nil, _by_position, _where), do: {:ok, nil}

  defp layer_id(position, by_position, where) do
    case Map.fetch(by_position, position) do
      {:ok, id} -> {:ok, id}
      :error -> {:error, "#{where}.layer_position does not match a layer"}
    end
  end

  @doc "Renumbers the layers by depth and syncs the rule flags; the end of every write."
  def finish(borehole_id) do
    {:ok, id} = Ecto.UUID.dump(borehole_id)

    Repo.query!(
      """
      UPDATE borehole_layers l SET position = r.rn
      FROM (SELECT id, row_number() OVER (ORDER BY depth_from_m, depth_to_m, id) AS rn
            FROM borehole_layers WHERE borehole_id = $1) r
      WHERE l.id = r.id AND l.position IS DISTINCT FROM r.rn
      """,
      [id]
    )

    Checks.sync(borehole_id)
  end

  # -- Helpers -------------------------------------------------------------------------------

  # One transaction: `fun` returns :ok or {:error, reason}.
  defp write(id, fun) do
    with {:ok, borehole} <- fetch_borehole(id) do
      Repo.transaction(fn ->
        case fun.(borehole) do
          :ok ->
            finish(borehole.id)
            Boreholes.get_borehole(borehole.id)

          {:error, reason} ->
            Repo.rollback(reason)
        end
      end)
    end
  end

  # Resolves the open flags on each field, then writes one edit row per field. The flags come
  # first so the edit is newer than the resolution (see `Checks`).
  defp record(borehole_id, layer_id, edits) do
    Enum.each(edits, fn {field, old, new} ->
      now = DateTime.utc_now()

      from(f in FieldFlag,
        where: f.borehole_id == ^borehole_id and f.field == ^field and is_nil(f.resolved_at)
      )
      |> where_layer(layer_id)
      |> Repo.update_all(set: [resolved_at: now, resolved_by: "human", updated_at: now])

      Repo.insert!(%FieldEdit{
        borehole_id: borehole_id,
        layer_id: layer_id,
        field: field,
        old_value: old,
        new_value: new,
        source: "human"
      })
    end)
  end

  defp where_layer(query, nil), do: where(query, [f], is_nil(f.layer_id))
  defp where_layer(query, layer_id), do: where(query, [f], f.layer_id == ^layer_id)

  defp current_location(id),
    do: Repo.one(from b in Borehole, where: b.id == ^id, select: b.location)

  # `new_value` is what was written (x/y/epsg in the source CRS); the old location is only known
  # in WGS84 (`epsg` 4326), which `Boreholes.set_location/2` can reproject just the same.
  defp location_edit(old, new, new_value) do
    if json(old) == json(new),
      do: [],
      else: [{"location", json(old), new_value || json(new)}]
  end

  defp check_coordinates(attrs) do
    given = Enum.count(~w(x y epsg), &(attrs[&1] != nil))
    if given in [0, 3], do: :ok, else: {:error, "x, y and epsg must be given together"}
  end

  defp fetch_borehole(id) do
    with {:ok, uuid} <- Ecto.UUID.cast(id),
         %Borehole{} = borehole <- Repo.get(Borehole, uuid) do
      {:ok, borehole}
    else
      _ -> {:error, :not_found}
    end
  end

  defp fetch_layer(%Borehole{id: borehole_id}, layer_id) do
    with {:ok, uuid} <- Ecto.UUID.cast(layer_id),
         %BoreholeLayer{borehole_id: ^borehole_id} = layer <- Repo.get(BoreholeLayer, uuid) do
      {:ok, layer}
    else
      _ -> {:error, :not_found}
    end
  end

  defp fetch_edit(%Borehole{id: borehole_id}, edit_id) do
    with {:ok, uuid} <- Ecto.UUID.cast(edit_id),
         %FieldEdit{borehole_id: ^borehole_id} = edit <- Repo.get(FieldEdit, uuid) do
      {:ok, edit}
    else
      _ -> {:error, :not_found}
    end
  end

  defp snapshot(%BoreholeLayer{} = layer),
    do: Map.new(@layer_snapshot, &{Atom.to_string(&1), json(Map.get(layer, &1))})

  # Values as stored in the history: plain JSON.
  defp json(%Decimal{} = decimal), do: Decimal.to_float(decimal)
  defp json(%Date{} = date), do: Date.to_iso8601(date)

  defp json(%Geo.Point{coordinates: {lon, lat}}), do: %{"x" => lon, "y" => lat, "epsg" => 4326}

  defp json(value), do: value

  defp stringify(map), do: Map.new(map, fn {k, v} -> {to_string(k), v} end)
end
