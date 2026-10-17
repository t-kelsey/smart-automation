defmodule ApiWeb.PipelineRunControllerTest do
  use ApiWeb.ConnCase, async: true

  import Ecto.Query

  alias Api.Boreholes
  alias Api.Boreholes.PipelineRun
  alias Api.Repo

  defp upload(name, content \\ "%PDF-1.4 test") do
    path = Path.join(System.tmp_dir!(), "upload_#{System.unique_integer([:positive])}")
    File.write!(path, content)
    %Plug.Upload{path: path, filename: name, content_type: "application/pdf"}
  end

  # `pipeline_runs.inserted_at` has second resolution, so runs created back-to-back in a test can
  # tie; backdate by `seconds_ago` to make insertion order deterministic for order-sensitive tests.
  defp backdate(run, seconds_ago) do
    inserted_at =
      DateTime.utc_now() |> DateTime.add(-seconds_ago, :second) |> DateTime.truncate(:second)

    Repo.update_all(from(p in PipelineRun, where: p.id == ^run.id),
      set: [inserted_at: inserted_at]
    )
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

  describe "index/2" do
    test "empty list", %{conn: conn} do
      conn = get(conn, ~p"/api/pipeline_runs")

      assert %{"data" => [], "total" => 0, "limit" => nil, "offset" => 0} =
               json_response(conn, 200)
    end

    test "lists entries with document_filename, newest first", %{conn: conn} do
      File.mkdir_p!(Boreholes.storage_dir())
      {:ok, document_a} = Boreholes.create_uploaded_document(upload("a.pdf"))
      {:ok, document_b} = Boreholes.create_uploaded_document(upload("b.pdf"))

      {:ok, run_a} = Boreholes.create_pipeline_run(%{"document_id" => document_a.id})
      {:ok, run_b} = Boreholes.create_pipeline_run(%{"document_id" => document_b.id})
      backdate(run_a, 10)

      conn = get(conn, ~p"/api/pipeline_runs")
      %{"data" => [first, second], "total" => 2} = json_response(conn, 200)

      assert first["id"] == run_b.id
      assert first["document_filename"] == "b.pdf"
      refute Map.has_key?(first, "exec_stages")
      refute Map.has_key?(first, "report")

      assert second["id"] == run_a.id
      assert second["document_filename"] == "a.pdf"
    end

    test "filters by status", %{conn: conn} do
      File.mkdir_p!(Boreholes.storage_dir())
      {:ok, document} = Boreholes.create_uploaded_document(upload("a.pdf"))
      {:ok, run} = Boreholes.create_pipeline_run(%{"document_id" => document.id})
      {:ok, _run} = Boreholes.update_pipeline_run_status(run, "completed")

      {:ok, document2} = Boreholes.create_uploaded_document(upload("b.pdf"))
      {:ok, _other_run} = Boreholes.create_pipeline_run(%{"document_id" => document2.id})

      conn = get(conn, ~p"/api/pipeline_runs?status=completed")
      %{"data" => [entry], "total" => 1} = json_response(conn, 200)
      assert entry["id"] == run.id
      assert entry["status"] == "completed"
    end

    test "paging via limit/offset", %{conn: conn} do
      File.mkdir_p!(Boreholes.storage_dir())

      runs =
        for n <- 1..3 do
          {:ok, document} = Boreholes.create_uploaded_document(upload("doc_#{n}.pdf"))
          {:ok, run} = Boreholes.create_pipeline_run(%{"document_id" => document.id})
          run
        end

      runs
      |> Enum.with_index()
      |> Enum.each(fn {run, idx} -> backdate(run, (3 - idx) * 10) end)

      conn = get(conn, ~p"/api/pipeline_runs?limit=2&offset=1")
      %{"data" => entries, "total" => 3, "limit" => 2, "offset" => 1} = json_response(conn, 200)

      expected_ids = runs |> Enum.reverse() |> Enum.slice(1, 2) |> Enum.map(& &1.id)
      assert Enum.map(entries, & &1["id"]) == expected_ids
    end
  end
end
