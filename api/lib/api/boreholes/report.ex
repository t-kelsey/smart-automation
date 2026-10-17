defmodule Api.Boreholes.Report do
  @moduledoc """
  One row per `claude_test/` pipeline run (ADR-0034): `run_id` groups it with the run's
  `Api.Boreholes.ExecStage` rows, `data` is `report.json` as-is (per-step model/time/token/cost
  stats). Debug/internal only — never serialised in a public API response.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "reports" do
    field :run_id, :string
    field :data, :map

    belongs_to :document, Api.Boreholes.Document

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(report, attrs) do
    report
    |> cast(attrs, [:document_id, :run_id, :data])
    |> validate_required([:document_id, :run_id, :data])
    |> foreign_key_constraint(:document_id)
  end
end
