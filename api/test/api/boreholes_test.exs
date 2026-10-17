defmodule Api.BoreholesTest do
  use Api.DataCase, async: true

  alias Api.Boreholes
  alias Api.Boreholes.Borehole
  alias Api.Boreholes.BoreholeLayer
  alias Api.Boreholes.Document

  defp insert_borehole(attrs) do
    %Borehole{}
    |> Borehole.changeset(attrs)
    |> Repo.insert!()
  end

  defp insert_layer(borehole, attrs) do
    %BoreholeLayer{}
    |> BoreholeLayer.changeset(attrs)
    |> Ecto.Changeset.put_change(:borehole_id, borehole.id)
    |> Repo.insert!()
  end

  defp insert_document(attrs) do
    %Document{}
    |> Document.changeset(attrs)
    |> Repo.insert!()
  end

  describe "list_boreholes/1" do
    test "without a bbox, returns all boreholes" do
      inside =
        insert_borehole(%{
          name: "Inside",
          location: %Geo.Point{coordinates: {10.0, 50.0}, srid: 4326}
        })

      outside =
        insert_borehole(%{
          name: "Outside",
          location: %Geo.Point{coordinates: {100.0, 10.0}, srid: 4326}
        })

      ids = Boreholes.list_boreholes() |> Enum.map(& &1.id)
      assert inside.id in ids
      assert outside.id in ids
    end

    test "with a bbox, filters boreholes to those within the envelope" do
      inside =
        insert_borehole(%{
          name: "Inside",
          location: %Geo.Point{coordinates: {10.0, 50.0}, srid: 4326}
        })

      outside =
        insert_borehole(%{
          name: "Outside",
          location: %Geo.Point{coordinates: {100.0, 10.0}, srid: 4326}
        })

      bbox = %{min_lon: 9.0, min_lat: 49.0, max_lon: 11.0, max_lat: 51.0}

      result_ids = Boreholes.list_boreholes(bbox) |> Enum.map(& &1.id)

      assert inside.id in result_ids
      refute outside.id in result_ids
    end
  end

  describe "get_borehole!/1" do
    test "preloads layers ordered by position and documents" do
      borehole = insert_borehole(%{name: "With Layers"})

      insert_layer(borehole, %{position: 2, depth_from_m: 2, depth_to_m: 4})
      insert_layer(borehole, %{position: 1, depth_from_m: 0, depth_to_m: 2})

      document = insert_document(%{original_filename: "scan.pdf", storage_path: "/tmp/scan.pdf"})

      borehole
      |> Repo.preload(:documents)
      |> Ecto.Changeset.change()
      |> Ecto.Changeset.put_assoc(:documents, [document])
      |> Repo.update!()

      fetched = Boreholes.get_borehole!(borehole.id)

      assert Enum.map(fetched.borehole_layers, & &1.position) == [1, 2]
      assert [%Document{id: doc_id}] = fetched.documents
      assert doc_id == document.id
    end
  end

  describe "search_boreholes/1" do
    test "matches by name" do
      match = insert_borehole(%{name: "Schönberg Hole"})
      insert_borehole(%{name: "Unrelated"})

      assert [%Borehole{id: id}] = Boreholes.search_boreholes("schönberg")
      assert id == match.id
    end

    test "matches by a layer's stratigraphy without duplicating the borehole" do
      borehole = insert_borehole(%{name: "Multi-layer"})
      insert_layer(borehole, %{position: 1, depth_from_m: 0, depth_to_m: 2, stratigraphy: "qh"})
      insert_layer(borehole, %{position: 2, depth_from_m: 2, depth_to_m: 4, stratigraphy: "qh"})

      insert_borehole(%{name: "Other"})

      assert [%Borehole{id: id}] = Boreholes.search_boreholes("qh")
      assert id == borehole.id
    end
  end
end
