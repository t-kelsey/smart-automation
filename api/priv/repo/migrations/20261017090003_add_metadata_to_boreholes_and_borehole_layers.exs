defmodule Api.Repo.Migrations.AddMetadataToBoreholesAndBoreholeLayers do
  use Ecto.Migration

  def change do
    alter table(:boreholes) do
      add :metadata, :map, null: false, default: %{}
    end

    alter table(:borehole_layers) do
      add :metadata, :map, null: false, default: %{}
    end
  end
end
