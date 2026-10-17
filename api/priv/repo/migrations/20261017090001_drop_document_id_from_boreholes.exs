defmodule Api.Repo.Migrations.DropDocumentIdFromBoreholes do
  use Ecto.Migration

  # document <-> borehole is now many-to-many via borehole_documents; reversible explicitly since
  # `remove/3` requires the original column definition to restore it on rollback.
  def up do
    drop index(:boreholes, [:document_id])

    alter table(:boreholes) do
      remove :document_id
    end
  end

  def down do
    alter table(:boreholes) do
      add :document_id, references(:documents, type: :binary_id)
    end

    create index(:boreholes, [:document_id])
  end
end
