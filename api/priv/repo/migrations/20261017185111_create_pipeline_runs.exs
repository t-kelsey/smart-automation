defmodule Api.Repo.Migrations.CreatePipelineRuns do
  use Ecto.Migration

  def change do
    create table(:pipeline_runs, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :document_id, references(:documents, type: :binary_id, on_delete: :delete_all),
        null: false

      add :status, :string, null: false, default: "new"
      add :config, :map, null: false, default: %{}

      timestamps(type: :utc_datetime)
    end

    create index(:pipeline_runs, [:document_id])
  end
end
