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
end
