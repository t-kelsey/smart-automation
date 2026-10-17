defmodule Api.Boreholes.PipelineRun do
  @moduledoc """
  One invocation of the `claude_test/` pipeline (ADR-0035) for a single document: `id` is handed
  out to the pipeline as `run_id`, grouping its `Api.Boreholes.ExecStage` rows and (optional)
  `Api.Boreholes.Report`. `config` is the frontend's free-form per-stage model/effort choices,
  stored as-is. `status` tracks the run from `"new"` (just created) through `"running"` (handed
  to the pipeline) to `"completed"` / `"failed"` (reported back by the pipeline).
  """
  use Ecto.Schema
  import Ecto.Changeset

  @statuses ~w(new running completed failed)

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "pipeline_runs" do
    field :status, :string, default: "new"
    field :config, :map, default: %{}

    belongs_to :document, Api.Boreholes.Document

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(pipeline_run, attrs) do
    pipeline_run
    |> cast(attrs, [:document_id, :status, :config])
    |> validate_required([:document_id])
    |> validate_inclusion(:status, @statuses)
    |> foreign_key_constraint(:document_id)
  end
end
