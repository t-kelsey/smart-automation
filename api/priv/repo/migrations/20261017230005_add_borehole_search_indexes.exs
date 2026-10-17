defmodule Api.Repo.Migrations.AddBoreholeSearchIndexes do
  use Ecto.Migration

  # Indexes for the search query language (ADR-0042): trigram GIN indexes serve `ILIKE '%term%'`
  # and the word-similarity lookups of the autocorrection, the B-tree serves date ranges.
  def up do
    execute "CREATE EXTENSION IF NOT EXISTS pg_trgm"

    for column <- [:name, :external_id, :place] do
      execute "CREATE INDEX boreholes_#{column}_trgm_index ON boreholes USING gin (#{column} gin_trgm_ops)"
    end

    create index(:boreholes, [:drilled_at])
  end

  def down do
    drop index(:boreholes, [:drilled_at])

    for column <- [:name, :external_id, :place] do
      execute "DROP INDEX boreholes_#{column}_trgm_index"
    end

    # Like postgis, keep the extension: removing it could break something else that uses it.
  end
end
