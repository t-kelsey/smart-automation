defmodule Api.Boreholes.JsonValue do
  @moduledoc """
  Ecto type for a jsonb column that holds any JSON value (number, string, object, ...), used for
  the old/new value of `Api.Boreholes.FieldEdit`. `nil` is stored as SQL `NULL`.
  """
  use Ecto.Type

  @impl true
  def type, do: :map

  @impl true
  def cast(value), do: {:ok, value}

  @impl true
  def load(value), do: {:ok, value}

  @impl true
  def dump(value), do: {:ok, value}
end
