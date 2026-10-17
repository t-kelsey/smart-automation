defmodule ApiWeb.ExecStageController do
  @moduledoc """
  Pipeline step tracking for the `claude_test/` pipeline (ADR-0034). Debug/internal only, never
  consumed by `web/`'s public pages.
  """
  use ApiWeb, :controller

  alias Api.Boreholes

  action_fallback ApiWeb.FallbackController

  @doc """
  Records one pipeline step execution. Body: `{"type", "run_id", "position", "data",
  "document_ids"}` — `document_ids` needs at least one entry. Append-only: rerunning a step adds
  a new row rather than replacing the previous one.
  """
  def create(conn, params) do
    with {:ok, exec_stage} <- Boreholes.create_exec_stage(params) do
      conn
      |> put_status(:created)
      |> render(:show, exec_stage: exec_stage)
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
