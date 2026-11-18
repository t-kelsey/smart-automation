defmodule ApiWeb.FlagController do
  use ApiWeb, :controller

  alias Api.Boreholes.Review

  action_fallback ApiWeb.FallbackController

  @doc "A human confirms a flagged value (ADR-0006); answers with the borehole."
  def resolve(conn, %{"id" => id}) do
    with {:ok, borehole} <- Review.resolve_flag(id) do
      conn |> put_view(json: ApiWeb.BoreholeJSON) |> render(:show, borehole: borehole)
    end
  end
end
