defmodule ApiWeb.ReportJSON do
  @doc "Renders a single report."
  def show(%{report: report}) do
    %{
      data: %{
        id: report.id,
        document_id: report.document_id,
        run_id: report.run_id,
        data: report.data,
        inserted_at: report.inserted_at
      }
    }
  end
end
