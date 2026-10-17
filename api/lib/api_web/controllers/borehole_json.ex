defmodule ApiWeb.BoreholeJSON do
  alias Api.Boreholes.Borehole

  @doc """
  Renders a GeoJSON FeatureCollection for a list of boreholes.
  """
  def index(%{boreholes: boreholes}) do
    %{
      type: "FeatureCollection",
      features: Enum.map(boreholes, &feature/1)
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

  defp feature(%Borehole{} = borehole) do
    %{
      type: "Feature",
      geometry: borehole.location,
      properties: properties(borehole)
    }
  end

  # Borehole fields, excluding :location, :borehole_layers, and :documents.
  defp properties(%Borehole{} = borehole) do
    %{
      id: borehole.id,
      name: borehole.name,
      external_id: borehole.external_id,
      purpose: borehole.purpose,
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

  # Never include :storage_path or :raw_extraction (confidential, see ADR-0014).
  defp document(document) do
    %{
      id: document.id,
      original_filename: document.original_filename,
      mime_type: document.mime_type,
      source_country: document.source_country,
      status: document.status
    }
  end
end
