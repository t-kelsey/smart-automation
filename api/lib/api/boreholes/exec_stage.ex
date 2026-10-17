defmodule Api.Boreholes.ExecStage do
  @moduledoc """
  One step execution of the pipeline (ADR-0034, lifecycle ADR-0040): `type` is `filter`, `split`,
  `extract` or `transform`; `run_id` groups every stage (and the `Api.Boreholes.Report`) of one
  pipeline run; `position` is the borehole index within the run for `extract`/`transform` (`nil`
  for the whole-document `filter`/`split` steps); `data` is the step's JSON result as-is (`nil`
  until it has one).

  `status` follows the stage through `"new"` (planned) → `"running"` → `"success"` / `"failed"`,
  or `"stopped"` if the run ended before the stage could finish. `started_at`/`finished_at` are
  set automatically on the transitions; `error`, `model`, `effort` and `usage` (tokens, cost,
  calls) are reported by the pipeline. Reruns add new rows instead of replacing previous ones.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @types ~w(filter split extract transform)
  @statuses ~w(new running success failed stopped)
  @terminal ~w(success failed stopped)

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "exec_stages" do
    field :type, :string
    field :run_id, :string
    field :position, :integer
    field :data, :map
    field :status, :string, default: "new"
    field :started_at, :utc_datetime_usec
    field :finished_at, :utc_datetime_usec
    field :error, :string
    field :model, :string
    field :effort, :string
    field :usage, :map

    many_to_many :documents, Api.Boreholes.Document, join_through: Api.Boreholes.StageDocumentLink

    timestamps(type: :utc_datetime)
  end

  @doc "Every valid `status`."
  def statuses, do: @statuses

  @doc "Statuses after which a stage does not change any more."
  def terminal_statuses, do: @terminal

  @doc "Changeset for a new stage (`type` and `run_id` required)."
  def changeset(exec_stage, attrs) do
    exec_stage
    |> cast(attrs, [:type, :run_id, :position | update_fields()])
    |> validate_required([:type, :run_id, :status])
    |> validate_inclusion(:type, @types)
    |> validate_common()
  end

  @doc """
  Changeset for reporting progress on an existing stage: only the lifecycle fields change; a
  finished stage (`success`/`failed`/`stopped`) cannot change any more.
  """
  def update_changeset(exec_stage, attrs) do
    exec_stage
    |> cast(attrs, update_fields())
    |> validate_required([:status])
    |> validate_not_finished(exec_stage)
    |> validate_common()
  end

  defp update_fields,
    do: [:status, :data, :error, :model, :effort, :usage, :started_at, :finished_at]

  defp validate_common(changeset) do
    changeset
    |> validate_inclusion(:status, @statuses)
    |> stamp_times()
  end

  defp validate_not_finished(changeset, %__MODULE__{status: status}) when status in @terminal do
    if changeset.changes != %{} do
      add_error(changeset, :status, "stage is already #{status} and cannot change any more")
    else
      changeset
    end
  end

  defp validate_not_finished(changeset, _exec_stage), do: changeset

  # running stamps started_at, a terminal status stamps finished_at, unless the caller sent its
  # own times
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
