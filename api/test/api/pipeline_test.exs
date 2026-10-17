defmodule Api.PipelineTest do
  use ApiWeb.ConnCase, async: false

  alias Api.Boreholes

  setup do
    File.mkdir_p!(Boreholes.storage_dir())
    on_exit(fn -> Application.delete_env(:api, :pipeline_url) end)
  end

  defp upload(name, content \\ "%PDF-1.4 test") do
    path = Path.join(System.tmp_dir!(), "upload_#{System.unique_integer([:positive])}")
    File.write!(path, content)
    %Plug.Upload{path: path, filename: name, content_type: "application/pdf"}
  end

  describe "PUT /api/documents/:id/status" do
    test "updates the status, rejects unknown ones", %{conn: conn} do
      {:ok, document} = Boreholes.create_uploaded_document(upload("a.pdf"))
      path = ~p"/api/documents/#{document.id}/status"

      assert %{"data" => %{"status" => "extracted"}} =
               json_response(put(conn, path, %{"status" => "extracted"}), 200)

      assert json_response(put(conn, path, %{"status" => "bogus"}), 422)

      assert json_response(
               put(conn, ~p"/api/documents/#{Ecto.UUID.generate()}/status", %{
                 "status" => "failed"
               }),
               404
             )
    end
  end

  describe "POST /api/documents" do
    test "stores the file under its document id and keeps it pending without a pipeline", %{
      conn: conn
    } do
      conn = post(conn, ~p"/api/documents", %{"file" => upload("Bericht Ü.PDF")})
      %{"data" => data} = json_response(conn, 202)

      assert data["original_filename"] == "Bericht Ü.PDF"
      assert data["status"] == "pending"
      assert data["has_file"]
      assert data["size_bytes"] == 13
      assert File.read!(Path.join(Boreholes.storage_dir(), "#{data["id"]}.pdf")) =~ "%PDF"
    end

    test "sends the file to the pipeline and marks the document processing", %{conn: conn} do
      Application.put_env(:api, :pipeline_url, "http://pipeline.test/process")
      test_pid = self()

      Req.Test.stub(Api.Pipeline, fn conn ->
        {:ok, body, conn} = Plug.Conn.read_body(conn)
        send(test_pid, {:pipeline_request, body})
        Plug.Conn.send_resp(conn, 202, "")
      end)

      Req.Test.allow(Api.Pipeline, self(), Process.whereis(Api.TaskSupervisor))
      conn = post(conn, ~p"/api/documents", %{"file" => upload("a.pdf")})
      %{"data" => %{"id" => id, "status" => "processing"}} = json_response(conn, 202)

      assert_receive {:pipeline_request, body}, 2000
      assert body =~ id
      assert body =~ "%PDF-1.4 test"
    end

    test "marks the document failed if the pipeline refuses it" do
      Application.put_env(:api, :pipeline_url, "http://pipeline.test/process")
      Req.Test.stub(Api.Pipeline, &Plug.Conn.send_resp(&1, 500, "boom"))

      {:ok, document} = Boreholes.create_uploaded_document(upload("a.pdf"))
      assert {:error, {:status, 500}} = Api.Pipeline.submit(document)
    end

    test "rejects unsupported file types and a missing file", %{conn: conn} do
      conn1 = post(conn, ~p"/api/documents", %{"file" => upload("virus.exe")})

      assert %{"errors" => %{"detail" => "unsupported file type" <> _}} =
               json_response(conn1, 400)

      conn2 = post(conn, ~p"/api/documents", %{})
      assert json_response(conn2, 400)
    end
  end
end
