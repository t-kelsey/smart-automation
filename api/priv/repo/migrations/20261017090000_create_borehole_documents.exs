defmodule Api.Repo.Migrations.CreateBoreholeDocuments do
  use Ecto.Migration

  def change do
    create table(:borehole_documents, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :borehole_id, references(:boreholes, type: :binary_id, on_delete: :delete_all),
        null: false

      add :document_id, references(:documents, type: :binary_id, on_delete: :delete_all),
        null: false

      timestamps(type: :utc_datetime)
    end

    create unique_index(:borehole_documents, [:borehole_id, :document_id])
    create index(:borehole_documents, [:document_id])
  end
end
