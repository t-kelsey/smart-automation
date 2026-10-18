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

    test "stays pending even with a pipeline configured (ADR-0035: no auto-trigger)", %{
      conn: conn
    } do
      Application.put_env(:api, :pipeline_url, "http://pipeline.test/process")

      conn = post(conn, ~p"/api/documents", %{"file" => upload("a.pdf")})
      %{"data" => %{"status" => "pending"}} = json_response(conn, 202)
    end

    test "rejects unsupported file types and a missing file", %{conn: conn} do
      conn1 = post(conn, ~p"/api/documents", %{"file" => upload("virus.exe")})

      assert %{"errors" => %{"detail" => "unsupported file type" <> _}} =
               json_response(conn1, 400)

      conn2 = post(conn, ~p"/api/documents", %{})
      assert json_response(conn2, 400)
    end
  end

  describe "Api.Pipeline.submit_pipeline_run/1" do
    test "posts a file-free JSON body and marks the run running on success" do
      Application.put_env(:api, :pipeline_url, "http://pipeline.test/process")
      {:ok, document} = Boreholes.create_uploaded_document(upload("a.pdf"))
      {:ok, pipeline_run} = Boreholes.create_pipeline_run(%{"document_id" => document.id})

      Req.Test.stub(Api.Pipeline, fn conn ->
        {:ok, body, conn} = Plug.Conn.read_body(conn)

        assert Jason.decode!(body) == %{
                 "document_id" => document.id,
                 "pipeline_id" => pipeline_run.id,
                 "config" => %{}
               }

        refute conn.req_headers |> List.keyfind("content-type", 0) |> elem(1) =~ "multipart"
        Plug.Conn.send_resp(conn, 200, "")
      end)

      assert {:ok, %{status: "running"}} = Api.Pipeline.submit_pipeline_run(pipeline_run)
    end

    test "marks the run failed if the pipeline refuses it" do
      Application.put_env(:api, :pipeline_url, "http://pipeline.test/process")
      {:ok, document} = Boreholes.create_uploaded_document(upload("a.pdf"))
      {:ok, pipeline_run} = Boreholes.create_pipeline_run(%{"document_id" => document.id})

      Req.Test.stub(Api.Pipeline, &Plug.Conn.send_resp(&1, 500, "boom"))

      log =
        ExUnit.CaptureLog.capture_log(fn ->
          assert {:ok, %{status: "failed", error: "pipeline could not be reached" <> _}} =
                   Api.Pipeline.submit_pipeline_run(pipeline_run)
        end)

      assert log =~ "pipeline run submit failed"
    end
  end

  describe "Boreholes.stop_pipeline_run/1" do
    test "stops a running run, its open stages and tells the pipeline" do
      Application.put_env(:api, :pipeline_url, "http://pipeline.test/execute")
      {:ok, document} = Boreholes.create_uploaded_document(upload("a.pdf"))
      {:ok, run} = Boreholes.create_pipeline_run(%{"document_id" => document.id})
      {:ok, run} = Boreholes.update_pipeline_run_status(run, "running")

      stage = fn type, status ->
        {:ok, s} =
          Boreholes.create_exec_stage(%{
            "type" => type,
            "run_id" => run.id,
            "status" => status,
            "document_ids" => [document.id]
          })

        s
      end

      done = stage.("filter", "success")
      running = stage.("split", "running")
      planned = stage.("extract", "new")

      test_pid = self()

      Req.Test.stub(Api.Pipeline, fn conn ->
        send(test_pid, {:stop_request, conn.method, conn.request_path})
        Plug.Conn.send_resp(conn, 202, "")
      end)

      assert {:ok, %{status: "stopped", error: "stopped by user", finished_at: %DateTime{}}} =
               Boreholes.stop_pipeline_run(run)

      assert_received {:stop_request, "POST", path}
      assert path == "/runs/#{run.id}/stop"

      assert Boreholes.get_exec_stage(done.id).status == "success"
      assert Boreholes.get_exec_stage(running.id).status == "stopped"
      assert %{status: "stopped", finished_at: %DateTime{}} = Boreholes.get_exec_stage(planned.id)

      # stopped wins over the pipeline's late report
      assert {:error, {:conflict, _}} =
               Boreholes.update_pipeline_run_status(Boreholes.get_pipeline_run(run.id), "failed")

      # stopping again is a no-op that does not bother the pipeline
      assert {:ok, %{status: "stopped"}} =
               Boreholes.stop_pipeline_run(Boreholes.get_pipeline_run(run.id))

      refute_received {:stop_request, _, _}
    end
  end

  describe "POST /api/exec_stages/:id/retry" do
    setup do
      Application.put_env(:api, :pipeline_url, "http://pipeline.test/execute")
      {:ok, document} = Boreholes.create_uploaded_document(upload("a.pdf"))

      {:ok, run} =
        Boreholes.create_pipeline_run(%{"document_id" => document.id, "config" => %{"x" => 1}})

      {:ok, run} = Boreholes.update_pipeline_run_status(run, "running")
      {:ok, run} = Boreholes.update_pipeline_run_status(run, "failed", %{"error" => "boom"})

      stage = fn type, position, status ->
        {:ok, s} =
          Boreholes.create_exec_stage(%{
            "type" => type,
            "run_id" => run.id,
            "position" => position,
            "status" => status,
            "document_ids" => [document.id]
          })

        s
      end

      %{run: run, document: document, stage: stage}
    end

    test "reopens the run and asks the pipeline to redo the job", %{conn: conn, run: run} = ctx do
      ctx.stage.("split", nil, "success")
      ctx.stage.("extract", 1, "success")
      failed = ctx.stage.("transform", 1, "failed")
      test_pid = self()

      Req.Test.stub(Api.Pipeline, fn conn ->
        {:ok, body, conn} = Plug.Conn.read_body(conn)
        send(test_pid, {:retry_request, conn.request_path, Jason.decode!(body)})
        Plug.Conn.send_resp(conn, 202, "")
      end)

      assert %{"data" => %{"status" => "running", "error" => nil, "finished_at" => nil}} =
               conn |> post(~p"/api/exec_stages/#{failed.id}/retry") |> json_response(202)

      assert_received {:retry_request, path, body}
      assert path == "/runs/#{run.id}/retry"

      assert body == %{
               "document_id" => run.document_id,
               "stage" => "transform",
               "position" => 1,
               "config" => %{"x" => 1}
             }

      # the run is active again, so a second retry is refused
      assert conn |> post(~p"/api/exec_stages/#{failed.id}/retry") |> json_response(409)
    end

    test "restores the run if the pipeline cannot be reached", %{conn: conn} = ctx do
      ctx.stage.("split", nil, "success")
      failed = ctx.stage.("extract", 1, "failed")
      Req.Test.stub(Api.Pipeline, &Plug.Conn.send_resp(&1, 500, "boom"))

      assert conn |> post(~p"/api/exec_stages/#{failed.id}/retry") |> json_response(400)

      assert %{status: "failed", error: "boom", finished_at: %DateTime{}} =
               Boreholes.get_pipeline_run(failed.run_id)
    end

    test "refuses jobs that cannot be retried", %{conn: conn} = ctx do
      filter = ctx.stage.("filter", nil, "failed")
      success = ctx.stage.("extract", 2, "success")
      no_split = ctx.stage.("extract", 1, "failed")
      no_extract = ctx.stage.("transform", 3, "stopped")

      for stage <- [filter, success, no_split, no_extract] do
        assert conn |> post(~p"/api/exec_stages/#{stage.id}/retry") |> json_response(409)
      end

      assert conn
             |> post(~p"/api/exec_stages/#{Ecto.UUID.generate()}/retry")
             |> json_response(404)
    end

    test "refuses a job that was already retried", %{conn: conn, run: run} = ctx do
      ctx.stage.("split", nil, "success")
      old = ctx.stage.("extract", 1, "failed")
      ctx.stage.("extract", 1, "failed")
      Req.Test.stub(Api.Pipeline, &Plug.Conn.send_resp(&1, 202, ""))

      assert %{"errors" => %{"detail" => "this job was already retried"}} =
               conn |> post(~p"/api/exec_stages/#{old.id}/retry") |> json_response(409)

      assert Boreholes.get_pipeline_run(run.id).status == "failed"
    end
  end
end
