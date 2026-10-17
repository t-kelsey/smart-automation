defmodule Api.Repo.Migrations.CreateStageDocumentLinks do
  use Ecto.Migration

  def change do
    create table(:stage_document_links, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :exec_stage_id, references(:exec_stages, type: :binary_id, on_delete: :delete_all),
        null: false

      add :document_id, references(:documents, type: :binary_id, on_delete: :delete_all),
        null: false

      timestamps(type: :utc_datetime)
    end

    create unique_index(:stage_document_links, [:exec_stage_id, :document_id])
  end
end
