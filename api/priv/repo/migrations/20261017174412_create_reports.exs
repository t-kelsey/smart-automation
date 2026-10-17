defmodule Api.Repo.Migrations.CreateReports do
  use Ecto.Migration

  def change do
    create table(:reports, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :document_id, references(:documents, type: :binary_id, on_delete: :delete_all),
        null: false

      add :run_id, :string, null: false
      add :data, :map, null: false

      timestamps(type: :utc_datetime)
    end

    create index(:reports, [:document_id])
  end
end
