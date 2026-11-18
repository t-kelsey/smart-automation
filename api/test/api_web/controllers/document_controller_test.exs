defmodule ApiWeb.DocumentControllerTest do
  use ApiWeb.ConnCase, async: true

  alias Api.Boreholes.Document
  alias Api.Repo

  setup do
    dir = Application.fetch_env!(:api, :document_storage_dir)
    File.mkdir_p!(dir)
    %{dir: dir}
  end

  defp insert_document(attrs) do
    %Document{}
    |> Document.changeset(Map.merge(%{original_filename: "Schichtenverzeichnis Ü.pdf"}, attrs))
    |> Repo.insert!()
  end

  defp store(dir, name, content) do
    File.write!(Path.join(dir, name), content)
    on_exit(fn -> File.rm(Path.join(dir, name)) end)
  end

  describe "GET /api/documents/:id" do
    test "returns metadata and linked boreholes, without the storage path", %{conn: conn} do
      borehole = Repo.insert!(%Api.Boreholes.Borehole{name: "BK 1"})
      document = insert_document(%{storage_path: "x.pdf", mime_type: "application/pdf"})

      Repo.insert!(%Api.Boreholes.BoreholeDocument{
        borehole_id: borehole.id,
        document_id: document.id
      })

      %{"data" => data} = json_response(get(conn, ~p"/api/documents/#{document.id}"), 200)
      assert data["id"] == document.id
      assert data["original_filename"] == "Schichtenverzeichnis Ü.pdf"
      assert data["has_file"] == false
      assert data["boreholes"] == [%{"id" => borehole.id, "name" => "BK 1"}]
      refute Map.has_key?(data, "storage_path")
      refute Map.has_key?(data, "raw_extraction")
    end

    test "returns 404 for unknown or invalid ids", %{conn: conn} do
      for id <- [Ecto.UUID.generate(), "not-a-uuid"] do
        assert json_response(get(conn, ~p"/api/documents/#{id}"), 404)
      end
    end
  end

  describe "GET /api/documents/:id/file" do
    test "streams the stored file inline, or as attachment with download=1", %{
      conn: conn,
      dir: dir
    } do
      name = "#{Ecto.UUID.generate()}.pdf"
      store(dir, name, "%PDF-1.4 test")
      document = insert_document(%{storage_path: name, mime_type: "application/pdf"})

      conn1 = get(conn, ~p"/api/documents/#{document.id}/file")
      assert response(conn1, 200) == "%PDF-1.4 test"
      assert get_resp_header(conn1, "content-type") == ["application/pdf"]
      assert [disposition] = get_resp_header(conn1, "content-disposition")
      assert disposition =~ ~s(inline; filename="Schichtenverzeichnis _.pdf")
      assert disposition =~ "filename*=UTF-8''Schichtenverzeichnis%20%C3%9C.pdf"

      conn2 = get(conn, ~p"/api/documents/#{document.id}/file?download=1")
      assert [<<"attachment;", _::binary>>] = get_resp_header(conn2, "content-disposition")
    end

    test "returns 404 when the document or its file does not exist", %{conn: conn} do
      missing = insert_document(%{storage_path: "#{Ecto.UUID.generate()}.pdf"})
      mock = insert_document(%{storage_path: "mock/#{Ecto.UUID.generate()}.pdf"})

      for path <- [
            ~p"/api/documents/#{missing.id}/file",
            ~p"/api/documents/#{mock.id}/file",
            ~p"/api/documents/#{Ecto.UUID.generate()}/file",
            ~p"/api/documents/not-a-uuid/file"
          ] do
        assert %{"errors" => %{"detail" => "Not Found"}} = json_response(get(conn, path), 404)
      end
    end

    test "never serves files outside the storage directory", %{conn: conn, dir: dir} do
      name = "outside-#{Ecto.UUID.generate()}.txt"
      File.write!(Path.join(Path.dirname(dir), name), "secret")
      on_exit(fn -> File.rm(Path.join(Path.dirname(dir), name)) end)
      document = insert_document(%{storage_path: "../#{name}"})

      assert json_response(get(conn, ~p"/api/documents/#{document.id}/file"), 404)
    end
  end

  describe "duplicate upload detection" do
    defp upload(conn, content, name \\ "a.pdf") do
      path = Path.join(System.tmp_dir!(), "up_#{System.unique_integer([:positive])}")
      File.write!(path, content)
      file = %Plug.Upload{path: path, filename: name, content_type: "application/pdf"}

      conn
      |> post(~p"/api/documents", %{"file" => file})
      |> json_response(202)
      |> Map.fetch!("data")
    end

    test "backfill fills the SHA-256 of documents stored without one", %{conn: conn} do
      doc = upload(conn, "old bytes")
      Api.Repo.update_all(Api.Boreholes.Document, set: [sha256: nil])

      assert %{updated: 1} = Api.Boreholes.backfill_document_sha256()

      assert Api.Repo.get!(Api.Boreholes.Document, doc["id"]).sha256 ==
               :crypto.hash(:sha256, "old bytes") |> Base.encode16(case: :lower)
    end

    test "uploads store the SHA-256 and GET /api/documents?sha256= finds them newest first", %{
      conn: conn
    } do
      first = upload(conn, "same bytes")
      second = upload(conn, "same bytes", "b.pdf")
      _other = upload(conn, "different")
      sha = :crypto.hash(:sha256, "same bytes") |> Base.encode16(case: :lower)
      assert first["sha256"] == sha

      borehole = Repo.insert!(%Api.Boreholes.Borehole{name: "BK"})

      Repo.insert!(%Api.Boreholes.BoreholeDocument{
        borehole_id: borehole.id,
        document_id: first["id"],
        role: "original"
      })

      {:ok, run} = Api.Boreholes.create_pipeline_run(%{"document_id" => first["id"]})

      %{"data" => [newest, oldest]} =
        conn |> get(~p"/api/documents?sha256=#{String.upcase(sha)}") |> json_response(200)

      # same second: ties are broken by id, so just match by id
      by_id = Map.new([newest, oldest], &{&1["id"], &1})
      assert by_id[second["id"]]["borehole_count"] == 0
      assert by_id[second["id"]]["pipeline_runs"] == []
      assert by_id[first["id"]]["borehole_count"] == 1
      assert by_id[first["id"]]["original_filename"] == "a.pdf"

      assert [%{"id" => run_id, "status" => "new", "inserted_at" => _}] =
               by_id[first["id"]]["pipeline_runs"]

      assert run_id == run.id

      assert %{"data" => []} =
               conn
               |> get(~p"/api/documents?sha256=#{String.duplicate("0", 64)}")
               |> json_response(200)

      assert conn |> get(~p"/api/documents") |> json_response(400)

      %{"data" => shown} = conn |> get(~p"/api/documents/#{first["id"]}") |> json_response(200)
      assert shown["sha256"] == sha
    end
  end
end
