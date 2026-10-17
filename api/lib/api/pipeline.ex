defmodule Api.Pipeline do
  @moduledoc """
  Hands pipeline runs to the extraction pipeline (`claude_test/`, ADR-0033/ADR-0035).

  The pipeline is an HTTP service configured by `PIPELINE_URL`. The webhook call carries no file
  bytes: it POSTs a small JSON body (`document_id`, `pipeline_id`, `config`) to `PIPELINE_URL`.
  The pipeline fetches the actual file itself via `GET /api/documents/:id/file`, keyed by
  `document_id` — the same mechanism it already uses for the split-out per-borehole PDFs it
  uploads mid-run through `POST /api/documents` (ADR-0034). That makes "pull the file by
  document_id" the one consistent way to get any document's bytes, original or split-out, instead
  of special-casing the initial trigger with a push.

  Note: this module is the generic webhook-submit client. `Api.Boreholes.PipelineRun` is the
  unrelated `pipeline_runs` schema (ADR-0035) — don't confuse the two.
  """

  require Logger

  alias Api.Boreholes
  alias Api.Boreholes.PipelineRun

  @doc "The configured pipeline endpoint, or `nil` if uploads are not processed."
  def url, do: Application.get_env(:api, :pipeline_url)

  @doc """
  Submits a pipeline run to the pipeline synchronously (ADR-0035): posts the run's `document_id`,
  `pipeline_id` (the pipeline run's id) and `config`, then sets the run's status to `"running"` on
  success or `"failed"` if the pipeline refuses it or cannot be reached. Leaves the status
  unchanged (`"new"`) if no pipeline is configured — uploads no longer auto-trigger processing
  (ADR-0035).
  """
  @spec submit_pipeline_run(PipelineRun.t()) :: {:ok, PipelineRun.t()}
  def submit_pipeline_run(%PipelineRun{} = pipeline_run) do
    if url() do
      case submit_run(pipeline_run) do
        :ok ->
          Boreholes.update_pipeline_run_status(pipeline_run, "running")

        {:error, reason} ->
          Logger.error(
            "pipeline run submit failed for run #{pipeline_run.id}: #{inspect(reason)}"
          )

          Boreholes.update_pipeline_run_status(pipeline_run, "failed")
      end
    else
      {:ok, pipeline_run}
    end
  end

  defp submit_run(%PipelineRun{} = pipeline_run) do
    options =
      [
        url: url(),
        json: %{
          document_id: pipeline_run.document_id,
          pipeline_id: pipeline_run.id,
          config: pipeline_run.config || %{}
        },
        retry: false,
        receive_timeout: 30_000
      ] ++ Application.get_env(:api, :pipeline_req_options, [])

    case Req.post(options) do
      {:ok, %Req.Response{status: status}} when status in 200..299 -> :ok
      {:ok, %Req.Response{status: status}} -> {:error, {:status, status}}
      {:error, reason} -> {:error, reason}
    end
  end
end
