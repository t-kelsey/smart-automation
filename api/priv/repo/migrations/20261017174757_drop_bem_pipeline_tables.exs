defmodule Api.Repo.Migrations.DropBemPipelineTables do
  @moduledoc """
  Drops the four `bem/` pipeline-tracking tables (ADR-0030); replaced by `exec_stages`,
  `stage_document_links` and `reports` (ADR-0034).
  """
  use Ecto.Migration

  def up do
    drop table(:sink_results)
    drop table(:extraction_results)
    drop table(:triage_sections)
    drop table(:pipeline_stage_runs)
  end

  def down do
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

    create table(:triage_sections, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :document_id, references(:documents, type: :binary_id, on_delete: :delete_all),
        null: false

      add :section_index, :integer, null: false
      add :borehole_id_guess, :string
      add :raw_markdown, :text
      add :translate_errors, {:array, :string}, null: false, default: []

      timestamps(type: :utc_datetime)
    end

    create unique_index(:triage_sections, [:document_id, :section_index])

    create table(:extraction_results, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :triage_section_id,
          references(:triage_sections, type: :binary_id, on_delete: :delete_all),
          null: false

      add :status, :string, null: false
      add :extracted_fields, :map
      add :validation_issues, :map
      add :error, :string

      timestamps(type: :utc_datetime)
    end

    create unique_index(:extraction_results, [:triage_section_id])

    create table(:sink_results, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :extraction_result_id,
          references(:extraction_results, type: :binary_id, on_delete: :delete_all),
          null: false

      add :target, :string, null: false
      add :success, :boolean, null: false
      add :response_status, :integer
      add :created_borehole_id, references(:boreholes, type: :binary_id, on_delete: :nilify_all)
      add :error, :string

      timestamps(type: :utc_datetime)
    end

    create unique_index(:sink_results, [:extraction_result_id])
    create index(:sink_results, [:created_borehole_id])
  end
end
