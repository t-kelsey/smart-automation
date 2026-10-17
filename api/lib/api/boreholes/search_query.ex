defmodule Api.Boreholes.SearchQuery do
  @moduledoc """
  The borehole search query language (ADR-0042, docs/api-reference.md).

  A query is a list of terms separated by spaces. A borehole matches if it matches every term.

    * `word`, `"a phrase"` - the name, external id or place contains it (case-insensitive)
    * `name:word` (or `n:`) - the name or external id contains it
    * `place:word` (or `location:`, `loc:`) - the place contains it
    * `date:1959`, `date:1959-06`, `date:1959-06-12`, `date:12.06.1959` - drilled in that year,
      month or on that day (or `drilled:`, `year:`)
    * `date:1950..1960`, `date:1990..`, `date:..1960` - inclusive ranges, open on one side
    * `date:>1990`, `date:>=1990`, `date:<2000`, `date:<=2000` - comparisons;
      `after:1990` is `date:>1990`, `before:2000` is `date:<2000`
    * a bare year, date or date range (`1959`, `1950..1960`) is a date term; quote it to search
      for it as text
    * `a,b` - either value, e.g. `place:Bern,Basel`
    * `-term` - must not match, e.g. `-place:Bern`

  Parsing only builds terms; `Api.Boreholes` turns them into SQL.
  """

  defstruct terms: []

  @type field :: :text | :name | :place | :date
  @type date_range :: {Date.t() | nil, Date.t() | nil}

  @typedoc """
  One term. `key` is the field prefix as typed (`nil` for a bare term), `raw` the values as typed
  (with whether they were quoted), `values` what is matched: strings for text fields, inclusive
  date ranges for `:date`. A term with an unknown key (`unknown_key: true`) is searched as text.
  """
  @type term_t :: %{
          field: field(),
          key: String.t() | nil,
          negate: boolean(),
          raw: [{String.t(), boolean()}],
          values: [String.t()] | [date_range()],
          unknown_key: boolean()
        }

  @type t :: %__MODULE__{terms: [term_t()]}

  @keys %{
    "name" => :name,
    "n" => :name,
    "place" => :place,
    "location" => :place,
    "loc" => :place,
    "date" => :date,
    "drilled" => :date,
    "year" => :date,
    "after" => :after,
    "before" => :before
  }

  # -?  key:?  value(,value)*  where a value is "quoted" or a run of other characters
  @token ~r/(-?)(?:([[:alpha:]]+):)?((?:"[^"]*"?|[^\s",]+)(?:,(?:"[^"]*"?|[^\s",]+))*)/u
  @value ~r/"[^"]*"?|[^\s",]+/u

  @doc "The field keys of the language, for autocorrection."
  def keys, do: Map.keys(@keys)

  @doc """
  Parses a query string. Returns `{:error, message}` for an invalid date or a field without a
  value.
  """
  @spec parse(String.t()) :: {:ok, t()} | {:error, String.t()}
  def parse(string) when is_binary(string) do
    @token
    |> Regex.scan(string, capture: :all)
    |> Enum.reduce_while({:ok, []}, fn [source, minus, key, values], {:ok, acc} ->
      case parse_term(source, minus == "-", blank_to_nil(key), values) do
        {:ok, nil} -> {:cont, {:ok, acc}}
        {:ok, term} -> {:cont, {:ok, [term | acc]}}
        {:error, _} = error -> {:halt, error}
      end
    end)
    |> case do
      {:ok, terms} -> {:ok, %__MODULE__{terms: Enum.reverse(terms)}}
      error -> error
    end
  end

  @doc "Like `parse/1`, but raises `ArgumentError` for an invalid query."
  @spec parse!(String.t()) :: t()
  def parse!(string) do
    case parse(string) do
      {:ok, query} -> query
      {:error, message} -> raise ArgumentError, message
    end
  end

  @typedoc """
  The term at the end of a query that is being typed (ADR-0043): `partial` is its unfinished
  value, `field` where to look for completions, and `prefix` everything before the value that
  stays (the rest of the query, `-`, the key and earlier comma alternatives).
  """
  @type completion_target :: %{
          prefix: String.t(),
          field: :text | :name | :place | :key,
          partial: String.t()
        }

  @doc """
  What the term being typed at the end of `query` can be completed to: none (empty query, a
  trailing space, dates, unknown keys), its field's values, and for a bare word also the keys it
  starts (`pla` to `place:`, `field: :key`).
  """
  @spec completion_targets(String.t()) :: [completion_target()]
  def completion_targets(query) when is_binary(query) do
    {head, token} = String.split_at(query, last_token_start(query))
    [_, minus, key, value] = Regex.run(~r/^(-?)(?:([[:alpha:]]+):)?(.*)$/su, token)
    # With comma alternatives only the value after the last comma is completed.
    {alternatives, partial} =
      case Regex.run(~r/^(.*,)([^,]*)$/su, value) do
        [_, alternatives, partial] -> {alternatives, partial}
        nil -> {"", value}
      end

    partial = String.trim(partial, "\"")
    prefix = head <> minus <> if(key == "", do: "", else: key <> ":") <> alternatives

    cond do
      String.trim(partial) == "" ->
        []

      key == "" ->
        target = %{prefix: prefix, field: :text, partial: partial}

        if alternatives == "" and minus == "" and Regex.match?(~r/^[[:alpha:]]+$/u, partial),
          do: [%{target | field: :key}, target],
          else: [target]

      true ->
        case Map.get(@keys, String.downcase(key)) do
          field when field in [:name, :place] ->
            [%{prefix: prefix, field: field, partial: partial}]

          _ ->
            []
        end
    end
  end

  @doc """
  The query with the target's partial value replaced by `value`, quoted if needed, followed by a
  space so the next term can be typed. A key (`field: :key`) is completed as `key:`.
  """
  @spec complete(completion_target(), String.t()) :: String.t()
  def complete(%{field: :key, prefix: prefix}, key), do: prefix <> key <> ":"

  def complete(%{field: field, prefix: prefix}, value) do
    value = String.replace(value, "\"", "")
    # A bare year or date would be read as a date, a space or comma would split the value.
    quote? =
      String.match?(value, ~r/[\s,]/u) or (field == :text and match?({:ok, _}, parse_date(value)))

    prefix <> if(quote?, do: ~s("#{value}"), else: value) <> " "
  end

  @doc "Keys starting with `partial` (case-insensitive), shortest first."
  @spec keys_starting_with(String.t()) :: [String.t()]
  def keys_starting_with(partial) do
    partial = String.downcase(partial)

    @keys
    |> Map.keys()
    |> Enum.filter(&String.starts_with?(&1, partial))
    |> Enum.sort_by(&{String.length(&1), &1})
  end

  # Index (in graphemes) where the last term starts: after the last space outside quotes.
  defp last_token_start(query) do
    query
    |> String.graphemes()
    |> Enum.with_index()
    |> Enum.reduce({false, 0}, fn
      {"\"", _index}, {quoted, start} -> {not quoted, start}
      {char, index}, {false, start} -> {false, if(char =~ ~r/^\s$/u, do: index + 1, else: start)}
      _char, acc -> acc
    end)
    |> elem(1)
  end

  @doc "Writes the query back as a query string."
  @spec to_string(t()) :: String.t()
  def to_string(%__MODULE__{terms: terms}), do: Enum.map_join(terms, " ", &term_to_string/1)

  @doc """
  Autocorrects a query (ADR-0042). Unknown keys become the closest known key, and every unquoted
  text value of at least 3 characters in a term that is not negated is replaced by
  `correct.(field, value)` unless that returns `nil`. Returns the corrected query.
  """
  @spec correct(t(), (field(), String.t() -> String.t() | nil)) :: t()
  def correct(%__MODULE__{terms: terms} = query, correct) do
    %{query | terms: Enum.map(terms, &(&1 |> correct_key() |> correct_values(correct)))}
  end

  defp correct_key(%{unknown_key: true, key: key} = term) do
    with closest when closest != nil <- closest_key(key),
         {:ok, %{terms: [corrected]}} <- parse(term_to_string(%{term | key: closest})) do
      corrected
    else
      _ -> term
    end
  end

  defp correct_key(term), do: term

  defp closest_key(key) do
    key = String.downcase(key)

    {closest, distance} =
      @keys
      |> Map.keys()
      |> Enum.map(&{&1, String.jaro_distance(&1, key)})
      |> Enum.max_by(&elem(&1, 1))

    if distance >= 0.75, do: closest
  end

  defp correct_values(%{field: field, negate: false, unknown_key: false} = term, correct)
       when field in [:text, :name, :place] do
    raw =
      Enum.map(term.raw, fn
        {text, false} = value ->
          if String.length(text) >= 3, do: {correct.(field, text) || text, false}, else: value

        quoted ->
          quoted
      end)

    %{term | raw: raw, values: Enum.map(raw, &elem(&1, 0))}
  end

  defp correct_values(term, _correct), do: term

  defp parse_term(source, negate, key, values_source) do
    raw =
      @value
      |> Regex.scan(values_source)
      |> Enum.map(fn [value] -> unquote_value(value) end)
      |> Enum.reject(fn {text, _quoted} -> String.trim(text) == "" end)

    term = %{field: :text, key: key, negate: negate, raw: raw, values: [], unknown_key: false}

    case key && Map.get(@keys, String.downcase(key)) do
      _ when raw == [] ->
        {:ok, nil}

      nil when key != nil ->
        # An unknown key is not a field: search the whole token as text.
        text = if negate, do: String.slice(source, 1..-1//1), else: source
        {:ok, %{term | values: [text], unknown_key: true}}

      nil ->
        bare_term(term)

      field when field in [:name, :place] ->
        {:ok, %{term | field: field, values: Enum.map(raw, &elem(&1, 0))}}

      field ->
        date_term(term, field)
    end
  end

  # A bare value is a date term if every value is an unquoted date; a lone "name:" is an error.
  defp bare_term(%{raw: raw} = term) do
    texts = Enum.map(raw, &elem(&1, 0))

    dates =
      Enum.map(raw, fn
        {text, false} -> parse_date(text)
        _quoted -> :error
      end)

    cond do
      match?([_], texts) and key_without_value?(hd(texts)) ->
        {:error, "#{hd(texts)} needs a value, e.g. #{hd(texts)}Bern"}

      Enum.all?(dates, &match?({:ok, _}, &1)) ->
        {:ok, %{term | field: :date, values: Enum.map(dates, &elem(&1, 1))}}

      true ->
        {:ok, %{term | values: texts}}
    end
  end

  defp key_without_value?(text) do
    String.ends_with?(text, ":") and
      Map.has_key?(@keys, text |> String.trim_trailing(":") |> String.downcase())
  end

  defp date_term(%{raw: raw, key: key} = term, field) do
    raw
    |> Enum.reduce_while({:ok, []}, fn {text, _quoted}, {:ok, acc} ->
      prefixed =
        case field do
          :after -> ">" <> text
          :before -> "<" <> text
          :date -> text
        end

      case parse_date(prefixed) do
        {:ok, range} ->
          {:cont, {:ok, [range | acc]}}

        :error ->
          {:halt,
           {:error,
            ~s(invalid date "#{text}" after #{key}:, expected e.g. 1959, 1959-06-12 or 1950..1960)}}
      end
    end)
    |> case do
      {:ok, ranges} -> {:ok, %{term | field: :date, values: Enum.reverse(ranges)}}
      error -> error
    end
  end

  @doc """
  Parses one date value into an inclusive `{from, to}` range (either side may be `nil`):
  a year, month or day, a `from..to` range, or a comparison (`>`, `>=`, `<`, `<=`).
  """
  @spec parse_date(String.t()) :: {:ok, date_range()} | :error
  def parse_date(">=" <> text), do: with({:ok, from, _} <- period(text), do: {:ok, {from, nil}})
  def parse_date("<=" <> text), do: with({:ok, _, to} <- period(text), do: {:ok, {nil, to}})

  def parse_date(">" <> text),
    do: with({:ok, _, to} <- period(text), do: {:ok, {Date.add(to, 1), nil}})

  def parse_date("<" <> text),
    do: with({:ok, from, _} <- period(text), do: {:ok, {nil, Date.add(from, -1)}})

  def parse_date(text) do
    case String.split(text, "..") do
      [single] ->
        with {:ok, from, to} <- period(single), do: {:ok, {from, to}}

      [from, to] when from != "" or to != "" ->
        with {:ok, from} <- range_side(from, :from),
             {:ok, to} <- range_side(to, :to),
             do: {:ok, {from, to}}

      _ ->
        :error
    end
  end

  defp range_side("", _side), do: {:ok, nil}

  defp range_side(text, side) do
    with {:ok, from, to} <- period(text), do: {:ok, if(side == :from, do: from, else: to)}
  end

  # The first and last day of a year, month or day.
  defp period(text) do
    cond do
      match = Regex.run(~r/^(\d{4})$/, text) ->
        [_, y] = match
        dates(Date.new(int(y), 1, 1), Date.new(int(y), 12, 31))

      match = Regex.run(~r/^(\d{4})-(\d{1,2})$/, text) ->
        [_, y, m] = match
        month(int(y), int(m))

      match = Regex.run(~r/^(\d{1,2})\.(\d{4})$/, text) ->
        [_, m, y] = match
        month(int(y), int(m))

      match = Regex.run(~r/^(\d{4})-(\d{1,2})-(\d{1,2})$/, text) ->
        [_, y, m, d] = match
        day(int(y), int(m), int(d))

      match = Regex.run(~r/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/, text) ->
        [_, d, m, y] = match
        day(int(y), int(m), int(d))

      true ->
        :error
    end
  end

  defp month(y, m) do
    with {:ok, first} <- Date.new(y, m, 1), do: {:ok, first, Date.end_of_month(first)}
  end

  defp day(y, m, d) do
    with {:ok, date} <- Date.new(y, m, d), do: {:ok, date, date}
  end

  defp dates({:ok, from}, {:ok, to}), do: {:ok, from, to}
  defp dates(_, _), do: :error

  defp int(text), do: String.to_integer(text)

  defp unquote_value("\"" <> rest), do: {String.trim_trailing(rest, "\""), true}
  defp unquote_value(text), do: {text, false}

  defp term_to_string(%{negate: negate, key: key, raw: raw}) do
    values =
      Enum.map_join(raw, ",", fn
        {text, true} -> ~s("#{text}")
        {text, false} -> text
      end)

    "#{if negate, do: "-"}#{if key, do: key <> ":"}#{values}"
  end

  defp blank_to_nil(""), do: nil
  defp blank_to_nil(s), do: s
end
