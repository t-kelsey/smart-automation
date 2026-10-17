defmodule Api.Release do
  @moduledoc """
  Tasks to run from a release, where Mix is not available:

      bin/api eval "Api.Release.migrate()"
      bin/api eval "Api.Release.seed()"
  """
  @app :api

  def migrate do
    Application.load(@app)

    for repo <- Application.fetch_env!(@app, :ecto_repos) do
      {:ok, _, _} = Ecto.Migrator.with_repo(repo, &Ecto.Migrator.run(&1, :up, all: true))
    end
  end

  @doc """
  Runs `priv/repo/seeds.exs`: a few hand-made example boreholes plus `MOCK_BOREHOLES` (default
  1000) generated ones. Only previously seeded/generated rows are replaced; real data is kept.
  """
  def seed do
    Application.load(@app)

    seeds = Application.app_dir(@app, "priv/repo/seeds.exs")

    for repo <- Application.fetch_env!(@app, :ecto_repos) do
      {:ok, _, _} = Ecto.Migrator.with_repo(repo, fn _repo -> Code.eval_file(seeds) end)
    end
  end
end
