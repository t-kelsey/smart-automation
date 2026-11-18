defmodule ApiWeb.ReviewControllerTest do
  use ApiWeb.ConnCase, async: true

  defp create(conn, extra \\ %{}) do
    body =
      Map.merge(
        %{
          "borehole" => %{
            "name" => "BH 1",
            "x" => 8.0,
            "y" => 48.0,
            "epsg" => 4326,
            "elevation_m" => 100,
            "total_depth_m" => 5,
            "sources" => %{"elevation_m" => %{"document_id" => nil, "page" => 1, "box" => nil}}
          },
          "layers" => [
            %{"depth_from_m" => 0, "depth_to_m" => 2, "petrography" => "Kies"},
            %{"depth_from_m" => 2, "depth_to_m" => 5, "petrography" => "Sand"}
          ],
          "flags" => [],
          "edits" => []
        },
        extra
      )

    conn |> post(~p"/api/boreholes", body) |> json_response(201) |> Map.fetch!("data")
  end

  defp codes(data, open? \\ true) do
    for %{"code" => code, "resolved_at" => at} <- data["flags"], is_nil(at) == open?, do: code
  end

  defp layer_ids(data), do: Enum.map(data["layers"], & &1["id"])

  describe "POST /api/boreholes with review data" do
    test "stores sources, flags and validator edits by layer position", %{conn: conn} do
      doc = %{"document_id" => Ecto.UUID.generate(), "page" => 2, "box" => [0.1, 0.2, 0.3, 0.4]}

      data =
        create(conn, %{
          "layers" => [
            %{"depth_from_m" => 0, "depth_to_m" => 5, "petrography" => "Kies", "source" => doc}
          ],
          "flags" => [
            %{
              "field" => "depth_to_m",
              "layer_position" => 1,
              "severity" => "warning",
              "message" => "unsure",
              "origin" => "validator"
            },
            %{
              "field" => "place",
              "severity" => "error",
              "message" => "?",
              "origin" => "validator"
            }
          ],
          "edits" => [
            %{
              "field" => "depth_to_m",
              "layer_position" => 1,
              "old_value" => 4.8,
              "new_value" => 5,
              "reason" => "re-read"
            },
            %{"field" => "name", "old_value" => nil, "new_value" => "BH 1"}
          ]
        })

      [layer] = data["layers"]
      assert layer["source"] == doc
      assert data["sources"]["elevation_m"]["page"] == 1
      assert data["open_flag_count"] == 2

      assert [%{"layer_id" => layer_id, "origin" => "validator"}, %{"layer_id" => nil}] =
               data["flags"]

      assert layer_id == layer["id"]

      assert [
               %{
                 "field" => "name",
                 "old_value" => nil,
                 "new_value" => "BH 1",
                 "source" => "validator"
               },
               %{"old_value" => 4.8, "new_value" => 5, "layer_id" => ^layer_id}
             ] = data["edits"] |> Enum.sort_by(& &1["field"], :desc)
    end

    test "an unknown layer_position is rejected", %{conn: conn} do
      body = %{
        "borehole" => %{"name" => "X"},
        "flags" => [
          %{
            "field" => "a",
            "layer_position" => 9,
            "severity" => "error",
            "message" => "m",
            "origin" => "rule"
          }
        ]
      }

      assert %{"errors" => %{"detail" => detail}} =
               conn |> post(~p"/api/boreholes", body) |> json_response(400)

      assert detail =~ "layer_position"
    end

    test "runs the checks and renumbers layers by depth", %{conn: conn} do
      data =
        create(conn, %{
          "borehole" => %{"name" => "BH"},
          "layers" => [
            %{"depth_from_m" => 3, "depth_to_m" => 4, "petrography" => nil},
            %{"depth_from_m" => 0, "depth_to_m" => 2, "petrography" => "Kies"}
          ]
        })

      assert Enum.map(data["layers"], & &1["position"]) == [1, 2]
      assert Enum.map(data["layers"], & &1["depth_from_m"]) == ["0", "3"]

      assert Enum.sort(codes(data)) ==
               Enum.sort(~w(layer_gap missing_elevation missing_location missing_petrography))
    end
  end

  describe "PATCH /api/boreholes/:id" do
    test "edits fields, records history, resolves flags and reruns the checks", %{conn: conn} do
      data = create(conn, %{"borehole" => %{"name" => "BH", "total_depth_m" => 9}})
      assert "total_depth_mismatch" in codes(data)

      data =
        conn
        |> patch(~p"/api/boreholes/#{data["id"]}", %{
          "borehole" => %{"total_depth_m" => 5, "name" => "BH"}
        })
        |> json_response(200)
        |> Map.fetch!("data")

      refute "total_depth_mismatch" in codes(data)

      assert [
               %{
                 "field" => "total_depth_m",
                 "old_value" => 9.0,
                 "new_value" => 5.0,
                 "source" => "human"
               }
             ] = data["edits"]

      assert %{"resolved_by" => "human"} =
               Enum.find(data["flags"], &(&1["code"] == "total_depth_mismatch"))
    end

    test "reprojects x/y/epsg and keeps the history reversible", %{conn: conn} do
      data = create(conn)
      id = data["id"]
      %{"coordinates" => [lon, lat]} = patch_location(conn, id, 8.5, 48.5, 4326)["location"]
      assert {lon, lat} == {8.5, 48.5}

      data = patch_location(conn, id, 9.0, 49.0, 4326)

      assert [
               %{"field" => "location", "old_value" => %{"x" => 8.5, "y" => 48.5, "epsg" => 4326}} =
                 edit
               | _
             ] =
               data["edits"]

      assert edit["new_value"] == %{"x" => 9.0, "y" => 49.0, "epsg" => 4326}

      data =
        conn
        |> post(~p"/api/boreholes/#{id}/edits/#{edit["id"]}/revert")
        |> json_response(200)
        |> Map.fetch!("data")

      assert data["location"]["coordinates"] == [8.5, 48.5]
      assert [%{"field" => "location", "new_value" => %{"x" => 8.5}} | _] = data["edits"]
    end

    test "a partial location and invalid values are rejected", %{conn: conn} do
      id = create(conn)["id"]

      assert conn
             |> patch(~p"/api/boreholes/#{id}", %{"borehole" => %{"x" => 1}})
             |> json_response(400)

      assert conn
             |> patch(~p"/api/boreholes/#{id}", %{"borehole" => %{"total_depth_m" => -1}})
             |> json_response(422)

      assert conn
             |> patch(~p"/api/boreholes/#{Ecto.UUID.generate()}", %{"borehole" => %{}})
             |> json_response(404)
    end

    test "an unchanged value writes no edit", %{conn: conn} do
      id = create(conn)["id"]

      data =
        conn
        |> patch(~p"/api/boreholes/#{id}", %{"borehole" => %{"name" => "BH 1"}})
        |> json_response(200)

      assert data["data"]["edits"] == []
    end

    defp patch_location(conn, id, x, y, epsg) do
      conn
      |> patch(~p"/api/boreholes/#{id}", %{"borehole" => %{"x" => x, "y" => y, "epsg" => epsg}})
      |> json_response(200)
      |> Map.fetch!("data")
    end
  end

  describe "layers" do
    test "create, patch, delete and revert", %{conn: conn} do
      data = create(conn)
      id = data["id"]

      data =
        conn
        |> post(~p"/api/boreholes/#{id}/layers", %{
          "layer" => %{"depth_from_m" => 5, "depth_to_m" => 6}
        })
        |> json_response(201)
        |> Map.fetch!("data")

      assert [_, _, %{"id" => new_id, "position" => 3}] = data["layers"]
      assert "missing_petrography" in codes(data)
      assert %{"field" => "layer", "old_value" => nil, "layer_id" => ^new_id} = hd(data["edits"])

      data =
        conn
        |> patch(~p"/api/boreholes/#{id}/layers/#{new_id}", %{
          "layer" => %{"petrography" => "Ton"}
        })
        |> json_response(200)
        |> Map.fetch!("data")

      refute "missing_petrography" in codes(data)

      assert %{"field" => "petrography", "old_value" => nil, "new_value" => "Ton"} =
               hd(data["edits"])

      data =
        conn
        |> delete(~p"/api/boreholes/#{id}/layers/#{new_id}")
        |> json_response(200)
        |> Map.fetch!("data")

      assert length(data["layers"]) == 2

      assert %{"field" => "layer", "new_value" => nil, "old_value" => %{"petrography" => "Ton"}} =
               hd(data["edits"])

      data =
        conn
        |> post(~p"/api/boreholes/#{id}/edits/#{hd(data["edits"])["id"]}/revert")
        |> json_response(200)
        |> Map.fetch!("data")

      assert new_id in layer_ids(data)
      assert Enum.find(data["layers"], &(&1["id"] == new_id))["petrography"] == "Ton"

      # reverting the creation deletes the layer again
      creation = Enum.find(data["edits"], &(&1["field"] == "layer" and &1["old_value"] == nil))

      data =
        conn
        |> post(~p"/api/boreholes/#{id}/edits/#{creation["id"]}/revert")
        |> json_response(200)
        |> Map.fetch!("data")

      refute new_id in layer_ids(data)
    end

    test "layers of another borehole are not found", %{conn: conn} do
      one = create(conn)
      other = create(conn)

      assert conn
             |> delete(~p"/api/boreholes/#{other["id"]}/layers/#{hd(one["layers"])["id"]}")
             |> json_response(404)
    end

    test "deleting a layer removes its open flags", %{conn: conn} do
      data = create(conn, %{"layers" => [%{"depth_from_m" => 0, "depth_to_m" => 5}]})
      [layer] = data["layers"]
      assert "missing_petrography" in codes(data)

      data =
        conn
        |> delete(~p"/api/boreholes/#{data["id"]}/layers/#{layer["id"]}")
        |> json_response(200)
        |> Map.fetch!("data")

      refute "missing_petrography" in codes(data)
      assert "no_layers" in codes(data)
    end
  end

  describe "flags and verification" do
    test "a human resolves a flag; the checks do not reopen it", %{conn: conn} do
      data = create(conn, %{"borehole" => %{"name" => "BH", "x" => 8, "y" => 48, "epsg" => 4326}})
      flag = Enum.find(data["flags"], &(&1["code"] == "missing_elevation"))

      data =
        conn
        |> post(~p"/api/flags/#{flag["id"]}/resolve")
        |> json_response(200)
        |> Map.fetch!("data")

      assert %{"resolved_by" => "human"} = Enum.find(data["flags"], &(&1["id"] == flag["id"]))
      refute "missing_elevation" in codes(data)

      # an unrelated edit reruns the checks: the confirmed finding stays resolved
      data =
        conn
        |> patch(~p"/api/boreholes/#{data["id"]}", %{"borehole" => %{"place" => "Bern"}})
        |> json_response(200)
        |> Map.fetch!("data")

      refute "missing_elevation" in codes(data)
      assert length(data["flags"]) == length(Enum.uniq_by(data["flags"], & &1["id"]))

      assert conn |> post(~p"/api/flags/#{flag["id"]}/resolve") |> json_response(409)
      assert conn |> post(~p"/api/flags/#{Ecto.UUID.generate()}/resolve") |> json_response(404)
    end

    test "verify sets and clears verified_at", %{conn: conn} do
      id = create(conn)["id"]

      data =
        conn
        |> post(~p"/api/boreholes/#{id}/verify", %{"verified" => true})
        |> json_response(200)
        |> Map.fetch!("data")

      assert data["verified"] and data["verified_at"]

      data =
        conn
        |> post(~p"/api/boreholes/#{id}/verify", %{"verified" => false})
        |> json_response(200)
        |> Map.fetch!("data")

      assert data["verified"] == false and data["verified_at"] == nil

      assert conn
             |> post(~p"/api/boreholes/#{id}/verify", %{"verified" => "yes"})
             |> json_response(400)
    end
  end

  describe "listing" do
    test "open_flag_count, flagged, sort=open_flags and the search keys", %{conn: conn} do
      clean =
        create(conn, %{
          "borehole" => %{
            "name" => "Clean",
            "x" => 1,
            "y" => 1,
            "epsg" => 4326,
            "elevation_m" => 1,
            "total_depth_m" => 5
          }
        })

      flagged = create(conn, %{"borehole" => %{"name" => "Flagged"}})
      assert clean["open_flag_count"] == 0
      assert flagged["open_flag_count"] == 2

      conn
      |> post(~p"/api/boreholes/#{clean["id"]}/verify", %{"verified" => true})
      |> json_response(200)

      names = fn query ->
        conn
        |> get(~p"/api/boreholes?#{query}")
        |> json_response(200)
        |> Map.fetch!("features")
        |> Enum.map(& &1["properties"]["name"])
      end

      assert names.(flagged: "true") == ["Flagged"]
      assert names.(flagged: "false") == ["Clean"]
      assert names.(sort: "open_flags") == ["Flagged", "Clean"]
      assert names.(sort: "-open_flags") == ["Clean", "Flagged"]
      assert names.(q: "verified:yes") == ["Clean"]
      assert names.(q: "flagged:yes") == ["Flagged"]
      assert names.(q: "verified:no flagged:true") == ["Flagged"]
      assert names.(q: "-flagged:true") == ["Clean"]

      %{"features" => [%{"properties" => %{"open_flag_count" => 2}}]} =
        conn |> get(~p"/api/boreholes?flagged=true&view=points") |> json_response(200)

      assert conn |> get(~p"/api/boreholes?q=verified:maybe") |> json_response(400)
    end
  end
end
