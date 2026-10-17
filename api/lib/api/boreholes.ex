defmodule Api.Boreholes do
  @moduledoc """
  The Boreholes context: querying boreholes, their layers and documents.
  """

  import Ecto.Query, warn: false
  alias Api.Repo

  alias Api.Boreholes.Borehole
  alias Api.Boreholes.BoreholeDocument
  alias Api.Boreholes.BoreholeLayer
  alias Api.Boreholes.Document

  @typedoc """
  Filters for `list_boreholes/1`; every key is optional.

    * `:bbox` - `%{min_lon:, min_lat:, max_lon:, max_lat:}`
    * `:q` - case-insensitive text search; adds a relevance `score` and a `snippet`
    * `:verified` - boolean
    * `:drilled_from`, `:drilled_to` - `Date`, inclusive
    * `:min_depth`, `:max_depth` - number, compared with `total_depth_m`
    * `:sort` - `{field, :asc | :desc}` with field `:name`, `:drilled_at`, `:total_depth_m`,
      `:inserted_at` or `:score` (only with `:q`); defaults to score (with `:q`) or name
    * `:limit`, `:offset` - paging; without `:limit` every match is returned
  """
  @type filters :: map()

  @typedoc "One result row; `score`/`snippet` are `nil` unless the query had a `:q`."
  @type entry :: %{borehole: Borehole.t(), score: integer() | nil, snippet: String.t() | nil}

  @doc """
  Lists boreholes matching `filters` (see `t:filters/0`).

  Returns the requested page and the total number of matches across all pages.
  """
  @spec list_boreholes(filters()) :: %{entries: [entry()], total: non_neg_integer()}
  def list_boreholes(filters \\ %{}) do
    query = filtered_query(filters)

    total =
      query
      |> exclude(:select)
      |> select([b], b.id)
      |> subquery()
      |> Repo.aggregate(:count)

    entries =
      query
      |> order(filters)
      |> page(filters)
      |> Repo.all()

    %{entries: entries, total: total}
  end

  @doc """
  Fetches a borehole by id, preloading its documents and layers (ordered by position).

  Each document carries its `role` for this borehole; the original document comes first.

  Returns `nil` if the id is not a valid UUID or no such borehole exists.
  """
  def get_borehole(id) do
    with {:ok, uuid} <- Ecto.UUID.cast(id),
         %Borehole{} = borehole <- Repo.get(Borehole, uuid) do
      layers_query = from(l in BoreholeLayer, order_by: l.position)
      borehole = Repo.preload(borehole, borehole_layers: layers_query)
      %{borehole | documents: list_documents(borehole)}
    else
      _ -> nil
    end
  end

  # Documents of a borehole with their role, the original first.
  defp list_documents(%Borehole{id: borehole_id}) do
    from(d in Document,
      join: bd in BoreholeDocument,
      on: bd.document_id == d.id,
      where: bd.borehole_id == ^borehole_id,
      order_by: [desc: bd.role, asc: d.original_filename],
      select: %{d | role: bd.role}
    )
    |> Repo.all()
  end

  @doc """
  Links documents to a borehole: `original` becomes its original document (or `nil` for none),
  `additional` its further information files. Fails if the borehole already has an original.
  """
  @spec attach_documents(Borehole.t(), Document.t() | nil, [Document.t()]) ::
          {:ok, [BoreholeDocument.t()]} | {:error, Ecto.Changeset.t()}
  def attach_documents(%Borehole{id: borehole_id}, original, additional \\ []) do
    links =
      Enum.reject([{original, "original"} | Enum.map(additional, &{&1, "additional"})], fn {doc,
                                                                                            _} ->
        is_nil(doc)
      end)

    Repo.transaction(fn ->
      Enum.map(links, fn {document, role} ->
        %BoreholeDocument{}
        |> BoreholeDocument.changeset(%{
          borehole_id: borehole_id,
          document_id: document.id,
          role: role
        })
        |> Repo.insert()
        |> case do
          {:ok, link} -> link
          {:error, changeset} -> Repo.rollback(changeset)
        end
      end)
    end)
  end

  @doc """
  Fetches a document by id; `nil` if the id is not a valid UUID or no such document exists.
  """
  def get_document(id) do
    case Ecto.UUID.cast(id) do
      {:ok, uuid} -> Repo.get(Document, uuid)
      :error -> nil
    end
  end

  @doc """
  Like `get_document/1`, with the linked boreholes preloaded (ordered by name).
  """
  def get_document_with_boreholes(id) do
    case get_document(id) do
      nil -> nil
      document -> Repo.preload(document, boreholes: from(b in Borehole, order_by: b.name))
    end
  end

  @doc """
  Absolute path of the document's file in the managed storage (ADR-0014), or `nil` if there is
  none. Only plain file names directly inside the storage directory are accepted, so a
  `storage_path` can never point elsewhere on disk.
  """
  def document_file_path(%Document{storage_path: storage_path}) when is_binary(storage_path) do
    path = Path.join(storage_dir(), storage_path)

    if Path.basename(storage_path) == storage_path and storage_path not in [".", ".."] and
         File.regular?(path),
       do: path
  end

  def document_file_path(_document), do: nil

  defp storage_dir do
    Application.get_env(:api, :document_storage_dir) ||
      Path.join(:code.priv_dir(:api), "storage")
  end

  # -- Query building --------------------------------------------------------------------------

  defp filtered_query(filters) do
    base =
      case blank_to_nil(filters[:q]) do
        nil ->
          from(b in Borehole, as: :borehole, select: %{borehole: b, score: nil, snippet: nil})

        q ->
          search_query(q)
      end

    Enum.reduce(filters, base, &filter/2)
  end

  defp filter(
         {:bbox, %{min_lon: min_lon, min_lat: min_lat, max_lon: max_lon, max_lat: max_lat}},
         q
       ) do
    where(
      q,
      [borehole: b],
      fragment(
        "? && ST_MakeEnvelope(?, ?, ?, ?, 4326)",
        b.location,
        ^min_lon,
        ^min_lat,
        ^max_lon,
        ^max_lat
      )
    )
  end

  defp filter({:verified, verified}, q) when is_boolean(verified),
    do: where(q, [borehole: b], b.verified == ^verified)

  defp filter({:drilled_from, %Date{} = date}, q),
    do: where(q, [borehole: b], b.drilled_at >= ^date)

  defp filter({:drilled_to, %Date{} = date}, q),
    do: where(q, [borehole: b], b.drilled_at <= ^date)

  defp filter({:min_depth, depth}, q) when is_number(depth),
    do: where(q, [borehole: b], b.total_depth_m >= ^depth)

  defp filter({:max_depth, depth}, q) when is_number(depth),
    do: where(q, [borehole: b], b.total_depth_m <= ^depth)

  defp filter(_other, q), do: q

  # Matches borehole fields and any layer's text. The score weights where the term was found;
  # the snippet is the description of the first matching layer, if any.
  defp search_query(q) do
    term = "%" <> escape_like(q) <> "%"

    layer_hits =
      from(l in BoreholeLayer,
        where:
          ilike(l.stratigraphy, ^term) or ilike(l.petrography, ^term) or ilike(l.color, ^term) or
            ilike(l.raw_text, ^term),
        group_by: l.borehole_id,
        select: %{
          borehole_id: l.borehole_id,
          hits: count(l.id),
          snippet:
            fragment(
              "(array_agg(coalesce(?, ?, ?) ORDER BY ?))[1]",
              l.petrography,
              l.raw_text,
              l.stratigraphy,
              l.position
            )
        }
      )

    from(b in Borehole,
      as: :borehole,
      left_join: lh in subquery(layer_hits),
      on: lh.borehole_id == b.id,
      as: :hits,
      where:
        ilike(b.name, ^term) or ilike(b.external_id, ^term) or ilike(b.place, ^term) or
          ilike(b.purpose, ^term) or ilike(b.client, ^term) or not is_nil(lh.borehole_id),
      select: %{
        borehole: b,
        score:
          selected_as(
            fragment(
              "(CASE WHEN ? ILIKE ? THEN 10 ELSE 0 END) + (CASE WHEN ? ILIKE ? THEN 8 ELSE 0 END) + (CASE WHEN ? ILIKE ? THEN 5 ELSE 0 END) + (CASE WHEN ? ILIKE ? THEN 3 ELSE 0 END) + (CASE WHEN ? ILIKE ? THEN 3 ELSE 0 END) + coalesce(?, 0)::int",
              b.name,
              ^term,
              b.external_id,
              ^term,
              b.place,
              ^term,
              b.purpose,
              ^term,
              b.client,
              ^term,
              lh.hits
            ),
            :score
          ),
        snippet: lh.snippet
      }
    )
  end

  defp order(query, filters) do
    searching? = blank_to_nil(filters[:q]) != nil

    case Map.get(filters, :sort) || if(searching?, do: {:score, :desc}, else: {:name, :asc}) do
      {:score, dir} when searching? ->
        order_by(query, [borehole: b], [{^nulls_last(dir), selected_as(:score)}, asc: b.name])

      {:score, _dir} ->
        order_by(query, [borehole: b], asc: b.name)

      {field, dir} ->
        order_by(query, [borehole: b], [{^nulls_last(dir), field(b, ^field)}, asc: b.id])
    end
  end

  defp nulls_last(:asc), do: :asc_nulls_last
  defp nulls_last(:desc), do: :desc_nulls_last

  defp page(query, filters) do
    query
    |> then(fn q -> if l = filters[:limit], do: limit(q, ^l), else: q end)
    |> then(fn q -> if o = filters[:offset], do: offset(q, ^o), else: q end)
  end

  defp blank_to_nil(nil), do: nil

  defp blank_to_nil(s) when is_binary(s) do
    case String.trim(s) do
      "" -> nil
      trimmed -> trimmed
    end
  end

  defp escape_like(s), do: String.replace(s, ~r/([\\%_])/, "\\\\\\1")
end
