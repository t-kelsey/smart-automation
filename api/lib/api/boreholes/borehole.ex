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
    field :sources, :map, default: %{}
    field :verified_at, :utc_datetime
    # set together with `location` from x/y/epsg, as written in the document
    field :source_x, :float
    field :source_y, :float
    field :source_epsg, :integer

    has_many :field_flags, Api.Boreholes.FieldFlag
    has_many :field_edits, Api.Boreholes.FieldEdit

    many_to_many :documents, Api.Boreholes.Document, join_through: Api.Boreholes.BoreholeDocument

    has_many :borehole_layers, Api.Boreholes.BoreholeLayer

    timestamps(type: :utc_datetime)
  end

  # what a human may change with PATCH /api/boreholes/:id (the location via x/y/epsg)
  @editable [
    :name,
    :external_id,
    :purpose,
    :place,
    :client,
    :drilling_method,
    :drilled_at,
    :end_date,
    :source_coordinate_system,
    :source_coordinate_raw,
    :total_depth_m,
    :borehole_length_m,
    :elevation_m,
    :groundwater_level_m
  ]

  @doc "Fields a human may edit."
  def editable, do: @editable

  @doc false
  def edit_changeset(borehole, attrs) do
    borehole |> cast(attrs, @editable) |> validate()
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
      :metadata,
      :sources
    ])
    |> validate()
  end

  defp validate(changeset) do
    changeset
    |> validate_required([:name])
    |> validate_number(:total_depth_m, greater_than_or_equal_to: 0)
    |> validate_number(:borehole_length_m, greater_than_or_equal_to: 0)
    |> validate_number(:groundwater_level_m, greater_than_or_equal_to: 0)
  end
end
