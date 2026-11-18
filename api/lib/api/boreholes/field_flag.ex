defmodule Api.Boreholes.FieldFlag do
  @moduledoc """
  A doubt about one value of a borehole (ADR-0006): `field` is the API column name (`location` for
  the coordinates), `layer_id` is `nil` for a borehole-level field (no foreign key: flags of a deleted layer are
  hidden until the layer is restored). `origin` is `rule`
  (`Api.Boreholes.Checks`, with its `code`) or `validator` (the pipeline). A flag is open until
  `resolved_at` is set, by a `human` or by the `rule` that no longer fires.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "field_flags" do
    field :field, :string
    field :severity, :string
    field :message, :string
    field :origin, :string
    field :code, :string
    # optional proposed value (any JSON); accepting it is a normal edit of the field
    field :suggestion, Api.Boreholes.JsonValue
    field :resolved_at, :utc_datetime_usec
    field :resolved_by, :string

    belongs_to :borehole, Api.Boreholes.Borehole
    belongs_to :layer, Api.Boreholes.BoreholeLayer

    timestamps(type: :utc_datetime_usec)
  end

  # borehole_id and layer_id are set by the caller, not cast
  @doc false
  def changeset(flag, attrs) do
    flag
    |> cast(attrs, [:field, :severity, :message, :origin, :code, :suggestion])
    |> validate_required([:field, :severity, :message, :origin])
    |> validate_inclusion(:severity, ~w(warning error))
    |> validate_inclusion(:origin, ~w(rule validator))
  end
end
