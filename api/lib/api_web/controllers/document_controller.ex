defmodule ApiWeb.DocumentController do
  use ApiWeb, :controller

  alias Api.Boreholes

  action_fallback ApiWeb.FallbackController

  @doc """
  Uploads a raw document (multipart field `file`). It is stored (ADR-0014) and handed to the
  extraction pipeline in the background (ADR-0033, `PIPELINE_URL`); the response is `202` with
  the document, whose `status` moves from `processing` to `extracted`/`failed`/... as the
  pipeline reports back.
  """
  def create(conn, %{"file" => %Plug.Upload{} = upload}) do
    with {:ok, document} <- Boreholes.create_uploaded_document(upload) do
      Api.Pipeline.submit_async(document)
      document = Boreholes.get_document(document.id)

      conn
      |> put_status(:accepted)
      |> render(:create, document: document)
    end
  end

  def create(_conn, _params), do: {:error, "multipart field \"file\" is required"}

  @doc "Metadata of a single document and the boreholes it belongs to (never the storage path)."
  def show(conn, %{"id" => id}) do
    case Boreholes.get_document_with_boreholes(id) do
      nil -> {:error, :not_found}
      document -> render(conn, :show, document: document)
    end
  end

  @doc """
  Streams a source document from the managed storage, for viewing in the application
  (ADR-0026). `?download=1` asks the browser to save it instead of displaying it.
  """
  def file(conn, %{"id" => id} = params) do
    with %{} = document <- Boreholes.get_document(id),
         path when is_binary(path) <- Boreholes.document_file_path(document) do
      disposition = if params["download"] in ["1", "true"], do: "attachment", else: "inline"

      conn
      |> put_resp_content_type(document.mime_type || MIME.from_path(path), nil)
      |> put_resp_header("content-disposition", content_disposition(disposition, document))
      # Confidential: keep it out of shared caches and search engines.
      |> put_resp_header("cache-control", "private, no-store")
      |> put_resp_header("x-robots-tag", "noindex")
      |> send_file(200, path)
    else
      _ -> {:error, :not_found}
    end
  end

  defp content_disposition(type, document) do
    filename = document.original_filename
    ascii = String.replace(filename, ~r/[^\x20-\x7E]|["\\]/u, "_")

    ~s(#{type}; filename="#{ascii}"; filename*=UTF-8''#{URI.encode(filename, &URI.char_unreserved?/1)})
  end
end
