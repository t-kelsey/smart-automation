defmodule Api.Repo.Migrations.AddRoleToBoreholeDocuments do
  use Ecto.Migration

  def up do
    alter table(:borehole_documents) do
      add :role, :string, null: false, default: "additional"
    end

    create constraint(:borehole_documents, :role_is_valid,
             check: "role IN ('original', 'additional')"
           )

    # Existing links: the oldest document of each borehole becomes its original.
    execute """
    UPDATE borehole_documents SET role = 'original'
    WHERE id IN (
      SELECT DISTINCT ON (borehole_id) id FROM borehole_documents
      ORDER BY borehole_id, inserted_at, id
    )
    """

    # At most one original document per borehole (ADR-0028).
    create unique_index(:borehole_documents, [:borehole_id],
             where: "role = 'original'",
             name: :borehole_documents_one_original_index
           )
  end

  def down do
    drop index(:borehole_documents, [:borehole_id], name: :borehole_documents_one_original_index)
    drop constraint(:borehole_documents, :role_is_valid)

    alter table(:borehole_documents) do
      remove :role
    end
  end
end
