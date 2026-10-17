defmodule Api.Repo.Migrations.TriageSections do
  use Ecto.Migration

  def change do
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
  end
end
