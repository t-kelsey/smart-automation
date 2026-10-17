defmodule Mix.Tasks.Boreholes.Mock do
  @shortdoc "Insert generated mock boreholes (with layers and documents) into the database"

  @moduledoc """
  Inserts invented boreholes from `Api.MockData` for development and demos. Previously
  generated mock rows are removed first, so the task can be re-run; seeded and real data stay.

      mix boreholes.mock                # 1000 boreholes
      mix boreholes.mock --count 10000  # the prototype's maximum
      mix boreholes.mock --count 0      # only remove mock data
      mix boreholes.mock --seed 7       # a different, but again reproducible, data set
  """

  use Mix.Task

  @impl Mix.Task
  def run(args) do
    {opts, _rest} = OptionParser.parse!(args, strict: [count: :integer, seed: :integer])
    count = Keyword.get(opts, :count, 1000)

    if count > Api.MockData.max_count() do
      Mix.raise("--count must be at most #{Api.MockData.max_count()}")
    end

    Mix.Task.run("app.start")
    Logger.configure(level: :info)

    removed = Api.MockData.delete_source("mock")
    created = Api.MockData.generate(count, seed: Keyword.get(opts, :seed, 42))

    Mix.shell().info(
      "Removed #{removed} mock boreholes; created #{created.boreholes} boreholes, " <>
        "#{created.layers} layers, #{created.documents} documents."
    )
  end
end
