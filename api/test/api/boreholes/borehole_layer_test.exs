defmodule Api.Boreholes.BoreholeLayerTest do
  use Api.DataCase, async: true

  alias Api.Boreholes.BoreholeLayer

  @valid_attrs %{
    position: 1,
    depth_from_m: 0,
    depth_to_m: 2.5
  }

  test "changeset with valid attributes is valid" do
    changeset = BoreholeLayer.changeset(%BoreholeLayer{}, @valid_attrs)
    assert changeset.valid?
  end

  test "changeset requires position, depth_from_m and depth_to_m" do
    changeset = BoreholeLayer.changeset(%BoreholeLayer{}, %{})

    refute changeset.valid?

    assert %{
             position: ["can't be blank"],
             depth_from_m: ["can't be blank"],
             depth_to_m: ["can't be blank"]
           } = errors_on(changeset)
  end

  test "changeset rejects depth_to_m not greater than depth_from_m" do
    changeset =
      BoreholeLayer.changeset(%BoreholeLayer{}, %{@valid_attrs | depth_from_m: 2, depth_to_m: 2})

    refute changeset.valid?
    assert %{depth_to_m: ["must be greater than depth_from_m"]} = errors_on(changeset)
  end

  test "changeset rejects negative depth_from_m or depth_to_m" do
    changeset = BoreholeLayer.changeset(%BoreholeLayer{}, %{@valid_attrs | depth_from_m: -1})

    refute changeset.valid?
    assert %{depth_from_m: ["must be greater than or equal to 0"]} = errors_on(changeset)
  end

  test "changeset accepts an open metadata map" do
    attrs = Map.put(@valid_attrs, :metadata, %{"rqd_percent" => 85})
    changeset = BoreholeLayer.changeset(%BoreholeLayer{}, attrs)

    assert changeset.valid?
    assert get_field(changeset, :metadata) == %{"rqd_percent" => 85}
  end
end
