defmodule ApiWeb.DocumentJSON do
  alias ApiWeb.BoreholeJSON

  @doc "Renders an uploaded document."
  def create(%{document: document}), do: %{data: BoreholeJSON.document(document)}

  @doc "Renders a single document with the (id, name) of each borehole it belongs to."
  def show(%{document: document}) do
    boreholes = Enum.map(document.boreholes, &%{id: &1.id, name: &1.name})
    %{data: Map.put(BoreholeJSON.document(document), :boreholes, boreholes)}
  end
end
