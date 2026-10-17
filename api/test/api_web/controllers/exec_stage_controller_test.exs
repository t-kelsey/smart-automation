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

  describe "status lifecycle" do
    setup do
      File.mkdir_p!(Boreholes.storage_dir())
      path = Path.join(System.tmp_dir!(), "upload_#{System.unique_integer([:positive])}")
      File.write!(path, "%PDF-1.4 test")

      {:ok, document} =
        Boreholes.create_uploaded_document(%Plug.Upload{
          path: path,
          filename: "a.pdf",
          content_type: "application/pdf"
        })

      {:ok, run} = Boreholes.create_pipeline_run(%{"document_id" => document.id})
      {:ok, run} = Boreholes.update_pipeline_run_status(run, "running")
      %{document: document, run: run}
    end

    test "new -> running -> success with timing, usage and extra documents", %{
      conn: conn,
      document: document,
      run: run
    } do
      %{"data" => created} =
        conn
        |> post(~p"/api/exec_stages", %{
          "type" => "split",
          "run_id" => run.id,
          "document_ids" => [document.id]
        })
        |> json_response(201)

      assert created["status"] == "new"
      assert created["data"] == nil
      assert created["started_at"] == nil

      %{"data" => running} =
        conn
        |> put(~p"/api/exec_stages/#{created["id"]}", %{
          "status" => "running",
          "model" => "haiku",
          "effort" => "medium"
        })
        |> json_response(200)

      assert running["status"] == "running"
      assert running["started_at"]
      assert running["finished_at"] == nil
      assert Boreholes.get_pipeline_run(run.id).current_stage == "split"

      {:ok, other} =
        Boreholes.create_uploaded_document(%Plug.Upload{
          path: Path.join(System.tmp_dir!(), "x") |> tap(&File.write!(&1, "%PDF-1.4 b")),
          filename: "b.pdf",
          content_type: "application/pdf"
        })

      %{"data" => done} =
        conn
        |> put(~p"/api/exec_stages/#{created["id"]}", %{
          "status" => "success",
          "data" => %{"boreholes" => []},
          "usage" => %{"calls" => 1, "cost_usd" => 0.01},
          "document_ids" => [document.id, other.id]
        })
        |> json_response(200)

      assert done["status"] == "success"
      assert done["data"] == %{"boreholes" => []}
      assert done["usage"] == %{"calls" => 1, "cost_usd" => 0.01}
      assert done["model"] == "haiku"
      assert done["finished_at"]
      assert is_integer(done["duration_ms"])
      assert Enum.sort(done["document_ids"]) == Enum.sort([document.id, other.id])

      # a finished stage stays as it is
      assert conn
             |> put(~p"/api/exec_stages/#{created["id"]}", %{"status" => "failed"})
             |> json_response(422)

      %{"data" => shown} = conn |> get(~p"/api/pipeline_runs/#{run.id}") |> json_response(200)
      assert shown["current_stage"] == "split"
      assert shown["stage_counts"]["success"] == 1
      assert shown["stage_counts"]["failed"] == 0
      assert [%{"status" => "success", "usage" => %{"calls" => 1}}] = shown["exec_stages"]
    end

    test "rejects unknown statuses and ids", %{conn: conn, document: document, run: run} do
      assert conn
             |> post(~p"/api/exec_stages", %{
               "type" => "filter",
               "run_id" => run.id,
               "status" => "done",
               "document_ids" => [document.id]
             })
             |> json_response(422)

      assert conn
             |> put(~p"/api/exec_stages/#{Ecto.UUID.generate()}", %{"status" => "running"})
             |> json_response(404)
    end

    test "a failed run stops its open stages", %{conn: conn, document: document, run: run} do
      {:ok, stage} =
        Boreholes.create_exec_stage(%{
          "type" => "extract",
          "run_id" => run.id,
          "position" => 1,
          "status" => "new",
          "document_ids" => [document.id]
        })

      %{"data" => failed} =
        conn
        |> put(~p"/api/pipeline_runs/#{run.id}/status", %{
          "status" => "failed",
          "error" => "split could not group pages"
        })
        |> json_response(200)

      assert failed["status"] == "failed"
      assert failed["error"] == "split could not group pages"
      assert failed["finished_at"]
      assert [%{"id" => id, "status" => "stopped"}] = failed["exec_stages"]
      assert id == stage.id

      assert conn
             |> put(~p"/api/pipeline_runs/#{run.id}/status", %{"status" => "completed"})
             |> json_response(409)
    end
  end
end
