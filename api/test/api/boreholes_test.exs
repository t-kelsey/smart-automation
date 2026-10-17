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

  defp ids(%{entries: entries}), do: Enum.map(entries, & &1.borehole.id)

  describe "list_boreholes/1" do
    test "without filters, returns all boreholes sorted by name" do
      b =
        insert_borehole(%{name: "B", location: %Geo.Point{coordinates: {10.0, 50.0}, srid: 4326}})

      a =
        insert_borehole(%{
          name: "A",
          location: %Geo.Point{coordinates: {100.0, 10.0}, srid: 4326}
        })

      assert %{total: 2} = result = Boreholes.list_boreholes()
      assert ids(result) == [a.id, b.id]
    end

    test "with a bbox, filters boreholes to those within the envelope" do
      inside =
        insert_borehole(%{
          name: "Inside",
          location: %Geo.Point{coordinates: {10.0, 50.0}, srid: 4326}
        })

      insert_borehole(%{
        name: "Outside",
        location: %Geo.Point{coordinates: {100.0, 10.0}, srid: 4326}
      })

      bbox = %{min_lon: 9.0, min_lat: 49.0, max_lon: 11.0, max_lat: 51.0}

      assert ids(Boreholes.list_boreholes(%{bbox: bbox})) == [inside.id]
    end

    test "pages with limit/offset and reports the total" do
      for name <- ~w(A B C D E), do: insert_borehole(%{name: name})

      result = Boreholes.list_boreholes(%{limit: 2, offset: 2})

      assert result.total == 5
      assert result.entries |> Enum.map(& &1.borehole.name) == ["C", "D"]
    end

    test "filters by verified, drilling date and depth" do
      match =
        insert_borehole(%{
          name: "Match",
          verified: true,
          drilled_at: ~D[1990-05-01],
          total_depth_m: Decimal.new("20")
        })

      insert_borehole(%{
        name: "Unverified",
        verified: false,
        drilled_at: ~D[1990-05-01],
        total_depth_m: Decimal.new("20")
      })

      insert_borehole(%{
        name: "Too old",
        verified: true,
        drilled_at: ~D[1950-01-01],
        total_depth_m: Decimal.new("20")
      })

      insert_borehole(%{
        name: "Too shallow",
        verified: true,
        drilled_at: ~D[1990-05-01],
        total_depth_m: Decimal.new("5")
      })

      filters = %{
        verified: true,
        drilled_from: ~D[1980-01-01],
        drilled_to: ~D[2000-01-01],
        min_depth: 10,
        max_depth: 30
      }

      assert ids(Boreholes.list_boreholes(filters)) == [match.id]
    end

    test "sorts by a field, with missing values last" do
      deep = insert_borehole(%{name: "Deep", total_depth_m: Decimal.new("50")})
      shallow = insert_borehole(%{name: "Shallow", total_depth_m: Decimal.new("5")})
      unknown = insert_borehole(%{name: "Unknown"})

      assert ids(Boreholes.list_boreholes(%{sort: {:total_depth_m, :desc}})) == [
               deep.id,
               shallow.id,
               unknown.id
             ]

      assert ids(Boreholes.list_boreholes(%{sort: {:total_depth_m, :asc}})) == [
               shallow.id,
               deep.id,
               unknown.id
             ]
    end
  end

  describe "list_boreholes/1 with q (search)" do
    test "matches by name and ranks name hits above layer hits" do
      by_layer = insert_borehole(%{name: "Other"})

      insert_layer(by_layer, %{
        position: 1,
        depth_from_m: 0,
        depth_to_m: 2,
        petrography: "Kies, sandig"
      })

      by_name = insert_borehole(%{name: "Kiesgrube Nord"})
      insert_borehole(%{name: "Unrelated"})

      assert [first, second] = Boreholes.list_boreholes(%{q: "kies"}).entries
      assert first.borehole.id == by_name.id
      assert second.borehole.id == by_layer.id
      assert first.score > second.score
      assert second.snippet == "Kies, sandig"
    end

    test "matches place, client and layer stratigraphy without duplicating the borehole" do
      borehole = insert_borehole(%{name: "Multi-layer"})
      insert_layer(borehole, %{position: 1, depth_from_m: 0, depth_to_m: 2, stratigraphy: "qh"})
      insert_layer(borehole, %{position: 2, depth_from_m: 2, depth_to_m: 4, stratigraphy: "qh"})
      by_place = insert_borehole(%{name: "P", place: "Stuttgart"})
      by_client = insert_borehole(%{name: "C", client: "Stadtwerke"})

      assert %{total: 1, entries: [%{borehole: %Borehole{id: id}, score: 2}]} =
               Boreholes.list_boreholes(%{q: "qh"})

      assert id == borehole.id
      assert ids(Boreholes.list_boreholes(%{q: "stuttgart"})) == [by_place.id]
      assert ids(Boreholes.list_boreholes(%{q: "stadtwerke"})) == [by_client.id]
    end

    test "treats LIKE wildcards in the query literally" do
      insert_borehole(%{name: "Anything"})
      assert %{total: 0} = Boreholes.list_boreholes(%{q: "%"})
    end
  end

  describe "get_borehole/1" do
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

      fetched = Boreholes.get_borehole(borehole.id)

      assert Enum.map(fetched.borehole_layers, & &1.position) == [1, 2]
      assert [%Document{id: doc_id}] = fetched.documents
      assert doc_id == document.id
    end

    test "returns nil for unknown or malformed ids" do
      assert Boreholes.get_borehole(Ecto.UUID.generate()) == nil
      assert Boreholes.get_borehole("not-a-uuid") == nil
    end
  end
end
