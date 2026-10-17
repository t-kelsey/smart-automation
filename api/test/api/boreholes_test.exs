defmodule Api.BoreholesTest do
  use Api.DataCase, async: true

  alias Api.Boreholes
  alias Api.Boreholes.Borehole
  alias Api.Boreholes.BoreholeLayer
  alias Api.Boreholes.Document
  alias Api.Boreholes.SearchQuery

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

  describe "list_boreholes/1 with q (search query language)" do
    test "bare words match name, external id and place; name hits rank first" do
      by_place = insert_borehole(%{name: "P1", place: "Kiesgrube"})
      by_name = insert_borehole(%{name: "Kiesgrube Nord"})
      by_external_id = insert_borehole(%{name: "X", external_id: "KIES-7"})
      insert_borehole(%{name: "Unrelated", client: "Kies AG", purpose: "Kies"})

      assert ids(Boreholes.list_boreholes(%{q: "kies"})) == [
               by_name.id,
               by_external_id.id,
               by_place.id
             ]
    end

    test "all terms must match" do
      both = insert_borehole(%{name: "B 1/59", place: "Stuttgart"})
      insert_borehole(%{name: "B 2/60", place: "Basel"})

      assert ids(Boreholes.list_boreholes(%{q: "B stuttgart"})) == [both.id]
    end

    test "name: and place: restrict the columns" do
      named = insert_borehole(%{name: "Bern 1", place: "Thun"})
      placed = insert_borehole(%{name: "T 1", place: "Bern"})

      assert ids(Boreholes.list_boreholes(%{q: "name:bern"})) == [named.id]
      assert ids(Boreholes.list_boreholes(%{q: "location:bern"})) == [placed.id]
    end

    test "quoted phrases and comma alternatives" do
      a = insert_borehole(%{name: "B 1/59", place: "Bern"})
      b = insert_borehole(%{name: "B 159", place: "Basel"})
      insert_borehole(%{name: "C", place: "Zürich"})

      assert ids(Boreholes.list_boreholes(%{q: ~s("B 1/59")})) == [a.id]

      assert ids(Boreholes.list_boreholes(%{q: "place:bern,basel", sort: {:name, :asc}})) ==
               [a.id, b.id]
    end

    test "negated terms exclude matches and keep rows without the value" do
      bern = insert_borehole(%{name: "A", place: "Bern"})
      no_place = insert_borehole(%{name: "B"})
      old = insert_borehole(%{name: "C", place: "Basel", drilled_at: ~D[1959-06-12]})

      assert ids(Boreholes.list_boreholes(%{q: "-place:basel"})) == [bern.id, no_place.id]
      assert ids(Boreholes.list_boreholes(%{q: "-1959"})) == [bern.id, no_place.id]
      assert ids(Boreholes.list_boreholes(%{q: "-place:bern"})) == [no_place.id, old.id]
    end

    test "dates: years, months, days, ranges and comparisons" do
      d1959 = insert_borehole(%{name: "A", drilled_at: ~D[1959-06-12]})
      d1975 = insert_borehole(%{name: "B", drilled_at: ~D[1975-01-31]})
      d2001 = insert_borehole(%{name: "C", drilled_at: ~D[2001-12-01]})
      insert_borehole(%{name: "D"})

      search = &ids(Boreholes.list_boreholes(%{q: &1, sort: {:name, :asc}}))

      assert search.("1959") == [d1959.id]
      assert search.("date:1959-06") == [d1959.id]
      assert search.("date:12.06.1959") == [d1959.id]
      assert search.("date:1959-06-13") == []
      assert search.("1950..1980") == [d1959.id, d1975.id]
      assert search.("date:1975..") == [d1975.id, d2001.id]
      assert search.("date:..1975-01") == [d1959.id, d1975.id]
      assert search.("date:>1975") == [d2001.id]
      assert search.("date:>=1975") == [d1975.id, d2001.id]
      assert search.("before:1975") == [d1959.id]
      assert search.("after:1959 before:2000") == [d1975.id]
      assert search.("date:1959,2001") == [d1959.id, d2001.id]
    end

    test "a quoted year is text, not a date" do
      named = insert_borehole(%{name: "Station 1959"})
      insert_borehole(%{name: "Other", drilled_at: ~D[1959-01-01]})

      assert ids(Boreholes.list_boreholes(%{q: ~s("1959")})) == [named.id]
    end

    test "treats LIKE wildcards in the query literally" do
      insert_borehole(%{name: "Anything"})
      assert %{total: 0} = Boreholes.list_boreholes(%{q: "%"})
    end

    test "returns a score per entry" do
      insert_borehole(%{name: "Kiesgrube"})
      assert [%{score: score}] = Boreholes.list_boreholes(%{q: "kies"}).entries
      assert score > 0
    end
  end

  describe "suggest_query/1" do
    setup do
      insert_borehole(%{name: "B 1/59 Schönberg", place: "Stuttgart"})
      insert_borehole(%{name: "KB 3", place: "Freiburg im Breisgau"})
      :ok
    end

    defp suggest(q), do: Boreholes.suggest_query(SearchQuery.parse!(q))

    test "replaces misspelt words with the most similar word of the searched columns" do
      assert suggest("Stutgart") == "Stuttgart"
      assert suggest("place:Freiburgg 1959") == "place:Freiburg 1959"
      assert suggest("name:Schonberg") == "name:Schönberg"
    end

    test "corrects unknown field keys" do
      assert suggest("plase:Stuttgart") == "place:Stuttgart"
    end

    test "keeps values that occur, quoted, negated and short values" do
      assert suggest("stuttgart") == nil
      assert suggest(~s("Stutgart")) == nil
      assert suggest("-Stutgart") == nil
      assert suggest("xy") == nil
    end

    test "returns nil when no similar word exists" do
      assert suggest("qwertzuiop") == nil
    end
  end

  describe "complete_query/2" do
    setup do
      insert_borehole(%{name: "B 1/59 Schönberg", place: "Stuttgart"})
      insert_borehole(%{name: "KB 3", place: "Freiburg im Breisgau"})
      insert_borehole(%{name: "Stuttgart-Ost", place: "Esslingen"})
      :ok
    end

    defp completions(q, limit \\ 8),
      do: Enum.map(Boreholes.complete_query(q, limit), &{&1.value, &1.kind, &1.query})

    test "completes names and places, values starting with the text first" do
      assert completions("stutt") == [
               {"Stuttgart", :place, "Stuttgart "},
               {"Stuttgart-Ost", :name, "Stuttgart-Ost "}
             ]
    end

    test "completes despite a typo through trigram similarity" do
      assert {"Stuttgart", :place, "place:Stuttgart "} in completions("place:Stutgart")
    end

    test "keeps the rest of the query, the key, negation and earlier alternatives" do
      assert completions("1959 -place:Esslingen,Frei") == [
               {"Freiburg im Breisgau", :place, ~s(1959 -place:Esslingen,"Freiburg im Breisgau" )}
             ]
    end

    test "name: only completes names, and values with spaces are quoted" do
      assert completions("name:schön") == [
               {"B 1/59 Schönberg", :name, ~s(name:"B 1/59 Schönberg" )}
             ]
    end

    test "completes keys" do
      assert [{"place:", :key, "place:"} | _] = completions("pla")
    end

    test "completes nothing after a space, for dates, or for one letter" do
      assert completions("stuttgart ") == []
      assert completions("date:19") == []
      assert completions("x") == []
    end

    test "returns at most limit entries" do
      assert length(completions("s", 1)) <= 1
      assert length(completions("st", 1)) == 1
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
