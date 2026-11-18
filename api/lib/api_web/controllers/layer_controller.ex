defmodule ApiWeb.LayerController do
  @moduledoc "Human edits of a borehole's layers (ADR-0006); every action answers with the borehole."
  use ApiWeb, :controller

  alias Api.Boreholes.Review

  action_fallback ApiWeb.FallbackController

  def create(conn, %{"id" => id, "layer" => attrs}) when is_map(attrs) do
    with {:ok, borehole} <- Review.create_layer(id, attrs) do
      conn |> put_status(:created) |> render_borehole(borehole)
    end
  end

  def create(_conn, _params), do: {:error, "layer must be an object"}

  def update(conn, %{"id" => id, "layer_id" => layer_id, "layer" => attrs}) when is_map(attrs) do
    with {:ok, borehole} <- Review.update_layer(id, layer_id, attrs),
         do: render_borehole(conn, borehole)
  end

  def update(_conn, _params), do: {:error, "layer must be an object"}

  def delete(conn, %{"id" => id, "layer_id" => layer_id}) do
    with {:ok, borehole} <- Review.delete_layer(id, layer_id), do: render_borehole(conn, borehole)
  end

  defp render_borehole(conn, borehole),
    do: conn |> put_view(json: ApiWeb.BoreholeJSON) |> render(:show, borehole: borehole)
end
