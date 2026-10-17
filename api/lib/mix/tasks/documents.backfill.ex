defmodule Mix.Tasks.Documents.Backfill do
  @shortdoc "Move files out of priv/uploads/ into priv/storage/ and create their documents rows"

  @moduledoc """
  `priv/uploads/` is a staging inbox: anything placed there is NOT yet tracked in the
  `documents` table. This task, for every file found there:

    1. generates a `documents.id` (UUID) up front
    2. inserts a `documents` row with `storage_path` set to `<id><ext>` (flat, no subfolders)
    3. moves the file from `priv/uploads/...` to `priv/storage/<id><ext>`

  Because the file is renamed to its document's UUID, a stored file can always be matched
  back to its `documents` row just from the filename — no separate bookkeeping needed.

  If the move fails after the row was inserted, the row is deleted again so `priv/uploads/`
  and the `documents` table stay consistent — safe to re-run.

  This exists because some sample data was copied directly onto disk instead of going
  through the (not yet built) upload endpoint. Once that endpoint exists, it should write
  straight into `priv/storage/` and skip `priv/uploads/` entirely for new uploads.

      mix documents.backfill
  """

  use Mix.Task

  alias Api.Boreholes.Document
  alias Api.Repo

  @skip_filenames ~w(.gitkeep .DS_Store)

  @impl Mix.Task
  def run(_args) do
    Mix.Task.run("app.start")

    priv_dir = :code.priv_dir(:api)
    uploads_dir = Path.join(priv_dir, "uploads")
    storage_dir = Path.join(priv_dir, "storage")

    File.mkdir_p!(storage_dir)

    uploads_dir
    |> Path.join("**/*")
    |> Path.wildcard()
    |> Enum.filter(&File.regular?/1)
    |> Enum.reject(&(Path.basename(&1) in @skip_filenames))
    |> Enum.each(&backfill_file(&1, storage_dir))
  end

  defp backfill_file(source_path, storage_dir) do
    id = Ecto.UUID.generate()
    extension = source_path |> Path.extname() |> String.downcase()
    storage_path = "#{id}#{extension}"
    destination_path = Path.join(storage_dir, storage_path)

    attrs = %{
      original_filename: Path.basename(source_path),
      storage_path: storage_path,
      mime_type: MIME.from_path(source_path)
    }

    case Repo.insert(Document.changeset(%Document{id: id}, attrs)) do
      {:ok, document} -> move_file(source_path, destination_path, document)
      {:error, changeset} -> report_insert_error(source_path, changeset)
    end
  end

  defp move_file(source_path, destination_path, document) do
    case File.rename(source_path, destination_path) do
      :ok ->
        Mix.shell().info("#{source_path} -> #{destination_path} (document #{document.id})")

      {:error, reason} ->
        Mix.shell().error(
          "failed to move #{source_path} to #{destination_path}: #{inspect(reason)}, rolling back document row"
        )

        Repo.delete!(document)
    end
  end

  defp report_insert_error(source_path, changeset) do
    Mix.shell().error(
      "failed to insert document for #{source_path}: #{inspect(changeset.errors)}"
    )
  end
end
