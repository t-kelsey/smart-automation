defmodule Api.Boreholes.ExecStage do
  @moduledoc """
  One step execution of the `claude_test/` pipeline (ADR-0034): `type` is `filter`, `split`,
  `extract` or `transform`; `run_id` groups every stage (and the `Api.Boreholes.Report`) of one
  pipeline run; `position` is the borehole index within the run for `extract`/`transform` (`nil`
  for the whole-document `filter`/`split` steps); `data` is the step's JSON file as-is. Debug/
  internal only — never serialised in a public API response. Append-only: reruns add new rows
  instead of replacing previous ones.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @types ~w(filter split extract transform)

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "exec_stages" do
    field :type, :string
    field :run_id, :string
    field :position, :integer
    field :data, :map

    many_to_many :documents, Api.Boreholes.Document, join_through: Api.Boreholes.StageDocumentLink

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(exec_stage, attrs) do
    exec_stage
    |> cast(attrs, [:type, :run_id, :position, :data])
    |> validate_required([:type, :run_id, :data])
    |> validate_inclusion(:type, @types)
  end
end
