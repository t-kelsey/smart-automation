defmodule Api.Repo.Migrations.CreateExecStages do
  use Ecto.Migration

  def change do
    create table(:exec_stages, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :type, :string, null: false
      add :run_id, :string, null: false
      add :position, :integer
      add :data, :map, null: false

      timestamps(type: :utc_datetime)
    end

    create index(:exec_stages, [:run_id])
  end
end
