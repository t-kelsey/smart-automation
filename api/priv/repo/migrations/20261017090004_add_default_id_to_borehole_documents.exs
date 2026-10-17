defmodule Api.Repo.Migrations.AddDefaultIdToBoreholeDocuments do
  use Ecto.Migration

  def up do
    execute "ALTER TABLE borehole_documents ALTER COLUMN id SET DEFAULT gen_random_uuid()"
    execute "ALTER TABLE borehole_documents ALTER COLUMN inserted_at SET DEFAULT now()"
    execute "ALTER TABLE borehole_documents ALTER COLUMN updated_at SET DEFAULT now()"
  end

  def down do
    execute "ALTER TABLE borehole_documents ALTER COLUMN id DROP DEFAULT"
    execute "ALTER TABLE borehole_documents ALTER COLUMN inserted_at DROP DEFAULT"
    execute "ALTER TABLE borehole_documents ALTER COLUMN updated_at DROP DEFAULT"
  end
end
