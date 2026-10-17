defmodule ApiWeb.ExecStageControllerTest do
  use ApiWeb.ConnCase, async: true

  alias Api.Boreholes

  test "show returns the stage and 404 for unknown ids", %{conn: conn} do
    path = Path.join(System.tmp_dir!(), "upload_#{System.unique_integer([:positive])}")
    File.write!(path, "%PDF-1.4 test")
    File.mkdir_p!(Boreholes.storage_dir())

    {:ok, document} =
      Boreholes.create_uploaded_document(%Plug.Upload{
        path: path,
        filename: "a.pdf",
        content_type: "application/pdf"
      })

    {:ok, stage} =
      Boreholes.create_exec_stage(%{
        "type" => "extract",
        "run_id" => "r1",
        "position" => 1,
        "data" => %{"depth" => 12},
        "document_ids" => [document.id]
      })

    %{"data" => shown} = conn |> get(~p"/api/exec_stages/#{stage.id}") |> json_response(200)
    assert shown["id"] == stage.id
    assert shown["data"] == %{"depth" => 12}
    assert shown["document_ids"] == [document.id]

    assert conn |> get(~p"/api/exec_stages/#{Ecto.UUID.generate()}") |> json_response(404)
    assert conn |> get(~p"/api/exec_stages/nope") |> json_response(404)
  end
end
