defmodule Api.Boreholes.StageDocumentLink do
  @moduledoc """
  Many-to-many join between `Api.Boreholes.ExecStage` and `Api.Boreholes.Document` (ADR-0034):
  a `filter` stage links only to the original source document; an `extract`/`transform` stage for
  one borehole can link to both the original source document and its split-out per-borehole PDF.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "stage_document_links" do
    belongs_to :exec_stage, Api.Boreholes.ExecStage
    belongs_to :document, Api.Boreholes.Document

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(stage_document_link, attrs) do
    stage_document_link
    |> cast(attrs, [:exec_stage_id, :document_id])
    |> validate_required([:exec_stage_id, :document_id])
    |> foreign_key_constraint(:exec_stage_id)
    |> foreign_key_constraint(:document_id)
    |> unique_constraint([:exec_stage_id, :document_id])
  end
end
