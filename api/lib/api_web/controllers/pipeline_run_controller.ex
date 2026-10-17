defmodule ApiWeb.PipelineRunController do
  @moduledoc """
  Kicks off and tracks `claude_test/` pipeline runs for a document (ADR-0035). The frontend calls
  `create`/`show`; `update_status` is called by the pipeline itself when a run finishes.
  """
  use ApiWeb, :controller

  alias Api.Boreholes
  alias Api.Boreholes.PipelineRun

  action_fallback ApiWeb.FallbackController

  @doc """
  Creates a pipeline run for a document and submits it to the pipeline. Body: `{"document_id",
  "config"}`. Submission happens synchronously in this request; the response reflects whether it
  reached the pipeline (`"running"`) or not (`"new"`/`"failed"`, see `Api.Pipeline.submit_pipeline_run/1`).
  """
  def create(conn, params) do
    with {:ok, pipeline_run} <- Boreholes.create_pipeline_run(params) do
      {:ok, pipeline_run} = Api.Pipeline.submit_pipeline_run(pipeline_run)

      conn
      |> put_status(:created)
      |> render(:show, pipeline_run: pipeline_run)
    end
  end

  @doc """
  The pipeline run plus its `exec_stages` (newest first) and `report` (`nil` until the pipeline
  has posted one), for the frontend to poll live progress.
  """
  def show(conn, %{"id" => id}) do
    case Boreholes.get_pipeline_run(id) do
      nil ->
        {:error, :not_found}

      pipeline_run ->
        exec_stages =
          Boreholes.list_document_exec_stages(pipeline_run.document_id, %{
            "run_id" => pipeline_run.id
          })

        report = Boreholes.get_report(pipeline_run.id)

        render(conn, :show,
          pipeline_run: pipeline_run,
          exec_stages: exec_stages,
          report: report
        )
    end
  end

  @doc """
  Updates a pipeline run's status, reported by the pipeline when the whole run finishes:
  `"completed"` or `"failed"`.
  """
  def update_status(conn, %{"id" => id, "status" => status}) do
    with %PipelineRun{} = pipeline_run <- Boreholes.get_pipeline_run(id),
         {:ok, pipeline_run} <- Boreholes.update_pipeline_run_status(pipeline_run, status) do
      exec_stages =
        Boreholes.list_document_exec_stages(pipeline_run.document_id, %{
          "run_id" => pipeline_run.id
        })

      report = Boreholes.get_report(pipeline_run.id)

      render(conn, :show,
        pipeline_run: pipeline_run,
        exec_stages: exec_stages,
        report: report
      )
    else
      nil -> {:error, :not_found}
      {:error, changeset} -> {:error, changeset}
    end
  end
end
