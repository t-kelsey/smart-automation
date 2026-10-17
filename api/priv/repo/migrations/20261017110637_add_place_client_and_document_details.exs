defmodule Api.Repo.Migrations.AddPlaceClientAndDocumentDetails do
  use Ecto.Migration

  def change do
    alter table(:boreholes) do
      # Place name as written on the log (town, site), and the client ("Auftraggeber").
      add :place, :string
      add :client, :string
    end

    alter table(:documents) do
      add :page_count, :integer
      add :size_bytes, :bigint
    end

    # The layer FK had no ON DELETE, so deleting a borehole failed while it still had layers.
    alter table(:borehole_layers) do
      modify :borehole_id,
             references(:boreholes, type: :binary_id, on_delete: :delete_all),
             null: false,
             from: {references(:boreholes, type: :binary_id), null: false}
    end
  end
end
