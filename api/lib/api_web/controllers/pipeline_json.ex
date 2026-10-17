defmodule ApiWeb.PipelineJSON do
  @moduledoc """
  Renders `ApiWeb.PipelineController`'s responses. Debug/internal only — exposes `extracted_fields`
  etc. freely, unlike `ApiWeb.DocumentJSON`/`BoreholeJSON`, since none of this is public-facing.
  """

  def stage(%{run: run}) do
    %{data: stage_data(run)}
  end

  def sections(%{sections: sections}) do
    %{data: Enum.map(sections, &section_data/1)}
  end

  def extraction_result(%{result: result}) do
    %{data: extraction_result_data(result)}
  end

  def sink_result(%{result: result}) do
    %{data: sink_result_data(result)}
  end

  @doc """
  Full trace for a document: its stage runs, and its triage sections each with their (possibly
  absent) extraction and sink result, for troubleshooting (ADR-0030).
  """
  def trace(%{trace: trace}) do
    %{
      data: %{
        document_id: trace.document.id,
        pipeline_stage_runs: Enum.map(trace.pipeline_stage_runs, &stage_data/1),
        triage_sections: Enum.map(trace.triage_sections, &section_trace_data/1)
      }
    }
  end

  defp section_trace_data(section) do
    extraction = section.extraction_result

    section_data(section)
    |> Map.put(:extraction_result, extraction && extraction_result_data(extraction))
    |> Map.put(
      :sink_result,
      extraction && extraction.sink_result && sink_result_data(extraction.sink_result)
    )
  end

  defp stage_data(run) do
    %{
      id: run.id,
      document_id: run.document_id,
      stage: run.stage,
      status: run.status,
      output: run.output,
      error: run.error,
      started_at: run.started_at,
      finished_at: run.finished_at
    }
  end

  defp section_data(section) do
    %{
      id: section.id,
      section_index: section.section_index,
      borehole_id_guess: section.borehole_id_guess,
      raw_markdown: section.raw_markdown,
      translate_errors: section.translate_errors
    }
  end

  defp extraction_result_data(result) do
    %{
      id: result.id,
      triage_section_id: result.triage_section_id,
      status: result.status,
      extracted_fields: result.extracted_fields,
      validation_issues: result.validation_issues,
      error: result.error
    }
  end

  defp sink_result_data(result) do
    %{
      id: result.id,
      extraction_result_id: result.extraction_result_id,
      target: result.target,
      success: result.success,
      response_status: result.response_status,
      created_borehole_id: result.created_borehole_id,
      error: result.error
    }
  end
end
