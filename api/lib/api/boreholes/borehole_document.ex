defmodule Api.Boreholes.BoreholeDocument do
  @moduledoc """
  Join schema for the many-to-many `boreholes` <-> `documents` relationship.

  A schema module (rather than a bare table-name string) is required so that
  `join_defaults` can populate the join table's NOT NULL timestamps on `put_assoc`.
  """
  use Ecto.Schema

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "borehole_documents" do
    belongs_to :borehole, Api.Boreholes.Borehole
    belongs_to :document, Api.Boreholes.Document

    timestamps(type: :utc_datetime)
  end
end
