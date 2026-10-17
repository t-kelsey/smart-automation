defmodule Api.Boreholes.PipelineStageRun do
  @moduledoc """
  Tracks what the `bem/` pipeline's OCR/translation stage produced for a document (design doc:
  docs/elixir-backend-borehole-pipeline.md, "Proposed Extension: Pipeline Stage Tracking").
  Debug/internal only — never serialised in a public API response. Latest run only: a rerun
  upserts on `(document_id, stage)` instead of keeping history.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @stages ~w(ocr translation)
  @statuses ~w(ok error)

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "pipeline_stage_runs" do
    field :stage, :string
    field :status, :string
    field :output, :map
    field :error, :string
    field :started_at, :utc_datetime
    field :finished_at, :utc_datetime

    belongs_to :document, Api.Boreholes.Document

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(pipeline_stage_run, attrs) do
    pipeline_stage_run
    |> cast(attrs, [:stage, :status, :output, :error, :started_at, :finished_at])
    |> validate_required([:stage, :status])
    |> validate_inclusion(:stage, @stages)
    |> validate_inclusion(:status, @statuses)
    |> unique_constraint([:document_id, :stage])
  end
end
