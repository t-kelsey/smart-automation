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
  alias Api.Boreholes.ExecStage
  alias Api.Boreholes.PipelineRun
  alias Api.Boreholes.Report
  alias Api.Boreholes.StageDocumentLink

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
    * `:additional_document_ids` - existing `documents.id`s to attach as `additional` documents
      (e.g. the split-out PDF the borehole was extracted from); duplicates and the original are
      ignored
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
    with {:ok, original} <- fetch_original(Keyword.get(opts, :document_id)),
         {:ok, additional} <-
           fetch_additional(Keyword.get(opts, :additional_document_ids), original),
         {:ok, _links} <- attach_documents(borehole, original, additional) do
      :ok
    end
  end

  defp fetch_original(nil), do: {:ok, nil}

  defp fetch_original(document_id) do
    case get_document(document_id) do
      nil -> {:error, "document_id does not reference an existing document"}
      document -> {:ok, document}
    end
  end

  defp fetch_additional(nil, _original), do: {:ok, []}

  defp fetch_additional(ids, original) when is_list(ids) do
    ids
    |> Enum.uniq()
    |> Enum.reduce_while({:ok, []}, fn id, {:ok, acc} ->
      case get_document(id) do
        nil ->
          {:halt,
           {:error,
            "additional_document_ids does not reference an existing document: #{inspect(id)}"}}

        %{id: id} when original != nil and id == original.id ->
          {:cont, {:ok, acc}}

        document ->
          {:cont, {:ok, [document | acc]}}
      end
    end)
    |> case do
      {:ok, documents} -> {:ok, Enum.reverse(documents)}
      error -> error
    end
  end

  defp fetch_additional(_ids, _original), do: {:error, "additional_document_ids must be a list"}

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

  # -- Pipeline stage tracking (write path for `claude_test/`, ADR-0034) --------------------------
  # Debug/internal only, never consumed by `web/`. Append-only: unlike the dropped bem tables
  # (ADR-0030), reruns add new rows instead of replacing previous ones.

  @doc """
  Records one pipeline step execution (`attrs` with `"type"`, `"run_id"`, `"position"` and
  optionally `"status"` (default `"new"`), `"data"`, `"error"`, `"model"`, `"effort"`, `"usage"`),
  linked to every document id in `attrs["document_ids"]` (at least one required). A stage created
  as `"running"` becomes its run's `current_stage`.
  """
  def create_exec_stage(attrs) do
    document_ids = attrs["document_ids"] || attrs[:document_ids] || []

    Repo.transaction(fn ->
      with :ok <- require_document_ids(document_ids),
           {:ok, exec_stage} <- %ExecStage{} |> ExecStage.changeset(attrs) |> Repo.insert(),
           {:ok, _links} <- link_documents(exec_stage, document_ids) do
        track_current_stage(exec_stage)
        Repo.preload(exec_stage, :documents)
      else
        {:error, reason} -> Repo.rollback(reason)
      end
    end)
  end

  @doc """
  Reports progress on a stage (ADR-0040): `attrs` with `"status"` (required) and optionally
  `"data"`, `"error"`, `"model"`, `"effort"`, `"usage"`, `"started_at"`, `"finished_at"`.
  `"document_ids"` (optional) are linked in addition to the stage's existing documents. A finished
  stage cannot change any more (422).
  """
  def update_exec_stage(%ExecStage{} = exec_stage, attrs) do
    document_ids = attrs["document_ids"] || attrs[:document_ids] || []
    exec_stage = Repo.preload(exec_stage, :documents)

    Repo.transaction(fn ->
      with :ok <- validate_id_list(document_ids, "document_ids"),
           {:ok, updated} <-
             exec_stage |> ExecStage.update_changeset(attrs) |> Repo.update(),
           {:ok, _links} <- link_documents(updated, unlinked(exec_stage, document_ids)) do
        track_current_stage(updated)
        updated |> Repo.preload(:documents, force: true)
      else
        {:error, reason} -> Repo.rollback(reason)
      end
    end)
  end

  defp unlinked(exec_stage, document_ids) do
    linked = MapSet.new(exec_stage.documents, & &1.id)
    document_ids |> Enum.uniq() |> Enum.reject(&MapSet.member?(linked, &1))
  end

  defp require_document_ids([_ | _] = ids), do: validate_id_list(ids, "document_ids")
  defp require_document_ids(_), do: {:error, "document_ids must have at least one entry"}

  defp validate_id_list(ids, name) do
    if is_list(ids) and Enum.all?(ids, &is_binary/1),
      do: :ok,
      else: {:error, "#{name} must be a list of document ids"}
  end

  # a stage that starts running becomes its pipeline run's current_stage (run_id is the run's id)
  defp track_current_stage(%ExecStage{status: "running", type: type, run_id: run_id}) do
    case Ecto.UUID.cast(run_id) do
      {:ok, uuid} ->
        from(pr in PipelineRun, where: pr.id == ^uuid and pr.status in ["new", "running"])
        |> Repo.update_all(set: [current_stage: type, updated_at: DateTime.utc_now(:second)])

      :error ->
        :ok
    end
  end

  defp track_current_stage(_exec_stage), do: :ok

  defp link_documents(_exec_stage, []), do: {:ok, []}

  defp link_documents(exec_stage, document_ids) do
    Enum.reduce_while(document_ids, {:ok, []}, fn document_id, {:ok, acc} ->
      case get_document(document_id) do
        nil ->
          {:halt,
           {:error, "document_ids does not reference an existing document: #{document_id}"}}

        document ->
          %StageDocumentLink{}
          |> StageDocumentLink.changeset(%{
            exec_stage_id: exec_stage.id,
            document_id: document.id
          })
          |> Repo.insert()
          |> case do
            {:ok, link} -> {:cont, {:ok, [link | acc]}}
            {:error, changeset} -> {:halt, {:error, changeset}}
          end
      end
    end)
  end

  @doc "One `exec_stage` with its documents, or `nil` if the id is not a valid UUID or unknown."
  def get_exec_stage(id) do
    case Ecto.UUID.cast(id) do
      {:ok, uuid} -> ExecStage |> Repo.get(uuid) |> Repo.preload(:documents)
      :error -> nil
    end
  end

  @doc """
  Every `exec_stage` linked to a document (via `stage_document_links`), newest first. Optional
  `filters["type"]`/`filters["run_id"]` narrow it down. `[]` if the id is not a valid UUID or no
  such document exists.
  """
  def list_document_exec_stages(document_id, filters \\ %{}) do
    case Ecto.UUID.cast(document_id) do
      {:ok, uuid} ->
        from(e in ExecStage,
          join: l in StageDocumentLink,
          on: l.exec_stage_id == e.id,
          where: l.document_id == ^uuid,
          distinct: true,
          order_by: [desc: e.inserted_at]
        )
        |> filter_exec_stages(filters)
        |> Repo.all()
        |> Repo.preload(:documents)

      :error ->
        []
    end
  end

  defp filter_exec_stages(query, filters) do
    query
    |> maybe_filter(:type, filters["type"] || filters[:type])
    |> maybe_filter(:run_id, filters["run_id"] || filters[:run_id])
  end

  defp maybe_filter(query, _field, nil), do: query
  defp maybe_filter(query, :type, type), do: where(query, [e], e.type == ^type)
  defp maybe_filter(query, :run_id, run_id), do: where(query, [e], e.run_id == ^run_id)

  @doc """
  Records one pipeline run's report (`attrs` with `"document_id"`, `"run_id"`, `"data"`).
  `"document_id"` must reference an existing document.
  """
  def create_report(attrs) do
    document_id = attrs["document_id"] || attrs[:document_id]

    case get_document(document_id) do
      nil -> {:error, "document_id does not reference an existing document"}
      _document -> %Report{} |> Report.changeset(attrs) |> Repo.insert()
    end
  end

  # -- Pipeline runs (ADR-0035) --------------------------------------------------------------

  @doc """
  Creates a pipeline run (`attrs` with `"document_id"`, optional `"config"`), status `"new"`.
  `"document_id"` must reference an existing document.
  """
  def create_pipeline_run(attrs) do
    document_id = attrs["document_id"] || attrs[:document_id]

    case get_document(document_id) do
      nil -> {:error, "document_id does not reference an existing document"}
      _document -> %PipelineRun{} |> PipelineRun.changeset(attrs) |> Repo.insert()
    end
  end

  @doc """
  Fetches a pipeline run by id; `nil` if the id is not a valid UUID or no such run exists.
  """
  def get_pipeline_run(id) do
    case Ecto.UUID.cast(id) do
      {:ok, uuid} -> Repo.get(PipelineRun, uuid)
      :error -> nil
    end
  end

  @doc """
  Lists pipeline runs for the overview page (`filters["status"]`/`filters["document_id"]` exact
  match, `filters[:limit]`/`filters[:offset]` paging), newest first. Preloads `:document` so the
  caller can read `original_filename` without a per-row round-trip.
  """
  @spec list_pipeline_runs(map()) :: %{entries: [PipelineRun.t()], total: non_neg_integer()}
  def list_pipeline_runs(filters \\ %{}) do
    query = filtered_pipeline_runs_query(filters)

    total = Repo.aggregate(query, :count, :id)

    entries =
      query
      |> order_by([pr], desc: pr.inserted_at, asc: pr.id)
      |> page(filters)
      |> Repo.all()
      |> Repo.preload(:document)

    %{entries: entries, total: total}
  end

  defp filtered_pipeline_runs_query(filters) do
    from(pr in PipelineRun)
    |> maybe_filter_pipeline_run(:status, filters["status"] || filters[:status])
    |> maybe_filter_pipeline_run(:document_id, filters["document_id"] || filters[:document_id])
  end

  defp maybe_filter_pipeline_run(query, _field, nil), do: query

  defp maybe_filter_pipeline_run(query, :status, status),
    do: where(query, [pr], pr.status == ^status)

  defp maybe_filter_pipeline_run(query, :document_id, document_id),
    do: where(query, [pr], pr.document_id == ^document_id)

  @doc """
  Sets the status of a pipeline run, optionally with an `"error"` (and `"current_stage"`) in
  `attrs`. Once a run has finished (`completed`/`failed`/`stopped`) its status cannot change any
  more: `{:error, {:conflict, message}}`, unless it is set to the same status again. Finishing a
  run marks its stages that are still `new`/`running` as `stopped` (ADR-0040).
  """
  def update_pipeline_run_status(%PipelineRun{} = pipeline_run, status, attrs \\ %{}) do
    terminal = PipelineRun.terminal_statuses()

    cond do
      pipeline_run.status in terminal and pipeline_run.status == status ->
        {:ok, pipeline_run}

      pipeline_run.status in terminal ->
        {:error,
         {:conflict, "pipeline run is already #{pipeline_run.status} and cannot become #{status}"}}

      true ->
        attrs =
          attrs
          |> Map.new(fn {k, v} -> {to_string(k), v} end)
          |> Map.take(["error", "current_stage"])
          |> Map.put("status", status)

        Repo.transaction(fn ->
          case pipeline_run |> PipelineRun.changeset(attrs) |> Repo.update() do
            {:ok, %PipelineRun{status: s} = updated} ->
              if s in terminal, do: stop_open_stages(updated)
              updated

            {:error, changeset} ->
              Repo.rollback(changeset)
          end
        end)
    end
  end

  @doc """
  Stops a pipeline run that is still `new`/`running`: sets it to `stopped` (its open stages too)
  and asks the pipeline to cancel it (`Api.Pipeline.stop_pipeline_run/1`, best effort).
  `{:error, {:conflict, message}}` if the run has already finished.
  """
  def stop_pipeline_run(%PipelineRun{} = pipeline_run) do
    with {:ok, stopped} <-
           update_pipeline_run_status(pipeline_run, "stopped", %{"error" => "stopped by user"}) do
      if pipeline_run.status == "running", do: Api.Pipeline.stop_pipeline_run(stopped)
      {:ok, stopped}
    end
  end

  @doc """
  Deletes a pipeline run together with its `exec_stages` and `reports` (matched by `run_id`), e.g.
  when it is stuck. A run that is still `new`/`running` is asked to cancel first (best effort).
  Boreholes already created by the run are kept.
  """
  def delete_pipeline_run(%PipelineRun{} = pipeline_run) do
    if pipeline_run.status == "running", do: Api.Pipeline.stop_pipeline_run(pipeline_run)

    Repo.transaction(fn ->
      from(e in ExecStage, where: e.run_id == ^pipeline_run.id) |> Repo.delete_all()
      from(r in Report, where: r.run_id == ^pipeline_run.id) |> Repo.delete_all()
      Repo.delete!(pipeline_run)
    end)
  end

  # stages that never finished end with their run
  defp stop_open_stages(%PipelineRun{id: id}) do
    now = DateTime.utc_now()

    from(e in ExecStage, where: e.run_id == ^id and e.status in ["new", "running"])
    |> Repo.update_all(
      set: [status: "stopped", finished_at: now, updated_at: DateTime.truncate(now, :second)]
    )
  end

  @doc """
  The most recently recorded `Api.Boreholes.Report` for a pipeline run (matched by `run_id`), or
  `nil` if the pipeline hasn't reported one yet.
  """
  def get_report(run_id) do
    Report
    |> where(run_id: ^run_id)
    |> order_by(desc: :inserted_at)
    |> limit(1)
    |> Repo.one()
  end

  @doc "The directory holding the stored document files (`DOCUMENT_STORAGE_DIR` or `priv/storage`)."
  def storage_dir do
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
