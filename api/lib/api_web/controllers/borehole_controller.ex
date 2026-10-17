defmodule ApiWeb.BoreholeController do
  use ApiWeb, :controller

  alias Api.Boreholes

  def index(conn, params) do
    case parse_bbox(params["bbox"]) do
      {:ok, bbox} ->
        boreholes = Boreholes.list_boreholes(bbox)
        render(conn, :index, boreholes: boreholes)

      :error ->
        conn
        |> put_status(:bad_request)
        |> json(%{errors: %{detail: "invalid bbox, expected minLon,minLat,maxLon,maxLat"}})
    end
  end

  def show(conn, %{"id" => id}) do
    borehole = Boreholes.get_borehole!(id)
    render(conn, :show, borehole: borehole)
  end

  def search(conn, params) do
    boreholes = Boreholes.search_boreholes(params["q"] || "")
    render(conn, :index, boreholes: boreholes)
  end

  defp parse_bbox(nil), do: {:ok, nil}

  defp parse_bbox(bbox) when is_binary(bbox) do
    with [min_lon, min_lat, max_lon, max_lat] <- String.split(bbox, ","),
         {min_lon, ""} <- Float.parse(min_lon),
         {min_lat, ""} <- Float.parse(min_lat),
         {max_lon, ""} <- Float.parse(max_lon),
         {max_lat, ""} <- Float.parse(max_lat) do
      {:ok, %{min_lon: min_lon, min_lat: min_lat, max_lon: max_lon, max_lat: max_lat}}
    else
      _ -> :error
    end
  end

  defp parse_bbox(_), do: :error
end
