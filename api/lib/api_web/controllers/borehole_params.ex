defmodule ApiWeb.BoreholeParams do
  @moduledoc """
  Parses and validates the query parameters of the borehole list/search endpoints into the
  filters understood by `Api.Boreholes.list_boreholes/1`.
  """

  alias Api.Boreholes.SearchQuery

  # A prototype limit: the dataset is capped at 10 000 boreholes, so one page may hold them all.
  @max_limit 10_000

  @sort_fields %{
    "name" => :name,
    "drilled_at" => :drilled_at,
    "total_depth_m" => :total_depth_m,
    "inserted_at" => :inserted_at,
    "score" => :score
  }

  @doc """
  Returns `{:ok, filters}` or `{:error, message}` for the first invalid parameter. `q` is parsed
  with `Api.Boreholes.SearchQuery`; its error message is returned as is.
  """
  def parse(params) do
    with {:ok, q} <- optional(params, "q", &SearchQuery.parse/1),
         {:ok, bbox} <- optional(params, "bbox", &parse_bbox/1),
         {:ok, verified} <- optional(params, "verified", &parse_boolean/1),
         {:ok, drilled_from} <- optional(params, "drilled_from", &parse_date/1),
         {:ok, drilled_to} <- optional(params, "drilled_to", &parse_date/1),
         {:ok, min_depth} <- optional(params, "min_depth", &parse_number/1),
         {:ok, max_depth} <- optional(params, "max_depth", &parse_number/1),
         {:ok, sort} <- optional(params, "sort", &parse_sort/1),
         {:ok, limit} <- optional(params, "limit", &parse_integer(&1, 1, @max_limit)),
         {:ok, offset} <- optional(params, "offset", &parse_integer(&1, 0, nil)) do
      filters =
        %{
          q: q,
          bbox: bbox,
          verified: verified,
          drilled_from: drilled_from,
          drilled_to: drilled_to,
          min_depth: min_depth,
          max_depth: max_depth,
          sort: sort,
          limit: limit,
          offset: offset
        }
        |> Map.reject(fn {_key, value} -> is_nil(value) end)

      {:ok, filters}
    end
  end

  defp optional(params, key, parser) do
    case params[key] do
      nil -> {:ok, nil}
      "" -> {:ok, nil}
      value -> with :error <- parser.(value), do: {:error, "invalid #{key}"}
    end
  end

  defp parse_bbox(value) do
    with [min_lon, min_lat, max_lon, max_lat] <- String.split(value, ","),
         {:ok, min_lon} <- parse_number(min_lon),
         {:ok, min_lat} <- parse_number(min_lat),
         {:ok, max_lon} <- parse_number(max_lon),
         {:ok, max_lat} <- parse_number(max_lat) do
      {:ok, %{min_lon: min_lon, min_lat: min_lat, max_lon: max_lon, max_lat: max_lat}}
    else
      _ -> :error
    end
  end

  defp parse_boolean("true"), do: {:ok, true}
  defp parse_boolean("false"), do: {:ok, false}
  defp parse_boolean(_), do: :error

  defp parse_date(value) do
    case Date.from_iso8601(value) do
      {:ok, date} -> {:ok, date}
      _ -> :error
    end
  end

  defp parse_number(value) do
    case Float.parse(String.trim(value)) do
      {number, ""} -> {:ok, number}
      _ -> :error
    end
  end

  defp parse_integer(value, min, max) do
    case Integer.parse(value) do
      {int, ""} when int >= min and (is_nil(max) or int <= max) -> {:ok, int}
      _ -> :error
    end
  end

  # "name" sorts ascending, "-name" descending.
  defp parse_sort("-" <> field), do: sort_field(field, :desc)
  defp parse_sort(field), do: sort_field(field, :asc)

  defp sort_field(field, dir) do
    case @sort_fields[field] do
      nil -> :error
      key -> {:ok, {key, dir}}
    end
  end
end
