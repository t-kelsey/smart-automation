defmodule ApiWeb.Router do
  use ApiWeb, :router

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/api", ApiWeb do
    pipe_through :api

    get "/boreholes/search", BoreholeController, :search
    get "/boreholes/:id", BoreholeController, :show
    get "/boreholes", BoreholeController, :index

    get "/documents/:id/file", DocumentController, :file
  end
end
