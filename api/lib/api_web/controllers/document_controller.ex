defmodule ApiWeb.DocumentController do
  use ApiWeb, :controller

  alias Api.Boreholes

  action_fallback ApiWeb.FallbackController

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
