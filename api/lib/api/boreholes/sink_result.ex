defmodule Api.Boreholes.SinkResult do
  @moduledoc """
  What happened when `bem/`'s output stage delivered one `ExtractionResult` — 1:1, cascades on
  delete (design doc: docs/elixir-backend-borehole-pipeline.md, "Proposed Extension: Pipeline
  Stage Tracking"). Debug/internal only. `created_borehole_id` is set once the API has actually
  created the borehole; it is cleared (not cascaded) if that borehole is later deleted.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @targets ~w(api json print)

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "sink_results" do
    field :target, :string
    field :success, :boolean
    field :response_status, :integer
    field :error, :string

    belongs_to :extraction_result, Api.Boreholes.ExtractionResult
    belongs_to :created_borehole, Api.Boreholes.Borehole

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(sink_result, attrs) do
    sink_result
    |> cast(attrs, [:target, :success, :response_status, :created_borehole_id, :error])
    |> validate_required([:target, :success])
    |> validate_inclusion(:target, @targets)
    |> unique_constraint(:extraction_result_id)
    |> foreign_key_constraint(:created_borehole_id)
  end
end
