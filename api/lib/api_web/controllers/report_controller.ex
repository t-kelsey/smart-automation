defmodule ApiWeb.ReportController do
  @moduledoc """
  Pipeline run reports for the `claude_test/` pipeline (ADR-0034). Debug/internal only, never
  consumed by `web/`'s public pages.
  """
  use ApiWeb, :controller

  alias Api.Boreholes

  action_fallback ApiWeb.FallbackController

  @doc """
  Records one pipeline run's report (`report.json` as-is). Body: `{"document_id", "run_id",
  "data"}`.
  """
  def create(conn, params) do
    with {:ok, report} <- Boreholes.create_report(params) do
      conn
      |> put_status(:created)
      |> render(:show, report: report)
    end
  end
end
