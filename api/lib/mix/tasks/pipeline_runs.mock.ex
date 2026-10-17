defmodule Mix.Tasks.PipelineRuns.Mock do
  @shortdoc "Insert mock pipeline runs (with stages and reports) for existing mock boreholes"

  @moduledoc """
  Creates invented pipeline runs for the documents of boreholes created by `mix boreholes.mock`.
  Previously generated mock runs are removed first; real runs stay.

      mix pipeline_runs.mock             # 20 runs
      mix pipeline_runs.mock --count 50
      mix pipeline_runs.mock --count 0   # only remove mock runs
  """

  use Mix.Task

  @impl Mix.Task
  def run(args) do
    {opts, _rest} = OptionParser.parse!(args, strict: [count: :integer, seed: :integer])

    Mix.Task.run("app.start")
    Logger.configure(level: :info)

    removed = Api.MockPipelineData.delete()

    created =
      Api.MockPipelineData.generate(Keyword.get(opts, :count, 20),
        seed: Keyword.get(opts, :seed, 42)
      )

    Mix.shell().info(
      "Removed #{removed} mock runs; created #{created.runs} runs, " <>
        "#{created.exec_stages} stages, #{created.reports} reports."
    )

    if created.runs == 0 and Keyword.get(opts, :count, 20) > 0,
      do: Mix.shell().info("No mock boreholes found; run `mix boreholes.mock` first.")
  end
end
