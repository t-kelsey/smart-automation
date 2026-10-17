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
  alias Api.Boreholes.ExtractionResult
  alias Api.Boreholes.PipelineStageRun
  alias Api.Boreholes.SinkResult
  alias Api.Boreholes.TriageSection

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
  Creates a borehole with its layers in one transaction. Returns the same shape as
  `get_borehole/1` on success.

  `borehole_attrs` may include `"x"`, `"y"`, `"epsg"` instead of a `"location"` key directly — if
  present, `location` is set via `ST_Transform(ST_SetSRID(ST_MakePoint(x, y), epsg), 4326)`
  (ADR-0002) rather than expecting the caller to reproject coordinates itself.

  Each map in `layers_attrs` gets `"position"` set to its 1-based index if it doesn't have one.

  Options:
    * `:document_id` - an existing `documents.id` to attach as this borehole's original
      document (ADR-0013, via `attach_documents/3`)
  """
  def create_borehole(borehole_attrs, layers_attrs, opts \\ []) do
    Repo.transaction(fn ->
      with {:ok, borehole} <- insert_borehole(borehole_attrs),
           :ok <- set_location(borehole, borehole_attrs),
           {:ok, _layers} <- insert_layers(borehole, layers_attrs),
           :ok <- maybe_attach(borehole, opts) do
        get_borehole(borehole.id)
      else
        {:error, reason} -> Repo.rollback(reason)
      end
    end)
  end

  defp insert_borehole(attrs) do
    %Borehole{} |> Borehole.changeset(attrs) |> Repo.insert()
  end

  defp set_location(borehole, attrs) do
    attrs = stringify_keys(attrs)

    case {attrs["x"], attrs["y"], attrs["epsg"]} do
      {x, y, epsg} when not is_nil(x) and not is_nil(y) and not is_nil(epsg) ->
        query =
          from(b in Borehole, where: b.id == ^borehole.id)
          |> update(
            set: [
              location:
                fragment("ST_Transform(ST_SetSRID(ST_MakePoint(?, ?), ?), 4326)", ^x, ^y, ^epsg)
            ]
          )

        Repo.update_all(query, [])
        :ok

      _ ->
        :ok
    end
  end

  defp insert_layers(borehole, layers_attrs) do
    layers_attrs
    |> Enum.with_index(1)
    |> Enum.reduce_while({:ok, []}, fn {attrs, index}, {:ok, acc} ->
      attrs = attrs |> stringify_keys() |> Map.put_new("position", index)

      %BoreholeLayer{}
      |> BoreholeLayer.changeset(attrs)
      |> Ecto.Changeset.put_change(:borehole_id, borehole.id)
      |> Repo.insert()
      |> case do
        {:ok, layer} -> {:cont, {:ok, [layer | acc]}}
        {:error, changeset} -> {:halt, {:error, changeset}}
      end
    end)
  end

  defp maybe_attach(borehole, opts) do
    case Keyword.get(opts, :document_id) do
      nil ->
        :ok

      document_id ->
        case get_document(document_id) do
          nil ->
            {:error, "document_id does not reference an existing document"}

          document ->
            with {:ok, _links} <- attach_documents(borehole, document, []) do
              :ok
            end
        end
    end
  end

  defp stringify_keys(map) do
    Map.new(map, fn {k, v} -> {to_string(k), v} end)
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

  @upload_extensions ~w(.pdf .png .jpg .jpeg .tif .tiff .docx)

  @doc """
  Stores a freshly uploaded raw file as a new document: the file is copied into the managed
  storage as `<id><ext>` (ADR-0014) and a `documents` row with status `pending` is inserted.
  Only the file types the pipeline can read are accepted.
  """
  @spec create_uploaded_document(Plug.Upload.t()) ::
          {:ok, Document.t()} | {:error, String.t() | Ecto.Changeset.t()}
  def create_uploaded_document(%Plug.Upload{path: path, filename: filename}) do
    extension = filename |> Path.extname() |> String.downcase()

    if extension in @upload_extensions do
      id = Ecto.UUID.generate()
      storage_path = "#{id}#{extension}"
      destination = Path.join(storage_dir(), storage_path)

      with :ok <- File.mkdir_p(storage_dir()),
           :ok <- File.cp(path, destination),
           {:ok, %{size: size}} <- File.stat(destination) do
        attrs = %{
          original_filename: Path.basename(filename),
          storage_path: storage_path,
          mime_type: MIME.from_path(filename),
          size_bytes: size
        }

        case Repo.insert(Document.changeset(%Document{id: id}, attrs)) do
          {:ok, document} ->
            {:ok, document}

          {:error, changeset} ->
            File.rm(destination)
            {:error, changeset}
        end
      else
        {:error, reason} -> {:error, "could not store the file: #{:file.format_error(reason)}"}
      end
    else
      {:error,
       "unsupported file type #{inspect(extension)}, expected one of #{Enum.join(@upload_extensions, ", ")}"}
    end
  end

  @doc "Sets the processing status of a document."
  def update_document_status(%Document{} = document, status) do
    document |> Document.changeset(%{status: status}) |> Repo.update()
  end

  @doc "The directory holding the stored document files (`DOCUMENT_STORAGE_DIR` or `priv/storage`)."
  def storage_dir do
    Application.get_env(:api, :document_storage_dir) ||
      Path.join(:code.priv_dir(:api), "storage")
  end

  @doc """
  Assembles the full pipeline trace for a document — its OCR/translation stage runs, and its
  triage sections each with their extraction and sink result — for troubleshooting (ADR-0030).

  Returns `nil` if the id is not a valid UUID or no such document exists.
  """
  def get_document_pipeline_trace(id) do
    case get_document(id) do
      nil ->
        nil

      document ->
        stage_runs =
          from(p in PipelineStageRun, where: p.document_id == ^document.id, order_by: p.stage)
          |> Repo.all()

        sections =
          from(t in TriageSection,
            where: t.document_id == ^document.id,
            order_by: t.section_index
          )
          |> Repo.all()
          |> Repo.preload(extraction_result: :sink_result)

        %{document: document, pipeline_stage_runs: stage_runs, triage_sections: sections}
    end
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

  # -- Pipeline stage tracking (write path for `bem/`, design doc: ------------------------------
  # docs/elixir-backend-borehole-pipeline.md, "Proposed Extension: Pipeline Stage Tracking".
  # Debug/internal only, never consumed by `web/`. Latest run only: each `put_*`/`replace_*`
  # call below replaces the previous result for that document/stage/section rather than keeping
  # history. `attrs` is expected to be the string-keyed map straight from controller params.

  @doc """
  Upserts the OCR or translation result for a document. `stage` is `"ocr"` or `"translation"`.
  """
  def put_pipeline_stage_run(document_id, stage, attrs) do
    with {:ok, uuid} <- Ecto.UUID.cast(document_id),
         true <- Repo.exists?(from(d in Document, where: d.id == ^uuid)) do
      (Repo.get_by(PipelineStageRun, document_id: uuid, stage: stage) ||
         %PipelineStageRun{document_id: uuid, stage: stage})
      |> PipelineStageRun.changeset(attrs)
      |> Repo.insert_or_update()
    else
      _ -> {:error, :not_found}
    end
  end

  @doc """
  Replaces every triage section for a document with `sections_attrs` (each a map, "section_index"
  defaults to its 0-based position in the list). Deleting the old sections cascades to their
  `extraction_results`/`sink_results` automatically.
  """
  def replace_triage_sections(document_id, sections_attrs) do
    with {:ok, uuid} <- Ecto.UUID.cast(document_id),
         true <- Repo.exists?(from(d in Document, where: d.id == ^uuid)) do
      Repo.transaction(fn ->
        Repo.delete_all(from(t in TriageSection, where: t.document_id == ^uuid))

        sections_attrs
        |> Enum.with_index()
        |> Enum.reduce_while([], fn {attrs, index}, acc ->
          %TriageSection{document_id: uuid}
          |> TriageSection.changeset(Map.put_new(attrs, "section_index", index))
          |> Repo.insert()
          |> case do
            {:ok, section} -> {:cont, [section | acc]}
            {:error, changeset} -> {:halt, {:error, changeset}}
          end
        end)
        |> case do
          {:error, changeset} -> Repo.rollback(changeset)
          sections -> Enum.reverse(sections)
        end
      end)
    else
      _ -> {:error, :not_found}
    end
  end

  @doc """
  Upserts the extraction result for the triage section at `section_index` within a document.
  """
  def put_extraction_result(document_id, section_index, attrs) do
    with {:ok, uuid} <- Ecto.UUID.cast(document_id),
         %TriageSection{} = section <-
           Repo.get_by(TriageSection, document_id: uuid, section_index: section_index) do
      (Repo.get_by(ExtractionResult, triage_section_id: section.id) ||
         %ExtractionResult{triage_section_id: section.id})
      |> ExtractionResult.changeset(attrs)
      |> Repo.insert_or_update()
    else
      _ -> {:error, :not_found}
    end
  end

  @doc """
  Upserts the sink result for the extraction result of the triage section at `section_index`
  within a document. `attrs["created_borehole_id"]` links the sink attempt to the borehole it
  actually created, if any.
  """
  def put_sink_result(document_id, section_index, attrs) do
    with {:ok, uuid} <- Ecto.UUID.cast(document_id),
         %TriageSection{} = section <-
           Repo.get_by(TriageSection, document_id: uuid, section_index: section_index),
         %ExtractionResult{} = extraction <-
           Repo.get_by(ExtractionResult, triage_section_id: section.id) do
      (Repo.get_by(SinkResult, extraction_result_id: extraction.id) ||
         %SinkResult{extraction_result_id: extraction.id})
      |> SinkResult.changeset(attrs)
      |> Repo.insert_or_update()
    else
      _ -> {:error, :not_found}
    end
  end
end
