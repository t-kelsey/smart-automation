defmodule Api.Pipeline do
  @moduledoc """
  Hands uploaded documents to the extraction pipeline (`bem/`, ADR-0033).

  The pipeline is an HTTP service configured by `PIPELINE_URL`. The raw file is sent as
  `multipart/form-data` (`document_id` and `file`, named `<document_id><ext>`), so the two
  services need no shared volume. The pipeline answers right away and then reports its stage
  results and the extracted boreholes back through the regular API endpoints.
  """

  require Logger

  alias Api.Boreholes
  alias Api.Boreholes.Document

  @doc "The configured pipeline endpoint, or `nil` if uploads are not processed."
  def url, do: Application.get_env(:api, :pipeline_url)

  @doc """
  Sends the document to the pipeline in the background and marks it `processing`, or `failed`
  if the pipeline refuses it or cannot be reached. Does nothing if no pipeline is configured.
  """
  @spec submit_async(Document.t()) :: :ok
  def submit_async(%Document{} = document) do
    if url() do
      {:ok, document} = Boreholes.update_document_status(document, "processing")
      Task.Supervisor.start_child(Api.TaskSupervisor, fn -> submit_and_track(document) end)
    end

    :ok
  end

  defp submit_and_track(document) do
    case submit(document) do
      :ok ->
        :ok

      {:error, reason} ->
        Logger.error("pipeline submit failed for document #{document.id}: #{inspect(reason)}")
        Boreholes.update_document_status(document, "failed")
    end
  end

  @doc false
  def submit(%Document{} = document) do
    with path when is_binary(path) <- Boreholes.document_file_path(document),
         {:ok, binary} <- File.read(path) do
      options =
        [
          url: url(),
          form_multipart: [
            document_id: document.id,
            file: {binary, filename: document.storage_path, content_type: document.mime_type}
          ],
          retry: false,
          receive_timeout: 30_000
        ] ++ Application.get_env(:api, :pipeline_req_options, [])

      case Req.post(options) do
        {:ok, %Req.Response{status: status}} when status in 200..299 -> :ok
        {:ok, %Req.Response{status: status}} -> {:error, {:status, status}}
        {:error, reason} -> {:error, reason}
      end
    else
      nil -> {:error, :file_missing}
      {:error, reason} -> {:error, reason}
    end
  end
end
