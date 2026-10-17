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
    post "/boreholes", BoreholeController, :create

    post "/documents", DocumentController, :create
    get "/documents/:id", DocumentController, :show
    get "/documents/:id/file", DocumentController, :file
    put "/documents/:id/status", DocumentController, :update_status

    post "/exec_stages", ExecStageController, :create
    get "/exec_stages/:id", ExecStageController, :show
    put "/exec_stages/:id", ExecStageController, :update
    get "/documents/:document_id/exec_stages", ExecStageController, :index

    post "/reports", ReportController, :create

    post "/pipeline_runs", PipelineRunController, :create
    get "/pipeline_runs", PipelineRunController, :index
    get "/pipeline_runs/:id", PipelineRunController, :show
    put "/pipeline_runs/:id/status", PipelineRunController, :update_status
    post "/pipeline_runs/:id/stop", PipelineRunController, :stop
    delete "/pipeline_runs/:id", PipelineRunController, :delete
  end
end
