defmodule Mix.Tasks.Boreholes.SectionMock do
  @shortdoc "Insert ten test boreholes along a line in Stuttgart-Feuerbach (section view)"

  @moduledoc """
  Inserts the ten boreholes of `Api.SectionMockData` (`SL-01` to `SL-10`) along a ~1 km line in
  Stuttgart-Feuerbach, for testing the map's section view and the layer correlation. Earlier
  section test rows (`metadata.source = "section-mock"`) are replaced; other data stays.

      mix boreholes.section_mock
  """

  use Mix.Task

  @impl Mix.Task
  def run(_args) do
    Mix.Task.run("app.start")

    {removed, created} = Api.SectionMockData.insert()

    Mix.shell().info(
      "Removed #{removed} and created #{length(created)} section test boreholes along the line " <>
        "9.1340, 48.8050 → 9.1475, 48.8030 (lon, lat):"
    )

    for {name, lon, lat, along, offset} <- Api.SectionMockData.positions() do
      Mix.shell().info("  #{name}  #{lon}, #{lat}  (#{along} m along, #{offset} m off the line)")
    end
  end
end
