defmodule ApiWeb.BoreholeController do
  use ApiWeb, :controller

  alias Api.Boreholes
  alias Api.Boreholes.Review
  alias Api.Boreholes.SearchQuery
  alias ApiWeb.BoreholeParams

  action_fallback ApiWeb.FallbackController

  @doc """
  GeoJSON list of boreholes with filters, sorting and paging (see docs/api-reference.md).
  `view=points` returns only id, name and verified per feature, for the map; `view=columns`
  (requires `bbox`) adds the total depth and the layers, for the map's 3D detail view.
  """
  def index(conn, params) do
    with {:ok, filters} <- BoreholeParams.parse(params),
         {:ok, view} <- parse_view(params, filters) do
      render_list(conn, filters, view)
    end
  end

  @doc """
  Probable EPSG codes for `x`/`y` written without one, judged by an optional rough area
  (`lon`/`lat`), the other boreholes nearby or the borehole's own position (see
  `Api.Boreholes.guess_epsg/4`). `{"data": [{"epsg", "distance_m", "near"}]}`, best first.
  """
  def epsg_guess(conn, %{"id" => id} = params) do
    with {:ok, _} <- Ecto.UUID.cast(id) |> ok_or(:not_found),
         {x, ""} <- Float.parse(to_string(params["x"] || "")),
         {y, ""} <- Float.parse(to_string(params["y"] || "")),
         {:ok, area} <- area(params) do
      json(conn, %{data: Boreholes.guess_epsg(id, x, y, area)})
    else
      {:error, :not_found} -> {:error, :not_found}
      _ -> {:error, "x and y must be numbers"}
    end
  end

  # optional `lon`/`lat`: the rough area the borehole is in
  defp area(%{"lon" => lon, "lat" => lat}) do
    with {lon, ""} <- Float.parse(to_string(lon)),
         {lat, ""} <- Float.parse(to_string(lat)),
         true <- abs(lon) <= 180 and abs(lat) <= 90 do
      {:ok, {lon, lat}}
    else
      _ -> {:error, "lon and lat must be degrees"}
    end
  end

  defp area(_params), do: {:ok, nil}

  defp ok_or({:ok, v}, _), do: {:ok, v}
  defp ok_or(:error, reason), do: {:error, reason}

  def show(conn, %{"id" => id}) do
    case Boreholes.get_borehole(id) do
      nil -> {:error, :not_found}
      borehole -> render(conn, :show, borehole: borehole)
    end
  end

  @doc "Deletes a borehole with its layers, flags and history (not its documents)."
  def delete(conn, %{"id" => id}) do
    with %{} = borehole <- Boreholes.get_borehole(id) || {:error, :not_found},
         {:ok, _} <- Boreholes.delete_borehole(borehole) do
      send_resp(conn, :no_content, "")
    end
  end

  @doc """
  Creates a borehole with its layers (see docs/api-reference.md). Body: `{"borehole": {...},
  "layers": [...], "document_id": "...", "additional_document_ids": ["..."]}`. `document_id` is
  the borehole's original document, `additional_document_ids` further linked documents (e.g. the
  split-out PDF). `flags` and `edits` are the validator's findings and corrections (ADR-0006),
  `borehole.sources` and `layers[].source` say where values stand in the document. `borehole` may carry `"x"`/`"y"`/`"epsg"` instead of `"location"` directly
  (ADR-0001).
  """
  def create(conn, params) do
    borehole_attrs = params["borehole"] || %{}
    layers_attrs = params["layers"] || []

    with {:ok, borehole} <-
           Boreholes.create_borehole(borehole_attrs, layers_attrs,
             document_id: params["document_id"],
             additional_document_ids: params["additional_document_ids"],
             flags: params["flags"],
             edits: params["edits"]
           ) do
      conn
      |> put_status(:created)
      |> render(:show, borehole: borehole)
    end
  end

  @doc "Edits borehole fields, body `{\"borehole\": {...}}` (ADR-0006)."
  def update(conn, %{"id" => id, "borehole" => attrs}) when is_map(attrs) do
    with {:ok, borehole} <- Review.update_borehole(id, attrs),
         do: render(conn, :show, borehole: borehole)
  end

  def update(_conn, _params), do: {:error, "borehole must be an object"}

  @doc "Releases (`true`) or un-releases (`false`) a borehole."
  def verify(conn, %{"id" => id, "verified" => verified}) when is_boolean(verified) do
    with {:ok, borehole} <- Review.set_verified(id, verified),
         do: render(conn, :show, borehole: borehole)
  end

  def verify(_conn, _params), do: {:error, "verified must be true or false"}

  @doc "Undoes one edit by writing its old value back as a new edit."
  def revert(conn, %{"id" => id, "edit_id" => edit_id}) do
    with {:ok, borehole} <- Review.revert_edit(id, edit_id),
         do: render(conn, :show, borehole: borehole)
  end

  @doc """
  Same as `index`, but `q` is the point: results carry a `score`, and a search that finds nothing
  carries an autocorrected `suggestion` if there is one (ADR-0003).
  """
  def search(conn, params) do
    with {:ok, filters} <- BoreholeParams.parse(params),
         {:ok, view} <- parse_view(params, filters) do
      render_list(conn, Map.put_new(filters, :q, ""), view)
    end
  end

  @doc """
  Completions for the term being typed at the end of `q` (ADR-0003). `limit` is 1–20, default 8.
  """
  def complete(conn, params) do
    with {:ok, limit} <- BoreholeParams.parse_completion_limit(params) do
      render(conn, :complete, completions: Boreholes.complete_query(params["q"] || "", limit))
    end
  end

  # Layers of every match are only loaded for a bounded area, never for the whole dataset.
  defp parse_view(%{"view" => "points"}, _filters), do: {:ok, :points}

  defp parse_view(%{"view" => "columns"}, filters) do
    if filters[:bbox], do: {:ok, :columns}, else: {:error, "bbox is required for view=columns"}
  end

  defp parse_view(_params, _filters), do: {:ok, :full}

  defp render_list(conn, filters, view) do
    %{entries: entries, total: total} = Boreholes.list_boreholes(filters)
    entries = if view == :columns, do: Boreholes.preload_layers(entries), else: entries

    suggestion =
      case filters[:q] do
        %SearchQuery{terms: [_ | _]} = search when total == 0 -> Boreholes.suggest_query(search)
        _ -> nil
      end

    render(conn, :index,
      entries: entries,
      total: total,
      suggestion: suggestion,
      limit: filters[:limit],
      offset: filters[:offset] || 0,
      view: view
    )
  end
end
