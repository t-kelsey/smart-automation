defmodule Api.Repo.Migrations.AddMimeTypeToDocuments do
  use Ecto.Migration

  def change do
    alter table(:documents) do
      add :mime_type, :string
    end
  end
end
