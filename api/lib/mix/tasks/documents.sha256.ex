defmodule Mix.Tasks.Documents.Sha256 do
  @shortdoc "Fill the missing documents.sha256 (duplicate upload detection) from the stored files"

  @moduledoc """
  Documents uploaded before `documents.sha256` existed, or added with `mix documents.backfill`,
  have no fingerprint, so a second upload of the same file is not recognised (ADR-0006). This
  task hashes their stored files. Safe to re-run; in a release use
  `bin/api eval "Api.Release.backfill_sha256()"`.

      mix documents.sha256
  """

  use Mix.Task

  @requirements ["app.start"]

  @impl Mix.Task
  def run(_args) do
    %{updated: updated, skipped: skipped} = Api.Boreholes.backfill_document_sha256()
    Mix.shell().info("documents.sha256: #{updated} filled, #{skipped} without file")
  end
end
