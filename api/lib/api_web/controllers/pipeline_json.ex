defmodule ApiWeb.PipelineJSON do
  @moduledoc """
  Renders `ApiWeb.PipelineController`'s responses. Debug/internal only — exposes `extracted_fields`
  etc. freely, unlike `ApiWeb.DocumentJSON`/`BoreholeJSON`, since none of this is public-facing.
  """

  def stage(%{run: run}) do
    %{
      data: %{
        id: run.id,
        document_id: run.document_id,
        stage: run.stage,
        status: run.status,
        output: run.output,
        error: run.error,
        started_at: run.started_at,
        finished_at: run.finished_at
      }
    }
  end

  def sections(%{sections: sections}) do
    %{
      data:
        Enum.map(sections, fn section ->
          %{
            id: section.id,
            section_index: section.section_index,
            borehole_id_guess: section.borehole_id_guess,
            raw_markdown: section.raw_markdown,
            translate_errors: section.translate_errors
          }
        end)
    }
  end

  def extraction_result(%{result: result}) do
    %{
      data: %{
        id: result.id,
        triage_section_id: result.triage_section_id,
        status: result.status,
        extracted_fields: result.extracted_fields,
        validation_issues: result.validation_issues,
        error: result.error
      }
    }
  end

  def sink_result(%{result: result}) do
    %{
      data: %{
        id: result.id,
        extraction_result_id: result.extraction_result_id,
        target: result.target,
        success: result.success,
        response_status: result.response_status,
        created_borehole_id: result.created_borehole_id,
        error: result.error
      }
    }
  end
end
