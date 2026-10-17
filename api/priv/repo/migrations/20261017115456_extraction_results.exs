defmodule Api.Repo.Migrations.ExtractionResults do
  use Ecto.Migration

  def change do
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
  end
end
