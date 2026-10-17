defmodule ApiWeb.PipelineRunJSON do
  @doc """
  Renders the pipeline runs list (`index`): one row per run with `document_filename`, no
  `exec_stages`/`report` (those stay on `GET /api/pipeline_runs/:id`, for a light table view).
  """
  def index(%{entries: entries, total: total, limit: limit, offset: offset}) do
    %{
      data: Enum.map(entries, &entry_data/1),
      total: total,
      limit: limit,
      offset: offset
    }
  end

  @doc """
  Renders a pipeline run. `exec_stages`/`report` are included only when given (`show`/
  `update_status`); omitted right after `create`, where there is nothing to show yet.
  """
  def show(assigns), do: %{data: data(assigns)}

  defp entry_data(pipeline_run) do
    data(%{pipeline_run: pipeline_run})
    |> Map.put(:document_filename, document_filename(pipeline_run))
  end

  defp document_filename(%{document: %Ecto.Association.NotLoaded{}}), do: nil
  defp document_filename(%{document: document}), do: document.original_filename

  defp data(%{pipeline_run: pipeline_run} = assigns) do
    %{
      id: pipeline_run.id,
      document_id: pipeline_run.document_id,
      status: pipeline_run.status,
      config: pipeline_run.config,
      inserted_at: pipeline_run.inserted_at,
      updated_at: pipeline_run.updated_at
    }
    |> maybe_put_exec_stages(assigns)
    |> maybe_put_report(assigns)
  end

  defp maybe_put_exec_stages(data, %{exec_stages: exec_stages}) do
    Map.put(data, :exec_stages, Enum.map(exec_stages, &exec_stage_data/1))
  end

  defp maybe_put_exec_stages(data, _assigns), do: data

  defp exec_stage_data(exec_stage) do
    %{
      id: exec_stage.id,
      type: exec_stage.type,
      position: exec_stage.position,
      data: exec_stage.data,
      document_ids: exec_stage_document_ids(exec_stage),
      inserted_at: exec_stage.inserted_at
    }
  end

  defp exec_stage_document_ids(%{documents: documents}) when is_list(documents) do
    Enum.map(documents, & &1.id)
  end

  defp exec_stage_document_ids(_exec_stage), do: []

  defp maybe_put_report(data, %{report: nil}), do: Map.put(data, :report, nil)

  defp maybe_put_report(data, %{report: report}) do
    Map.put(data, :report, %{
      id: report.id,
      run_id: report.run_id,
      data: report.data,
      inserted_at: report.inserted_at
    })
  end

  defp maybe_put_report(data, _assigns), do: data
end
