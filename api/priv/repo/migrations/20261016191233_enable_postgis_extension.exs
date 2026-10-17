defmodule Api.Repo.Migrations.EnablePostgisExtension do
  use Ecto.Migration

  def up do
    execute "CREATE EXTENSION IF NOT EXISTS postgis"
  end

  def down do
    # Other tables may come to depend on postgis types/functions, so treat
    # removal as a no-op rather than risk dropping an extension still in use.
    :ok
  end
end
