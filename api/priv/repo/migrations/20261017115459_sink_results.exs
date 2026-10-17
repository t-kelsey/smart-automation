defmodule Api.Repo.Migrations.SinkResults do
  use Ecto.Migration

  def change do
    create table(:sink_results, primary_key: false) do
      add :id, :binary_id, primary_key: true

      add :extraction_result_id,
          references(:extraction_results, type: :binary_id, on_delete: :delete_all),
          null: false

      add :target, :string, null: false
      add :success, :boolean, null: false
      add :response_status, :integer
      add :created_borehole_id, references(:boreholes, type: :binary_id, on_delete: :nilify_all)
      add :error, :string

      timestamps(type: :utc_datetime)
    end

    create unique_index(:sink_results, [:extraction_result_id])
    create index(:sink_results, [:created_borehole_id])
  end
end
