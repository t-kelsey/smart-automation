defmodule Api.Boreholes.TriageSection do
  @moduledoc """
  One borehole candidate that `bem/`'s triage stage found within a document — the fan-out point
  from one document to many boreholes (design doc: docs/elixir-backend-borehole-pipeline.md,
  "Proposed Extension: Pipeline Stage Tracking"). Debug/internal only. Latest run only: a rerun
  deletes all existing sections for the document and reinserts the new set.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "triage_sections" do
    field :section_index, :integer
    field :borehole_id_guess, :string
    field :raw_markdown, :string
    field :translate_errors, {:array, :string}, default: []

    belongs_to :document, Api.Boreholes.Document
    has_one :extraction_result, Api.Boreholes.ExtractionResult

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(triage_section, attrs) do
    triage_section
    |> cast(attrs, [:section_index, :borehole_id_guess, :raw_markdown, :translate_errors])
    |> validate_required([:section_index])
    |> validate_number(:section_index, greater_than_or_equal_to: 0)
    |> unique_constraint([:document_id, :section_index])
  end
end
