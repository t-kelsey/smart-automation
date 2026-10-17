defmodule Api.Boreholes.Borehole do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "boreholes" do
    field :name, :string
    field :external_id, :string
    field :purpose, :string
    field :place, :string
    field :client, :string
    field :drilling_method, :string
    field :drilled_at, :date
    field :end_date, :date
    field :location, Geo.PostGIS.Geometry
    field :source_coordinate_system, :string
    field :source_coordinate_raw, :string
    field :total_depth_m, :decimal
    field :borehole_length_m, :decimal
    field :elevation_m, :decimal
    field :groundwater_level_m, :decimal
    field :verified, :boolean, default: false
    field :metadata, :map, default: %{}

    many_to_many :documents, Api.Boreholes.Document, join_through: Api.Boreholes.BoreholeDocument

    has_many :borehole_layers, Api.Boreholes.BoreholeLayer

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(borehole, attrs) do
    borehole
    |> cast(attrs, [
      :name,
      :external_id,
      :purpose,
      :place,
      :client,
      :drilling_method,
      :drilled_at,
      :end_date,
      :location,
      :source_coordinate_system,
      :source_coordinate_raw,
      :total_depth_m,
      :borehole_length_m,
      :elevation_m,
      :groundwater_level_m,
      :verified,
      :metadata
    ])
    |> validate_required([:name])
    |> validate_number(:total_depth_m, greater_than_or_equal_to: 0)
    |> validate_number(:borehole_length_m, greater_than_or_equal_to: 0)
    |> validate_number(:elevation_m, greater_than_or_equal_to: 0)
    |> validate_number(:groundwater_level_m, greater_than_or_equal_to: 0)
  end
end
