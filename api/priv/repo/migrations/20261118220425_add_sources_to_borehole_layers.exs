defmodule Api.Repo.Migrations.AddSourcesToBoreholeLayers do
  use Ecto.Migration

  # ADR-0006: besides the box of the whole layer (`source`), one box per layer field, so the
  # review can zoom to a single depth or description.
  def change do
    alter table(:borehole_layers) do
      add :sources, :map, null: false, default: %{}
    end
  end
end
