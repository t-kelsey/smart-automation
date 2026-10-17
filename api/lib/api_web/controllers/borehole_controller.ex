defmodule ApiWeb.BoreholeController do
  use ApiWeb, :controller

  alias Api.Boreholes
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

  @doc "Same as `index`, but `q` is the point: results carry a `score` and a `snippet`."
  def search(conn, params) do
    with {:ok, filters} <- BoreholeParams.parse(params) do
      render_list(conn, Map.put_new(filters, :q, ""), params)
    end
  end

  defp render_list(conn, filters, params) do
    %{entries: entries, total: total} = Boreholes.list_boreholes(filters)

    render(conn, :index,
      entries: entries,
      total: total,
      limit: filters[:limit],
      offset: filters[:offset] || 0,
      view: if(params["view"] == "points", do: :points, else: :full)
    )
  end
end
