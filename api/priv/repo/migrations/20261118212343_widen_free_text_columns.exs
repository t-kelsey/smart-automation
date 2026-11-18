defmodule Api.Repo.Migrations.WidenFreeTextColumns do
  use Ecto.Migration

  # Extracted free text (layer descriptions, place names, coordinate notes) can exceed 255
  # characters; a too long value made POST /api/boreholes fail with a 500.
  def change do
    alter table(:borehole_layers) do
      modify :raw_text, :text, from: :string
      modify :stratigraphy, :text, from: :string
      modify :petrography, :text, from: :string
      modify :color, :text, from: :string
    end

    alter table(:boreholes) do
      modify :purpose, :text, from: :string
      modify :place, :text, from: :string
      modify :client, :text, from: :string
      modify :drilling_method, :text, from: :string
      modify :source_coordinate_system, :text, from: :string
      modify :source_coordinate_raw, :text, from: :string
    end
  end
end
