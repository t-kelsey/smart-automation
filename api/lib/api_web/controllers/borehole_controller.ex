defmodule ApiWeb.BoreholeController do
  use ApiWeb, :controller

  alias Api.Boreholes
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

  @doc """
  Creates a borehole with its layers (see docs/api-reference.md). Body: `{"borehole": {...},
  "layers": [...], "document_id": "...", "additional_document_ids": ["..."]}`. `document_id` is
  the borehole's original document, `additional_document_ids` further linked documents (e.g. the
  split-out PDF). `borehole` may carry `"x"`/`"y"`/`"epsg"` instead of `"location"` directly
  (ADR-0002).
  """
  def create(conn, params) do
    borehole_attrs = params["borehole"] || %{}
    layers_attrs = params["layers"] || []

    with {:ok, borehole} <-
           Boreholes.create_borehole(borehole_attrs, layers_attrs,
             document_id: params["document_id"],
             additional_document_ids: params["additional_document_ids"]
           ) do
      conn
      |> put_status(:created)
      |> render(:show, borehole: borehole)
    end
  end

  @doc """
  Same as `index`, but `q` is the point: results carry a `score`, and a search that finds nothing
  carries an autocorrected `suggestion` if there is one (ADR-0042).
  """
  def search(conn, params) do
    with {:ok, filters} <- BoreholeParams.parse(params) do
      render_list(conn, Map.put_new(filters, :q, ""), params)
    end
  end

  @doc """
  Completions for the term being typed at the end of `q` (ADR-0043). `limit` is 1–20, default 8.
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
