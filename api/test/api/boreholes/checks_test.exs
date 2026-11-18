defmodule Api.Boreholes.ChecksTest do
  use Api.DataCase, async: true

  alias Api.Boreholes
  alias Api.Boreholes.{Checks, FieldFlag}

  defp create(borehole, layers) do
    {:ok, borehole} = Boreholes.create_borehole(Map.put(borehole, "name", "BH"), layers)
    borehole
  end

  defp flags(borehole, open? \\ true) do
    from(f in FieldFlag, where: f.borehole_id == ^borehole.id and is_nil(f.resolved_at) == ^open?)
    |> Repo.all()
  end

  test "flags groundwater below the bottom and overlaps; only own rule flags are synced" do
    borehole =
      create(
        %{"x" => 8, "y" => 48, "epsg" => 4326, "elevation_m" => 1, "groundwater_level_m" => 9},
        [
          %{"depth_from_m" => 0, "depth_to_m" => 3, "petrography" => "Kies"},
          %{"depth_from_m" => 2, "depth_to_m" => 5, "petrography" => "Sand"}
        ]
      )

    pipeline_flag =
      Repo.insert!(%FieldFlag{
        borehole_id: borehole.id,
        field: "location",
        severity: "warning",
        message: "guessed",
        origin: "rule",
        code: "epsg_guessed"
      })

    assert flags(borehole) |> Enum.map(& &1.code) |> Enum.sort() ==
             ~w(epsg_guessed groundwater_below_bottom layer_overlap)

    # a second sync neither duplicates nor touches flags
    before = flags(borehole) |> Enum.map(& &1.id) |> Enum.sort()
    Checks.sync(borehole.id)
    assert flags(borehole) |> Enum.map(& &1.id) |> Enum.sort() == before

    Repo.update_all(from(b in Api.Boreholes.Borehole, where: b.id == ^borehole.id),
      set: [groundwater_level_m: 1]
    )

    Checks.sync(borehole.id)

    assert flags(borehole) |> Enum.map(& &1.code) |> Enum.sort() == ~w(epsg_guessed layer_overlap)

    assert [%{code: "groundwater_below_bottom", resolved_by: "rule", resolved_at: %DateTime{}}] =
             flags(borehole, false)

    assert Repo.reload!(pipeline_flag).resolved_at == nil
  end

  test "total depth within 5 cm of the last layer is fine, a missing petrography names the original" do
    borehole =
      create(
        %{"x" => 8, "y" => 48, "epsg" => 4326, "elevation_m" => 1, "total_depth_m" => 5.04},
        [
          %{
            "depth_from_m" => 0,
            "depth_to_m" => 5,
            "metadata" => %{"petrography_original" => "Torf"}
          }
        ]
      )

    assert [%{code: "missing_petrography", message: message}] = flags(borehole)
    assert message =~ "Torf"
  end
end
