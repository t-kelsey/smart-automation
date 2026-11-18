defmodule Api.SectionMockData do
  @moduledoc """
  Ten invented boreholes along a straight line in Stuttgart-Feuerbach, for testing the map's
  section (side) view and the layer correlation between neighbouring boreholes.

  The line runs from 9.1340, 48.8050 to 9.1475, 48.8030 (WGS84, about 1015 m, west-north-west to
  east-south-east). The boreholes `SL-01` to `SL-10` stand at irregular distances along it
  (0–1000 m) and up to 40 m to either side, so they all fall inside a 100 m corridor around it.

  Layers, top to bottom, chosen to exercise the correlation:

    * topsoil (Mutterboden) in every borehole
    * peat (Torf) that thins out eastwards and is gone from `SL-05` on (pinch-out)
    * loess loam (Lösslehm) in every borehole, thickening eastwards
    * sand (`SL-01`–`SL-05`) that turns into gravel (`SL-06`–`SL-10`) at the same level: a
      material change the "same main material" rule must not connect
    * clay (Ton) in every borehole, thickening eastwards, with a silt lens (Schluff) inside it in
      `SL-05`–`SL-07` only
    * sandstone (Sandstein) at the base, its top dipping from 9.4 m to 14.8 m below the start

  Rows are marked `metadata.source = "section-mock"`; `insert/0` replaces earlier ones.
  """

  alias Api.Boreholes

  @source "section-mock"

  # {name, lon, lat, metres along the line, metres off the line}
  @positions [
    {"SL-01", 9.134036, 48.805105, 0, 12},
    {"SL-02", 9.135189, 48.804594, 95, -25},
    {"SL-03", 9.136818, 48.804656, 210, 8},
    {"SL-04", 9.137973, 48.804761, 290, 38},
    {"SL-05", 9.139544, 48.804041, 420, -15},
    {"SL-06", 9.141009, 48.804238, 520, 30},
    {"SL-07", 9.142634, 48.803675, 650, -5},
    {"SL-08", 9.143594, 48.803210, 730, -40},
    {"SL-09", 9.145636, 48.803460, 870, 20},
    {"SL-10", 9.147277, 48.802941, 1000, -10}
  ]

  # Thicknesses in metres per borehole (index 0 = SL-01).
  @peat [1.6, 1.1, 0.7, 0.3, 0, 0, 0, 0, 0, 0]
  @coarse [2.4, 2.6, 2.2, 2.8, 2.5, 2.3, 2.7, 2.4, 2.6, 2.2]
  @lens [0, 0, 0, 0, 0.7, 1.3, 0.8, 0, 0, 0]
  @sandstone [3.6, 4.0, 4.4, 3.8, 4.2, 5.0, 3.9, 4.6, 4.1, 4.5]

  @doc "The test boreholes' names and positions: `{name, lon, lat, along_m, offset_m}`."
  def positions, do: @positions

  @doc """
  Removes earlier section test boreholes and inserts the ten again. Returns the number removed and
  the created boreholes.
  """
  def insert do
    removed = Api.MockData.delete_source(@source)

    created =
      @positions
      |> Enum.with_index()
      |> Enum.map(fn {position, index} ->
        {borehole, layers} = borehole(position, index)
        {:ok, created} = Boreholes.create_borehole(borehole, layers)
        created
      end)

    {removed, created}
  end

  defp borehole({name, lon, lat, along, offset}, i) do
    layers = layers(i)
    total_depth = layers |> List.last() |> Map.fetch!("depth_to_m")

    borehole = %{
      "name" => "#{name} Feuerbach",
      "external_id" => name,
      "place" => "Stuttgart-Feuerbach",
      "purpose" => "Section test (#{along} m along the line, #{offset} m off it)",
      "drilling_method" => "Rammkernbohrung",
      "drilled_at" => Date.to_iso8601(Date.add(~D[1994-03-14], i * 9)),
      "elevation_m" => Float.round(312.0 - 1.2 * i, 1),
      "total_depth_m" => total_depth,
      "verified" => rem(i, 3) != 2,
      "x" => lon,
      "y" => lat,
      "epsg" => 4326,
      "source_coordinate_system" => "WGS84",
      "source_coordinate_raw" => "#{lat} N, #{lon} E",
      "metadata" => %{
        "source" => @source,
        "section_along_m" => along,
        "section_offset_m" => offset
      }
    }

    {borehole, layers}
  end

  # Builds the layer list top-down from the thicknesses; zero-thickness layers are left out.
  defp layers(i) do
    clay = 3.0 + 0.6 * i
    lens = Enum.at(@lens, i)
    coarse = if i <= 4, do: sand(), else: gravel()

    clay_layers =
      if lens > 0 do
        [
          {clay / 2, clay_layer()},
          {lens, {"Schluff, tonig, schwach feinsandig", "oliv", "km1"}},
          {clay / 2, clay_layer()}
        ]
      else
        [{clay, clay_layer()}]
      end

    [
      {0.4, {"Mutterboden, schwach tonig, humos", "dunkelbraun", "qh"}},
      {Enum.at(@peat, i), {"Torf, schwach zersetzt", "schwarz", "qh"}},
      {2.0 + 0.2 * i, {"Lösslehm, schwach feinsandig", "gelblichbraun", "qp"}},
      {Enum.at(@coarse, i), coarse}
    ]
    |> Kernel.++(clay_layers)
    |> Kernel.++([{Enum.at(@sandstone, i), {"Sandstein, verwittert", "grau", "km4"}}])
    |> Enum.reject(fn {thickness, _} -> thickness <= 0 end)
    |> Enum.map_reduce(0.0, fn {thickness, {petrography, color, stratigraphy}}, top ->
      bottom = Float.round(top + thickness, 2)

      layer = %{
        "depth_from_m" => Float.round(top, 2),
        "depth_to_m" => bottom,
        "petrography" => petrography,
        "color" => color,
        "stratigraphy" => stratigraphy
      }

      {layer, bottom}
    end)
    |> elem(0)
  end

  defp sand, do: {"Sand, schwach kiesig, schwach schluffig", "gelb", "qp"}
  defp gravel, do: {"Kies, sandig, schwach steinig", "gelb", "qp"}
  defp clay_layer, do: {"Ton, schluffig, steif", "violett", "km1"}
end
