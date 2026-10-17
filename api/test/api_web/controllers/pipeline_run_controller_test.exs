defmodule ApiWeb.PipelineRunControllerTest do
  use ApiWeb.ConnCase, async: true

  alias Api.Boreholes

  defp upload(name, content \\ "%PDF-1.4 test") do
    path = Path.join(System.tmp_dir!(), "upload_#{System.unique_integer([:positive])}")
    File.write!(path, content)
    %Plug.Upload{path: path, filename: name, content_type: "application/pdf"}
  end

  test "create -> show -> update_status round trip", %{conn: conn} do
    File.mkdir_p!(Boreholes.storage_dir())
    {:ok, document} = Boreholes.create_uploaded_document(upload("a.pdf"))

    conn1 =
      post(conn, ~p"/api/pipeline_runs", %{
        "document_id" => document.id,
        "config" => %{"extract" => "sonnet"}
      })

    %{"data" => created} = json_response(conn1, 201)
    assert created["document_id"] == document.id
    assert created["status"] == "new"
    refute Map.has_key?(created, "exec_stages")
    refute Map.has_key?(created, "report")

    conn2 = get(conn, ~p"/api/pipeline_runs/#{created["id"]}")
    %{"data" => shown} = json_response(conn2, 200)
    assert shown["exec_stages"] == []
    assert shown["report"] == nil

    conn3 = put(conn, ~p"/api/pipeline_runs/#{created["id"]}/status", %{"status" => "completed"})
    %{"data" => updated} = json_response(conn3, 200)
    assert updated["status"] == "completed"
    assert updated["exec_stages"] == []
    assert updated["report"] == nil

    conn4 = get(conn, ~p"/api/pipeline_runs/#{Ecto.UUID.generate()}")
    assert json_response(conn4, 404)
  end
end
