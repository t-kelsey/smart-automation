defmodule Api.Repo.Migrations.ReviewFollowups do
  use Ecto.Migration

  def up do
    alter table(:field_flags) do
      add :suggestion, :map
    end

    # like field_edits.layer_id: a deleted layer must not take its flags with it
    drop constraint(:field_flags, "field_flags_layer_id_fkey")

    alter table(:documents) do
      add :sha256, :string
    end

    create index(:documents, [:sha256])

    # second precision made "newest row per (type, position)" ambiguous
    alter table(:exec_stages) do
      modify :inserted_at, :utc_datetime_usec
      modify :updated_at, :utc_datetime_usec
    end
  end

  def down do
    alter table(:exec_stages) do
      modify :inserted_at, :utc_datetime
      modify :updated_at, :utc_datetime
    end

    drop index(:documents, [:sha256])

    alter table(:documents) do
      remove :sha256
    end

    execute "DELETE FROM field_flags WHERE layer_id IS NOT NULL AND layer_id NOT IN (SELECT id FROM borehole_layers)"

    alter table(:field_flags) do
      modify :layer_id, references(:borehole_layers, type: :binary_id, on_delete: :delete_all),
        from: :binary_id
    end

    alter table(:field_flags) do
      remove :suggestion
    end
  end
end
