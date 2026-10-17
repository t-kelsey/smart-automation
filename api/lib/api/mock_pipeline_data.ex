defmodule Api.MockPipelineData do
  @moduledoc """
  Generates invented pipeline runs (with exec stages and reports) on top of the mock boreholes
  that are already in the database (`mix boreholes.mock`), for development and demos of the
  pipeline pages (`mix pipeline_runs.mock`).

  Every row is marked so `delete/0` can remove it again without touching real runs: the run's
  `config` carries `"mock" => true`, and its exec stages and report use `run_id` = the run id
  (which only exists for mock runs). Documents and boreholes are not created or deleted here.
  """

  import Ecto.Query

  alias Api.Boreholes.{
    Borehole,
    BoreholeDocument,
    BoreholeLayer,
    Document,
    ExecStage,
    PipelineRun,
    Report,
    StageDocumentLink
  }

  alias Api.Repo

  @statuses ["completed", "completed", "completed", "running", "failed", "new"]
  @steps ~w(filter split extract transform)
  @models %{
    "filter" => "haiku",
    "split" => "haiku",
    "extract" => "sonnet",
    "transform" => "haiku"
  }

  @doc """
  Creates up to `count` pipeline runs, one per document of an existing mock borehole. Returns
  `%{runs:, exec_stages:, reports:}`; all zero if there are no mock boreholes.
  """
  def generate(count, opts \\ []) do
    seed = Keyword.get(opts, :seed, 42)
    :rand.seed(:exsss, {seed, seed * 7 + 1, seed * 13 + 2})
    now = DateTime.utc_now() |> DateTime.truncate(:second)

    rows =
      from(bd in BoreholeDocument,
        join: b in Borehole,
        on: b.id == bd.borehole_id,
        where: fragment("?->>'source' = 'mock'", b.metadata),
        order_by: [asc: b.inserted_at, asc: b.id],
        limit: ^count,
        select: {bd.document_id, b.id}
      )
      |> Repo.all()

    pool = Enum.map(rows, &elem(&1, 1))

    rows
    |> Enum.with_index(1)
    |> Enum.reduce(%{runs: 0, exec_stages: 0, reports: 0}, fn {{document_id, borehole_id}, i},
                                                              acc ->
      # Every third run covers a multi-borehole document: extract/transform get one job each.
      extra =
        if rem(i, 3) == 0,
          do: pool |> List.delete(borehole_id) |> Enum.take_random(1 + :rand.uniform(4)),
          else: []

      stats = insert_run(document_id, [borehole_id | extra], now)
      Map.merge(acc, stats, fn _k, a, b -> a + b end)
    end)
  end

  @doc "Deletes all mock pipeline runs with their exec stages and reports. Returns the run count."
  def delete do
    run_ids =
      from(r in PipelineRun,
        where: fragment("?->>'mock' = 'true'", r.config),
        select: type(r.id, :string)
      )
      |> Repo.all()

    Repo.transaction(fn ->
      stage_ids = from(e in ExecStage, where: e.run_id in ^run_ids, select: e.id)
      Repo.delete_all(from(l in StageDocumentLink, where: l.exec_stage_id in subquery(stage_ids)))
      Repo.delete_all(from(e in ExecStage, where: e.run_id in ^run_ids))
      Repo.delete_all(from(r in Report, where: r.run_id in ^run_ids))
      {deleted, _} = Repo.delete_all(from(r in PipelineRun, where: r.id in ^run_ids))
      deleted
    end)
    |> elem(1)
  end

  defp insert_run(document_id, borehole_ids, now) do
    status = Enum.random(@statuses)

    boreholes =
      Enum.map(borehole_ids, fn id ->
        layers =
          Repo.all(from(l in BoreholeLayer, where: l.borehole_id == ^id, order_by: l.position))

        {Repo.get!(Borehole, id), layers}
      end)

    document = Repo.get!(Document, document_id)

    started = DateTime.add(now, -:rand.uniform(72 * 3600), :second)
    run_id = Ecto.UUID.generate()

    config =
      Map.new(@steps, fn step ->
        {step, %{"model" => @models[step], "effort" => Enum.random(~w(low medium high))}}
      end)
      |> Map.put("mock", true)

    finished_at = DateTime.add(started, 90, :second)

    Repo.insert!(%PipelineRun{
      id: run_id,
      document_id: document_id,
      status: status,
      config: config,
      started_at: if(status != "new", do: usec(started)),
      finished_at: if(status in ["completed", "failed"], do: usec(finished_at)),
      error: if(status == "failed", do: "mock: extraction failed"),
      inserted_at: started,
      updated_at: finished_at
    })

    positions = Enum.with_index(boreholes, 1)

    all_stages =
      [
        {"filter", nil, %{"pages" => classify_pages(document.page_count || 1)}},
        {"split", nil,
         %{
           "boreholes" =>
             Enum.map(positions, fn {{b, _}, i} -> %{"label" => b.name, "pages" => [i]} end)
         }}
      ] ++
        Enum.map(positions, fn {{b, layers}, i} ->
          {"extract", i,
           %{
             "borehole_id" => b.id,
             "borehole" => b.name,
             "raw_text" => Enum.map(layers, & &1.raw_text)
           }}
        end) ++
        Enum.map(positions, fn {{b, layers}, i} ->
          {"transform", i,
           %{"borehole_id" => b.id, "payload" => payload(b, layers), "validation_issues" => []}}
        end)

    # How many of the stage rows (jobs) have a result; a prefix, so partial extract/transform
    # stages show some sub jobs finished. The stage after the prefix is running (or failed) and
    # the rest is new (or stopped), as the pipeline reports them (ADR-0040).
    total = length(all_stages)

    done =
      case status do
        "completed" -> total
        "failed" -> Enum.random(1..(total - 1))
        "running" -> Enum.random(0..(total - 1))
        "new" -> 0
      end

    stages =
      if status == "new",
        do: [],
        else:
          all_stages
          |> Enum.with_index()
          |> Enum.map(fn {stage, i} -> {stage, mock_stage_status(status, i, done)} end)

    finished_stages =
      stages
      |> Enum.filter(fn {_, s} -> s == "success" end)
      |> Enum.map(fn {{type, _, _}, _} -> type end)
      |> Enum.uniq()
      |> length()

    current = Enum.find(stages, fn {_, s} -> s in ["running", "failed"] end)

    if current do
      {{type, _, _}, _} = current

      Repo.update_all(from(pr in PipelineRun, where: pr.id == ^run_id),
        set: [current_stage: type]
      )
    end

    Enum.each(stages, fn {{type, position, data}, stage_status} ->
      began = DateTime.add(started, 1, :second)

      stage =
        Repo.insert!(%ExecStage{
          type: type,
          run_id: run_id,
          position: position,
          status: stage_status,
          data: if(stage_status == "success", do: data),
          error: if(stage_status == "failed", do: "mock: #{type} failed"),
          model: config[type]["model"],
          effort: config[type]["effort"],
          started_at: if(stage_status in ~w(success failed running), do: usec(began)),
          finished_at:
            if(stage_status in ~w(success failed stopped),
              do: usec(DateTime.add(began, 1 + :rand.uniform(40), :second))
            ),
          inserted_at: started,
          updated_at: started
        })

      Repo.insert!(%StageDocumentLink{
        exec_stage_id: stage.id,
        document_id: document_id,
        inserted_at: started,
        updated_at: started
      })
    end)

    reports =
      if finished_stages > 0,
        do: insert_report(run_id, document_id, config, finished_stages, started)

    %{runs: 1, exec_stages: length(stages), reports: if(reports, do: 1, else: 0)}
  end

  defp insert_report(run_id, document_id, config, finished_stages, at) do
    steps =
      @steps
      |> Enum.take(finished_stages)
      |> Enum.with_index(1)
      |> Enum.map(fn {step, n} ->
        %{
          "step" => "#{n} #{step}",
          "model_requested" => config[step]["model"],
          "effort" => config[step]["effort"],
          "wall_seconds" => Float.round(2 + :rand.uniform() * 40, 1),
          "input_tokens" => :rand.uniform(30_000),
          "output_tokens" => :rand.uniform(4_000),
          "cost_usd" => Float.round(:rand.uniform() * 0.4, 4)
        }
      end)

    Repo.insert!(%Report{
      run_id: run_id,
      document_id: document_id,
      data: %{"steps" => steps},
      inserted_at: at,
      updated_at: at
    })
  end

  defp mock_stage_status(_run_status, i, done) when i < done, do: "success"
  defp mock_stage_status("running", i, done) when i == done, do: "running"
  defp mock_stage_status("running", _i, _done), do: "new"
  defp mock_stage_status("failed", i, done) when i == done, do: "failed"
  defp mock_stage_status("failed", _i, _done), do: "stopped"

  defp usec(%DateTime{} = dt), do: %{dt | microsecond: {0, 6}}

  defp classify_pages(count), do: Enum.map(1..count, &%{"page" => &1, "borehole_log" => true})

  defp payload(borehole, layers) do
    %{
      "borehole" => %{"name" => borehole.name, "place" => borehole.place},
      "layers" =>
        Enum.map(layers, fn l ->
          %{
            "depth_from_m" => l.depth_from_m,
            "depth_to_m" => l.depth_to_m,
            "petrography" => l.petrography,
            "stratigraphy" => l.stratigraphy
          }
        end)
    }
  end
end
