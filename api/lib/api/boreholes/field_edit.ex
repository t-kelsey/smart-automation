defmodule Api.Boreholes.FieldEdit do
  @moduledoc """
  Append-only history of a changed value (ADR-0006). `field` is the API column name, `location`
  for the coordinates (value: GeoJSON point) or `layer` for a created/deleted layer (value: the
  layer's snapshot). `old_value`/`new_value` are any JSON. `layer_id` has no foreign key, so the
  history survives a deleted layer. `source` is `validator` or `human`.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "field_edits" do
    field :layer_id, :binary_id
    field :field, :string
    field :old_value, Api.Boreholes.JsonValue
    field :new_value, Api.Boreholes.JsonValue
    field :source, :string
    field :reason, :string

    belongs_to :borehole, Api.Boreholes.Borehole

    timestamps(type: :utc_datetime_usec, updated_at: false)
  end

  # borehole_id, layer_id and source are set by the caller, not cast
  @doc false
  def changeset(edit, attrs) do
    edit
    |> cast(attrs, [:field, :old_value, :new_value, :reason])
    |> validate_required([:field])
  end
end
