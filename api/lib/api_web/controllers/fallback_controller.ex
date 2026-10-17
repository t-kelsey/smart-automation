defmodule ApiWeb.FallbackController do
  @moduledoc "Turns `{:error, ...}` results of controller actions into JSON error responses."
  use ApiWeb, :controller

  def call(conn, {:error, :not_found}) do
    conn
    |> put_status(:not_found)
    |> put_view(json: ApiWeb.ErrorJSON)
    |> render(:"404")
  end

  def call(conn, {:error, message}) when is_binary(message) do
    conn
    |> put_status(:bad_request)
    |> json(%{errors: %{detail: message}})
  end
end
