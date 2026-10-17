defmodule ApiWeb.BoreholeControllerTest do
  use ApiWeb.ConnCase, async: true

  alias Api.Boreholes.Borehole
  alias Api.Boreholes.BoreholeLayer
  alias Api.Boreholes.Document
  alias Api.Repo

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

  defp attach_document(borehole, document) do
    {:ok, _links} = Api.Boreholes.attach_documents(borehole, document)
  end

  describe "GET /api/boreholes" do
    test "returns a GeoJSON FeatureCollection", %{conn: conn} do
      insert_borehole(%{
        name: "Inside",
        location: %Geo.Point{coordinates: {10.0, 50.0}, srid: 4326}
      })

      conn = get(conn, ~p"/api/boreholes")

      assert %{"type" => "FeatureCollection", "features" => features} = json_response(conn, 200)
      assert [%{"type" => "Feature", "geometry" => _, "properties" => _}] = features
    end

    test "filters by bbox", %{conn: conn} do
      inside =
        insert_borehole(%{
          name: "Inside",
          location: %Geo.Point{coordinates: {10.0, 50.0}, srid: 4326}
        })

      insert_borehole(%{
        name: "Outside",
        location: %Geo.Point{coordinates: {100.0, 10.0}, srid: 4326}
      })

      conn = get(conn, ~p"/api/boreholes?bbox=9,49,11,51")

      assert %{"features" => [feature]} = json_response(conn, 200)
      assert feature["properties"]["id"] == inside.id
    end

    test "pages, sorts and filters, and reports the total", %{conn: conn} do
      for {name, depth} <- [{"A", "10"}, {"B", "30"}, {"C", "20"}, {"D", "5"}] do
        insert_borehole(%{name: name, total_depth_m: Decimal.new(depth), verified: name != "D"})
      end

      conn = get(conn, ~p"/api/boreholes?verified=true&sort=-total_depth_m&limit=2&offset=0")

      assert %{"total" => 3, "limit" => 2, "offset" => 0, "features" => features} =
               json_response(conn, 200)

      assert Enum.map(features, & &1["properties"]["name"]) == ["B", "C"]
    end

    test "view=points returns only id, name and verified", %{conn: conn} do
      insert_borehole(%{name: "P", purpose: "secret-ish detail"})

      assert %{"features" => [%{"properties" => props}]} =
               json_response(get(conn, ~p"/api/boreholes?view=points"), 200)

      assert Map.keys(props) |> Enum.sort() == ["id", "name", "verified"]
    end

    test "returns 400 for an invalid sort or limit", %{conn: conn} do
      assert %{"errors" => %{"detail" => "invalid sort"}} =
               json_response(get(conn, ~p"/api/boreholes?sort=nope"), 400)

      assert %{"errors" => %{"detail" => "invalid limit"}} =
               json_response(get(conn, ~p"/api/boreholes?limit=0"), 400)
    end

    test "returns 400 for a malformed bbox", %{conn: conn} do
      conn = get(conn, ~p"/api/boreholes?bbox=not-a-bbox")

      assert %{"errors" => %{"detail" => _}} = json_response(conn, 400)
    end
  end

  describe "GET /api/boreholes/:id" do
    test "returns the detail shape with layers/documents, excluding confidential fields", %{
      conn: conn
    } do
      borehole = insert_borehole(%{name: "Detail Hole"})
      insert_layer(borehole, %{position: 1, depth_from_m: 0, depth_to_m: 2})

      document =
        insert_document(%{
          original_filename: "scan.pdf",
          storage_path: "/secret/path/scan.pdf",
          raw_extraction: %{"secret" => "value"}
        })

      attach_document(borehole, document)

      conn = get(conn, ~p"/api/boreholes/#{borehole.id}")

      assert %{"data" => data} = json_response(conn, 200)
      assert data["id"] == borehole.id
      assert [%{"position" => 1}] = data["layers"]

      assert [%{"id" => doc_id, "original_filename" => "scan.pdf", "role" => "original"}] =
               data["documents"]

      assert doc_id == document.id

      body = response(conn, 200)
      refute body =~ "storage_path"
      refute body =~ "raw_extraction"
      refute body =~ "secret"
    end

    test "returns a JSON 404 for a nonexistent or malformed id", %{conn: conn} do
      conn1 = get(conn, ~p"/api/boreholes/#{Ecto.UUID.generate()}")
      assert %{"errors" => %{"detail" => "Not Found"}} = json_response(conn1, 404)

      conn2 = get(conn, ~p"/api/boreholes/not-a-uuid")
      assert %{"errors" => %{"detail" => "Not Found"}} = json_response(conn2, 404)
    end

    test "includes place, client and document details", %{conn: conn} do
      borehole = insert_borehole(%{name: "Hole", place: "Basel", client: "Stadtwerke"})

      document =
        insert_document(%{
          original_filename: "a.pdf",
          storage_path: "x.pdf",
          page_count: 3,
          size_bytes: 1234
        })

      attach_document(borehole, document)

      assert %{"data" => data} = json_response(get(conn, ~p"/api/boreholes/#{borehole.id}"), 200)
      assert %{"place" => "Basel", "client" => "Stadtwerke"} = data
      assert [%{"page_count" => 3, "size_bytes" => 1234, "has_file" => false}] = data["documents"]
    end
  end

  describe "GET /api/boreholes/search" do
    test "matches by name and by stratigraphy", %{conn: conn} do
      by_name = insert_borehole(%{name: "Schönberg Hole"})

      by_strat = insert_borehole(%{name: "Other"})
      insert_layer(by_strat, %{position: 1, depth_from_m: 0, depth_to_m: 2, stratigraphy: "qh"})

      insert_borehole(%{name: "Unrelated"})

      conn1 = get(conn, ~p"/api/boreholes/search?q=sch%C3%B6nberg")
      assert %{"features" => [feature1]} = json_response(conn1, 200)
      assert feature1["properties"]["id"] == by_name.id

      conn2 = get(conn, ~p"/api/boreholes/search?q=qh")
      assert %{"features" => [feature2]} = json_response(conn2, 200)
      assert feature2["properties"]["id"] == by_strat.id
    end

    test "returns score and snippet per feature", %{conn: conn} do
      borehole = insert_borehole(%{name: "Other"})

      insert_layer(borehole, %{
        position: 1,
        depth_from_m: 0,
        depth_to_m: 2,
        petrography: "Ton, steif"
      })

      conn = get(conn, ~p"/api/boreholes/search?q=ton")

      assert %{"total" => 1, "features" => [%{"score" => 1, "snippet" => "Ton, steif"}]} =
               json_response(conn, 200)
    end
  end
end
