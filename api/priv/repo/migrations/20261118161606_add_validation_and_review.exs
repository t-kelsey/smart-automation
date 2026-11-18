defmodule Api.Repo.Migrations.AddValidationAndReview do
  use Ecto.Migration

  # ADR-0006: sources (where a value stands in the document), verification time, flags and history.
  def change do
    alter table(:boreholes) do
      add :sources, :map, null: false, default: %{}
      add :verified_at, :utc_datetime
    end

    alter table(:borehole_layers) do
      add :source, :map
    end

    create table(:field_flags, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :borehole_id, references(:boreholes, type: :binary_id, on_delete: :delete_all),
        null: false

      add :layer_id, references(:borehole_layers, type: :binary_id, on_delete: :delete_all)
      add :field, :string, null: false
      add :severity, :string, null: false
      add :message, :text, null: false
      add :origin, :string, null: false
      add :code, :string
      add :resolved_at, :utc_datetime_usec
      add :resolved_by, :string

      timestamps(type: :utc_datetime_usec)
    end

    create index(:field_flags, [:borehole_id])

    create index(:field_flags, [:borehole_id],
             where: "resolved_at IS NULL",
             name: :field_flags_open_index
           )

    # layer_id has no foreign key: the history survives a deleted layer
    create table(:field_edits, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :borehole_id, references(:boreholes, type: :binary_id, on_delete: :delete_all),
        null: false

      add :layer_id, :binary_id
      add :field, :string, null: false
      add :old_value, :map
      add :new_value, :map
      add :source, :string, null: false
      add :reason, :text

      timestamps(type: :utc_datetime_usec, updated_at: false)
    end

    create index(:field_edits, [:borehole_id])
  end
end
