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

    get "/documents/:id", DocumentController, :show
    get "/documents/:id/file", DocumentController, :file

    put "/documents/:document_id/pipeline_stages/:stage", PipelineController, :put_stage
    put "/documents/:document_id/triage_sections", PipelineController, :put_triage_sections

    put "/documents/:document_id/triage_sections/:section_index/extraction_result",
        PipelineController,
        :put_extraction_result

    put "/documents/:document_id/triage_sections/:section_index/sink_result",
        PipelineController,
        :put_sink_result
  end
end
