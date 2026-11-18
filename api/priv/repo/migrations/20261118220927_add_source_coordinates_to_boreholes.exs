defmodule Api.Repo.Migrations.AddSourceCoordinatesToBoreholes do
  use Ecto.Migration

  # The coordinates as written in the document (x, y in the source CRS), next to the WGS84
  # `location`, so a reviewer can compare them with the log.
  def change do
    alter table(:boreholes) do
      add :source_x, :float
      add :source_y, :float
      add :source_epsg, :integer
    end
  end
end
