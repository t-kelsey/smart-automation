defmodule ApiWeb.DocumentJSON do
  alias ApiWeb.BoreholeJSON

  @doc "Renders an uploaded document."
  def create(%{document: document}), do: %{data: BoreholeJSON.document(document)}

  @doc "Renders the documents found by checksum, with their borehole count and pipeline runs."
  def index(%{entries: entries}) do
    %{
      data:
        for %{document: d, borehole_count: count, pipeline_runs: runs} <- entries do
          %{
            id: d.id,
            original_filename: d.original_filename,
            inserted_at: d.inserted_at,
            borehole_count: count,
            pipeline_runs:
              Enum.map(runs, &%{id: &1.id, status: &1.status, inserted_at: &1.inserted_at})
          }
        end
    }
  end

  @doc "Renders a single document with the (id, name) of each borehole it belongs to."
  def show(%{document: document}) do
    boreholes = Enum.map(document.boreholes, &%{id: &1.id, name: &1.name})
    %{data: Map.put(BoreholeJSON.document(document), :boreholes, boreholes)}
  end
end
