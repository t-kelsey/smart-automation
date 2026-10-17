defmodule Api.Repo.Migrations.CreateDocuments do
  use Ecto.Migration

  def change do
    create table(:documents, primary_key: false) do
      add :id, :binary_id, primary_key: true
      add :original_filename, :string, null: false
      add :storage_path, :string, null: false
      add :source_country, :string
      add :status, :string, null: false, default: "pending"
      add :raw_extraction, :map

      timestamps(type: :utc_datetime)
    end
  end
end
