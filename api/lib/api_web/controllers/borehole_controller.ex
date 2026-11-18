defmodule ApiWeb.BoreholeController do
  use ApiWeb, :controller

  alias Api.Boreholes
  alias Api.Boreholes.Review
  alias Api.Boreholes.SearchQuery
  alias ApiWeb.BoreholeParams

  action_fallback ApiWeb.FallbackController

  @doc """
  GeoJSON list of boreholes with filters, sorting and paging (see docs/api-reference.md).
  `view=points` returns only id, name and verified per feature, for the map.
  """
  def index(conn, params) do
    with {:ok, filters} <- BoreholeParams.parse(params) do
      render_list(conn, filters, params)
    end
  end

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
    with {:ok, filters} <- BoreholeParams.parse(params) do
      render_list(conn, Map.put_new(filters, :q, ""), params)
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

  defp render_list(conn, filters, params) do
    %{entries: entries, total: total} = Boreholes.list_boreholes(filters)

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
      view: if(params["view"] == "points", do: :points, else: :full)
    )
  end
end
