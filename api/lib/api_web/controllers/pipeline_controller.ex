defmodule ApiWeb.PipelineController do
  @moduledoc """
  Write endpoints `bem/` reports pipeline stage results to (design doc:
  docs/elixir-backend-borehole-pipeline.md, "Proposed Extension: Pipeline Stage Tracking").
  Debug/internal only — never consumed by `web/`. Every action is a `PUT`: latest run only, each
  call replaces the previous result for that document/stage/section instead of keeping history.
  """
  use ApiWeb, :controller

  alias Api.Boreholes

  action_fallback ApiWeb.FallbackController

  @doc "Upserts the OCR or translation result for a document."
  def put_stage(conn, %{"document_id" => document_id, "stage" => stage} = params) do
    with {:ok, run} <- Boreholes.put_pipeline_stage_run(document_id, stage, params) do
      render(conn, :stage, run: run)
    end
  end

  @doc "Replaces all triage sections for a document."
  def put_triage_sections(conn, %{"document_id" => document_id} = params) do
    with {:ok, sections} <-
           Boreholes.replace_triage_sections(document_id, params["sections"] || []) do
      render(conn, :sections, sections: sections)
    end
  end

  @doc "Upserts the extraction result for one triage section."
  def put_extraction_result(
        conn,
        %{"document_id" => document_id, "section_index" => section_index} = params
      ) do
    with {:ok, index} <- parse_index(section_index),
         {:ok, result} <- Boreholes.put_extraction_result(document_id, index, params) do
      render(conn, :extraction_result, result: result)
    end
  end

  @doc "Upserts the sink result for one triage section's extraction."
  def put_sink_result(
        conn,
        %{"document_id" => document_id, "section_index" => section_index} = params
      ) do
    with {:ok, index} <- parse_index(section_index),
         {:ok, result} <- Boreholes.put_sink_result(document_id, index, params) do
      render(conn, :sink_result, result: result)
    end
  end

  defp parse_index(section_index) when is_integer(section_index), do: {:ok, section_index}

  defp parse_index(section_index) when is_binary(section_index) do
    case Integer.parse(section_index) do
      {index, ""} -> {:ok, index}
      _ -> {:error, "invalid section_index"}
    end
  end

  defp parse_index(_section_index), do: {:error, "invalid section_index"}
end
