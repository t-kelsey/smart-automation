defmodule Api.Boreholes do
  @moduledoc """
  The Boreholes context: querying boreholes, their layers and documents.
  """

  import Ecto.Query, warn: false
  alias Api.Repo

  alias Api.Boreholes.Borehole
  alias Api.Boreholes.BoreholeLayer

  @doc """
  Lists boreholes, optionally filtered by a bounding box.

  `bbox` is `%{min_lon:, min_lat:, max_lon:, max_lat:}` or `nil` to return all boreholes.
  """
  def list_boreholes(bbox \\ nil)

  def list_boreholes(nil) do
    Repo.all(Borehole)
  end

  def list_boreholes(%{min_lon: min_lon, min_lat: min_lat, max_lon: max_lon, max_lat: max_lat}) do
    Borehole
    |> where(
      [b],
      fragment(
        "? && ST_MakeEnvelope(?, ?, ?, ?, 4326)",
        b.location,
        ^min_lon,
        ^min_lat,
        ^max_lon,
        ^max_lat
      )
    )
    |> Repo.all()
  end

  @doc """
  Fetches a borehole by id, preloading its documents and layers (ordered by position).
  """
  def get_borehole!(id) do
    layers_query = from(l in BoreholeLayer, order_by: l.position)

    Borehole
    |> Repo.get!(id)
    |> Repo.preload([:documents, borehole_layers: layers_query])
  end

  @doc """
  Searches boreholes by name, external_id, or a layer's stratigraphy (case-insensitive).
  """
  def search_boreholes(query_string) do
    term = "%#{query_string}%"

    Borehole
    |> join(:left, [b], l in BoreholeLayer, on: l.borehole_id == b.id)
    |> where(
      [b, l],
      ilike(b.name, ^term) or ilike(b.external_id, ^term) or ilike(l.stratigraphy, ^term)
    )
    |> distinct([b], b.id)
    |> Repo.all()
  end
end
