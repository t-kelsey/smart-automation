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
      data: exec_stage.data,
      document_ids: document_ids(exec_stage),
      inserted_at: exec_stage.inserted_at
    }
  end

  defp document_ids(%{documents: documents}) when is_list(documents) do
    Enum.map(documents, & &1.id)
  end

  defp document_ids(_exec_stage), do: []
end
