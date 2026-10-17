defmodule Api.Repo.Migrations.AddGroundwaterLevelToBoreholes do
  use Ecto.Migration

  def change do
    alter table(:boreholes) do
      add :groundwater_level_m, :decimal
    end
  end
end
