defmodule ApiWeb.ExecStageController do
  @moduledoc """
  Pipeline step tracking (ADR-0034, lifecycle ADR-0040): the pipeline creates a stage (`new` or
  `running`) and reports its progress with `update` until it is `success`/`failed`/`stopped`.
  """
  use ApiWeb, :controller

  alias Api.Boreholes
  alias Api.Boreholes.ExecStage

  action_fallback ApiWeb.FallbackController

  @doc """
  Records one pipeline step execution. Body: `{"type", "run_id", "position", "document_ids"}`
  plus optional `"status"` (default `"new"`), `"data"`, `"error"`, `"model"`, `"effort"`,
  `"usage"` — `document_ids` needs at least one entry. Rerunning a step adds a new row rather
  than replacing the previous one.
  """
  def create(conn, params) do
    with {:ok, exec_stage} <- Boreholes.create_exec_stage(params) do
      conn
      |> put_status(:created)
      |> render(:show, exec_stage: exec_stage)
    end
  end

  @doc """
  Reports progress on a stage. Body: `{"status"}` plus optional `"data"`, `"error"`, `"model"`,
  `"effort"`, `"usage"`, `"started_at"`, `"finished_at"`, `"document_ids"` (linked in addition).
  404 if unknown; 422 if the stage has already finished.
  """
  def update(conn, %{"id" => id} = params) do
    with %ExecStage{} = exec_stage <- Boreholes.get_exec_stage(id) || {:error, :not_found},
         {:ok, exec_stage} <- Boreholes.update_exec_stage(exec_stage, Map.delete(params, "id")) do
      render(conn, :show, exec_stage: exec_stage)
    end
  end

  @doc "One exec_stage by id; 404 if unknown."
  def show(conn, %{"id" => id}) do
    case Boreholes.get_exec_stage(id) do
      nil -> {:error, :not_found}
      exec_stage -> render(conn, :show, exec_stage: exec_stage)
    end
  end

  @doc """
  Every exec_stage linked to a document, newest first. Optional `type`/`run_id` query filters.
  """
  def index(conn, %{"document_id" => document_id} = params) do
    filters = Map.take(params, ["type", "run_id"])
    exec_stages = Boreholes.list_document_exec_stages(document_id, filters)
    render(conn, :index, exec_stages: exec_stages)
  end
end
