defmodule Api.Repo.Migrations.AddExternalIdEndDateLengthToBoreholes do
  use Ecto.Migration

  def change do
    alter table(:boreholes) do
      add :external_id, :string
      add :end_date, :date
      add :borehole_length_m, :decimal
    end
  end
end
