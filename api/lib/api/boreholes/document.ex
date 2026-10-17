defmodule Api.Boreholes.Document do
  use Ecto.Schema
  import Ecto.Changeset

  @statuses ~w(pending processing extracted failed reviewed)

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "documents" do
    field :original_filename, :string
    field :storage_path, :string
    field :mime_type, :string
    field :source_country, :string
    field :status, :string, default: "pending"
    field :page_count, :integer
    field :size_bytes, :integer
    field :raw_extraction, :map

    many_to_many :boreholes, Api.Boreholes.Borehole, join_through: Api.Boreholes.BoreholeDocument

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(document, attrs) do
    document
    |> cast(attrs, [
      :original_filename,
      :storage_path,
      :mime_type,
      :source_country,
      :status,
      :page_count,
      :size_bytes,
      :raw_extraction
    ])
    |> validate_required([:original_filename, :storage_path])
    |> validate_inclusion(:status, @statuses)
    |> validate_number(:page_count, greater_than: 0)
    |> validate_number(:size_bytes, greater_than_or_equal_to: 0)
  end
end
