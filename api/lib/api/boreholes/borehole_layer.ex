defmodule Api.Boreholes.BoreholeLayer do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "borehole_layers" do
    field :position, :integer
    field :depth_from_m, :decimal
    field :depth_to_m, :decimal
    field :stratigraphy, :string
    field :petrography, :string
    field :color, :string
    field :raw_text, :string

    belongs_to :borehole, Api.Boreholes.Borehole

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(borehole_layer, attrs) do
    borehole_layer
    |> cast(attrs, [
      :position,
      :depth_from_m,
      :depth_to_m,
      :stratigraphy,
      :petrography,
      :color,
      :raw_text
    ])
    |> validate_required([:position, :depth_from_m, :depth_to_m])
    |> validate_number(:depth_from_m, greater_than_or_equal_to: 0)
    |> validate_number(:depth_to_m, greater_than_or_equal_to: 0)
    |> validate_depth_range()
  end

  # Ecto has no built-in cross-field comparison validator, so depth_to_m > depth_from_m is checked manually.
  defp validate_depth_range(changeset) do
    depth_from = get_field(changeset, :depth_from_m)
    depth_to = get_field(changeset, :depth_to_m)

    if depth_from && depth_to && Decimal.compare(depth_to, depth_from) != :gt do
      add_error(changeset, :depth_to_m, "must be greater than depth_from_m")
    else
      changeset
    end
  end
end
