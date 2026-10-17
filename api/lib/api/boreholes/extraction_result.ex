defmodule Api.Boreholes.ExtractionResult do
  @moduledoc """
  What `bem/`'s extraction stage produced for one `TriageSection` — 1:1, cascades on delete when
  the section is reinserted on a rerun (design doc: docs/elixir-backend-borehole-pipeline.md,
  "Proposed Extension: Pipeline Stage Tracking"). Debug/internal only.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @statuses ~w(ok error)

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "extraction_results" do
    field :status, :string
    field :extracted_fields, :map
    field :validation_issues, :map
    field :error, :string

    belongs_to :triage_section, Api.Boreholes.TriageSection
    has_one :sink_result, Api.Boreholes.SinkResult

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(extraction_result, attrs) do
    extraction_result
    |> cast(attrs, [:status, :extracted_fields, :validation_issues, :error])
    |> validate_required([:status])
    |> validate_inclusion(:status, @statuses)
    |> unique_constraint(:triage_section_id)
  end
end
