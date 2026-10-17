defmodule Api.Repo.Migrations.CreateBoreholeLayers do
  use Ecto.Migration

  def change do
    create table(:borehole_layers, primary_key: false) do
      add :id, :binary_id, primary_key: true
      add :borehole_id, references(:boreholes, type: :binary_id), null: false
      add :position, :integer
      add :depth_from_m, :decimal
      add :depth_to_m, :decimal
      add :stratigraphy, :string
      add :petrography, :string
      add :color, :string
      add :raw_text, :string

      timestamps(type: :utc_datetime)
    end

    create index(:borehole_layers, [:borehole_id])
  end
end
