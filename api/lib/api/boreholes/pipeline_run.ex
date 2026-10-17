defmodule Api.Boreholes.PipelineRun do
  @moduledoc """
  One invocation of the pipeline (ADR-0035, lifecycle ADR-0040) for a single document: `id` is
  handed out to the pipeline as `run_id`, grouping its `Api.Boreholes.ExecStage` rows and
  (optional) `Api.Boreholes.Report`. `config` is the frontend's free-form per-stage model/effort
  choices, stored as-is.

  `status` tracks the run from `"new"` (just created) through `"running"` (handed to the
  pipeline) to `"completed"` / `"failed"` (reported back by the pipeline) or `"stopped"`
  (cancelled via `POST /api/pipeline_runs/:id/stop`). `started_at`/`finished_at` are stamped on
  those transitions, `current_stage` is the type of the stage that last started and `error` the
  reason a run failed.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @statuses ~w(new running completed failed stopped)
  @terminal ~w(completed failed stopped)

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "pipeline_runs" do
    field :status, :string, default: "new"
    field :config, :map, default: %{}
    field :started_at, :utc_datetime_usec
    field :finished_at, :utc_datetime_usec
    field :current_stage, :string
    field :error, :string

    belongs_to :document, Api.Boreholes.Document

    timestamps(type: :utc_datetime)
  end

  @doc "Statuses after which a run does not change any more."
  def terminal_statuses, do: @terminal

  @doc false
  def changeset(pipeline_run, attrs) do
    pipeline_run
    |> cast(attrs, [:document_id, :status, :config, :current_stage, :error])
    |> validate_required([:document_id])
    |> validate_inclusion(:status, @statuses)
    |> foreign_key_constraint(:document_id)
    |> stamp_times()
  end

  defp stamp_times(%Ecto.Changeset{valid?: false} = changeset), do: changeset

  defp stamp_times(changeset) do
    status = get_field(changeset, :status)
    now = DateTime.utc_now()

    changeset
    |> then(fn cs ->
      if status == "running" and is_nil(get_field(cs, :started_at)),
        do: put_change(cs, :started_at, now),
        else: cs
    end)
    |> then(fn cs ->
      if status in @terminal and is_nil(get_field(cs, :finished_at)),
        do: put_change(cs, :finished_at, now),
        else: cs
    end)
  end
end
