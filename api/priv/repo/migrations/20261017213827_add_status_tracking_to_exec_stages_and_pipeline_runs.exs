defmodule Api.Repo.Migrations.AddStatusTrackingToExecStagesAndPipelineRuns do
  use Ecto.Migration

  # Stage and run lifecycle tracking (ADR-0040): every exec_stage gets a status
  # (new|running|success|failed|stopped) plus timing, error, model/effort and token usage; a
  # pipeline run gets timing, the stage it is in and its error, and can be stopped.
  def up do
    alter table(:exec_stages) do
      add :status, :string, null: false, default: "new"
      add :started_at, :utc_datetime_usec
      add :finished_at, :utc_datetime_usec
      add :error, :text
      add :model, :string
      add :effort, :string
      add :usage, :map
    end

    # stages are now created before they have a result
    execute "ALTER TABLE exec_stages ALTER COLUMN data DROP NOT NULL"

    # rows recorded before this migration were posted once a stage had finished; failures stored
    # their reason in data (`{"status": "failed", "error": ...}`)
    execute """
    UPDATE exec_stages
    SET status = CASE WHEN data->>'status' = 'failed' THEN 'failed' ELSE 'success' END,
        error = data->>'error',
        finished_at = inserted_at
    """

    create index(:exec_stages, [:status])

    alter table(:pipeline_runs) do
      add :started_at, :utc_datetime_usec
      add :finished_at, :utc_datetime_usec
      add :current_stage, :string
      add :error, :text
    end

    execute "UPDATE pipeline_runs SET started_at = inserted_at WHERE status <> 'new'"

    execute """
    UPDATE pipeline_runs SET finished_at = updated_at WHERE status IN ('completed', 'failed')
    """
  end

  def down do
    execute "DELETE FROM exec_stages WHERE data IS NULL"
    execute "ALTER TABLE exec_stages ALTER COLUMN data SET NOT NULL"

    drop index(:exec_stages, [:status])

    alter table(:exec_stages) do
      remove :status
      remove :started_at
      remove :finished_at
      remove :error
      remove :model
      remove :effort
      remove :usage
    end

    execute "UPDATE pipeline_runs SET status = 'failed' WHERE status = 'stopped'"

    alter table(:pipeline_runs) do
      remove :started_at
      remove :finished_at
      remove :current_stage
      remove :error
    end
  end
end
