defmodule Api.Boreholes.BoreholeTest do
  use Api.DataCase, async: true

  alias Api.Boreholes.Borehole

  @valid_attrs %{
    name: "B 1/59 Schönberg"
  }

  test "changeset with valid attributes is valid" do
    changeset = Borehole.changeset(%Borehole{}, @valid_attrs)
    assert changeset.valid?
  end

  test "changeset requires name" do
    changeset = Borehole.changeset(%Borehole{}, %{})

    refute changeset.valid?
    assert %{name: ["can't be blank"]} = errors_on(changeset)
  end

  test "changeset defaults verified to false" do
    changeset = Borehole.changeset(%Borehole{}, @valid_attrs)
    assert get_field(changeset, :verified) == false
  end

  test "changeset rejects negative total_depth_m" do
    changeset = Borehole.changeset(%Borehole{}, Map.put(@valid_attrs, :total_depth_m, -1))

    refute changeset.valid?
    assert %{total_depth_m: ["must be greater than or equal to 0"]} = errors_on(changeset)
  end

  test "changeset rejects negative elevation_m" do
    changeset = Borehole.changeset(%Borehole{}, Map.put(@valid_attrs, :elevation_m, -1))

    refute changeset.valid?
    assert %{elevation_m: ["must be greater than or equal to 0"]} = errors_on(changeset)
  end

  test "changeset accepts non-negative total_depth_m and elevation_m" do
    attrs = Map.merge(@valid_attrs, %{total_depth_m: 12.5, elevation_m: 0})
    changeset = Borehole.changeset(%Borehole{}, attrs)
    assert changeset.valid?
  end

  test "changeset accepts external_id, end_date, and borehole_length_m" do
    attrs =
      Map.merge(@valid_attrs, %{
        external_id: "BH_AB01",
        end_date: ~D[2014-08-05],
        borehole_length_m: 18.3
      })

    changeset = Borehole.changeset(%Borehole{}, attrs)
    assert changeset.valid?
    assert get_field(changeset, :external_id) == "BH_AB01"
  end

  test "changeset rejects negative borehole_length_m" do
    changeset = Borehole.changeset(%Borehole{}, Map.put(@valid_attrs, :borehole_length_m, -1))

    refute changeset.valid?
    assert %{borehole_length_m: ["must be greater than or equal to 0"]} = errors_on(changeset)
  end

  test "changeset accepts groundwater_level_m" do
    changeset = Borehole.changeset(%Borehole{}, Map.put(@valid_attrs, :groundwater_level_m, 4.2))
    assert changeset.valid?
  end

  test "changeset rejects negative groundwater_level_m" do
    changeset = Borehole.changeset(%Borehole{}, Map.put(@valid_attrs, :groundwater_level_m, -1))

    refute changeset.valid?
    assert %{groundwater_level_m: ["must be greater than or equal to 0"]} = errors_on(changeset)
  end

  test "changeset accepts an open metadata map" do
    attrs = Map.put(@valid_attrs, :metadata, %{"rig_type" => "Hanjin D & B - 8D"})
    changeset = Borehole.changeset(%Borehole{}, attrs)

    assert changeset.valid?
    assert get_field(changeset, :metadata) == %{"rig_type" => "Hanjin D & B - 8D"}
  end
end
