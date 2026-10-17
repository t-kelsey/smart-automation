defmodule Api.Repo.Migrations.CreateBoreholes do
  use Ecto.Migration

  def change do
    create table(:boreholes, primary_key: false) do
      add :id, :binary_id, primary_key: true
      add :name, :string, null: false
      add :external_id, :string
      add :purpose, :string
      add :drilling_method, :string
      add :drilled_at, :date
      add :end_date, :date
      add :location, :geometry
      add :source_coordinate_system, :string
      add :source_coordinate_raw, :string
      add :total_depth_m, :decimal
      add :borehole_length_m, :decimal
      add :elevation_m, :decimal
      add :groundwater_level_m, :decimal
      add :verified, :boolean, null: false, default: false
      add :metadata, :map, null: false, default: %{}

      timestamps(type: :utc_datetime)
    end

    create index(:boreholes, [:location], using: :gist)
  end
end
