defmodule Api.Repo.Migrations.PipelineStageRuns do
  use Ecto.Migration

  def change do
    create table(:pipeline_stage_runs, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :document_id, references(:documents, type: :binary_id, on_delete: :delete_all),
        null: false

      add :stage, :string, null: false
      add :status, :string, null: false
      add :output, :map
      add :error, :string
      add :started_at, :utc_datetime
      add :finished_at, :utc_datetime

      timestamps(type: :utc_datetime)
    end

    create unique_index(:pipeline_stage_runs, [:document_id, :stage])
  end
end
