defmodule ApiWeb.ExecStageJSON do
  @doc "Renders a single exec_stage."
  def show(%{exec_stage: exec_stage}), do: %{data: data(exec_stage)}

  @doc "Renders a list of exec_stages."
  def index(%{exec_stages: exec_stages}), do: %{data: Enum.map(exec_stages, &data/1)}

  defp data(exec_stage) do
    %{
      id: exec_stage.id,
      type: exec_stage.type,
      run_id: exec_stage.run_id,
      position: exec_stage.position,
      status: exec_stage.status,
      data: exec_stage.data,
      error: exec_stage.error,
      model: exec_stage.model,
      effort: exec_stage.effort,
      usage: exec_stage.usage,
      started_at: exec_stage.started_at,
      finished_at: exec_stage.finished_at,
      duration_ms: duration_ms(exec_stage),
      document_ids: document_ids(exec_stage),
      inserted_at: exec_stage.inserted_at,
      updated_at: exec_stage.updated_at
    }
  end

  @doc "Milliseconds from `started_at` to `finished_at` (or to now while running); `nil` if not started."
  def duration_ms(%{started_at: nil}), do: nil

  def duration_ms(%{started_at: started, finished_at: finished}) do
    DateTime.diff(finished || DateTime.utc_now(), started, :millisecond)
  end

  defp document_ids(%{documents: documents}) when is_list(documents) do
    Enum.map(documents, & &1.id)
  end

  defp document_ids(_exec_stage), do: []
end
