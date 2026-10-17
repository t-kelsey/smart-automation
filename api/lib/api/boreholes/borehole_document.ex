defmodule Api.Boreholes.BoreholeDocument do
  @moduledoc """
  Join schema for the many-to-many `boreholes` <-> `documents` relationship.

  A schema module (rather than a bare table-name string) is required so that
  `join_defaults` can populate the join table's NOT NULL timestamps on `put_assoc`.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @roles ~w(original additional)

  @doc "The roles a document can have for a borehole."
  def roles, do: @roles

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "borehole_documents" do
    # "original": the one source log the borehole was extracted from (at most one per borehole,
    # ADR-0027); "additional": any further information file.
    field :role, :string, default: "additional"

    belongs_to :borehole, Api.Boreholes.Borehole
    belongs_to :document, Api.Boreholes.Document

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(link, attrs) do
    link
    |> cast(attrs, [:borehole_id, :document_id, :role])
    |> validate_required([:borehole_id, :document_id, :role])
    |> validate_inclusion(:role, @roles)
    |> unique_constraint([:borehole_id, :document_id])
    |> unique_constraint(:borehole_id,
      name: :borehole_documents_one_original_index,
      message: "already has an original document"
    )
  end
end
