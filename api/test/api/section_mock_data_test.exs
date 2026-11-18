defmodule Api.SectionMockDataTest do
  use Api.DataCase, async: true

  alias Api.Boreholes

  test "inserts ten located boreholes with contiguous layers, and replaces them on re-run" do
    {0, created} = Api.SectionMockData.insert()
    assert length(created) == 10

    for borehole <- created do
      borehole = Boreholes.get_borehole(borehole.id)
      assert %Geo.Point{srid: 4326} = borehole.location
      assert borehole.metadata["source"] == "section-mock"

      layers = borehole.borehole_layers
      assert hd(layers).depth_from_m == Decimal.new("0.0")

      # No gaps or overlaps between layers, and the total depth is the last layer's bottom.
      for [upper, lower] <- Enum.chunk_every(layers, 2, 1, :discard) do
        assert Decimal.equal?(upper.depth_to_m, lower.depth_from_m)
      end

      assert Decimal.equal?(List.last(layers).depth_to_m, borehole.total_depth_m)
    end

    {10, _} = Api.SectionMockData.insert()
  end

  test "contains the pinch-out, the lens and the sand-to-gravel change" do
    {_, created} = Api.SectionMockData.insert()

    texts =
      Enum.map(created, fn b ->
        Boreholes.get_borehole(b.id).borehole_layers
        |> Enum.map(& &1.petrography)
        |> Enum.join("|")
      end)

    assert Enum.map(texts, &(&1 =~ "Torf")) ==
             [true, true, true, true, false, false, false, false, false, false]

    assert Enum.map(texts, &(&1 =~ "Schluff, tonig")) ==
             [false, false, false, false, true, true, true, false, false, false]

    assert Enum.map(texts, &(&1 =~ "Sand, schwach kiesig")) ==
             [true, true, true, true, true, false, false, false, false, false]

    assert Enum.map(texts, &(&1 =~ "Kies, sandig")) ==
             [false, false, false, false, false, true, true, true, true, true]
  end
end
