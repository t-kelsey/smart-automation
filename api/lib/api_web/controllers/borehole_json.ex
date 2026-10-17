defmodule ApiWeb.BoreholeJSON do
  alias Api.Boreholes.Borehole

  @doc """
  Renders a GeoJSON FeatureCollection. `total`, `limit` and `offset` are GeoJSON foreign members
  for paging; search results also carry `score` and `snippet` on each feature.
  """
  def index(%{entries: entries, total: total, limit: limit, offset: offset, view: view}) do
    %{
      type: "FeatureCollection",
      total: total,
      limit: limit,
      offset: offset,
      features: Enum.map(entries, &feature(&1, view))
    }
  end

  @doc """
  Renders the full detail of a single borehole, including layers and documents.
  """
  def show(%{borehole: borehole}) do
    %{
      data:
        properties(borehole)
        |> Map.put(:location, borehole.location)
        |> Map.put(:layers, Enum.map(borehole.borehole_layers, &layer/1))
        |> Map.put(:documents, Enum.map(borehole.documents, &document/1))
    }
  end

  defp feature(%{borehole: borehole, score: score, snippet: snippet}, view) do
    %{
      type: "Feature",
      geometry: borehole.location,
      properties: if(view == :points, do: point_properties(borehole), else: properties(borehole))
    }
    |> then(fn f -> if score, do: Map.merge(f, %{score: score, snippet: snippet}), else: f end)
  end

  defp point_properties(%Borehole{} = borehole) do
    %{id: borehole.id, name: borehole.name, verified: borehole.verified}
  end

  # Borehole fields, excluding :location, :borehole_layers, and :documents.
  defp properties(%Borehole{} = borehole) do
    %{
      id: borehole.id,
      name: borehole.name,
      external_id: borehole.external_id,
      purpose: borehole.purpose,
      place: borehole.place,
      client: borehole.client,
      drilling_method: borehole.drilling_method,
      drilled_at: borehole.drilled_at,
      end_date: borehole.end_date,
      source_coordinate_system: borehole.source_coordinate_system,
      source_coordinate_raw: borehole.source_coordinate_raw,
      total_depth_m: borehole.total_depth_m,
      borehole_length_m: borehole.borehole_length_m,
      elevation_m: borehole.elevation_m,
      groundwater_level_m: borehole.groundwater_level_m,
      verified: borehole.verified,
      metadata: borehole.metadata,
      inserted_at: borehole.inserted_at,
      updated_at: borehole.updated_at
    }
  end

  defp layer(layer) do
    %{
      id: layer.id,
      position: layer.position,
      depth_from_m: layer.depth_from_m,
      depth_to_m: layer.depth_to_m,
      stratigraphy: layer.stratigraphy,
      petrography: layer.petrography,
      color: layer.color,
      raw_text: layer.raw_text,
      metadata: layer.metadata
    }
  end

  # Never include :storage_path or :raw_extraction (ADR-0014); the file itself is served by
  # GET /api/documents/:id/file when `has_file` is true (ADR-0026).
  defp document(document) do
    %{
      id: document.id,
      original_filename: document.original_filename,
      mime_type: document.mime_type,
      source_country: document.source_country,
      status: document.status,
      page_count: document.page_count,
      size_bytes: document.size_bytes,
      has_file: Api.Boreholes.document_file_path(document) != nil
    }
  end
end
