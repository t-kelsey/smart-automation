defmodule Api.Boreholes.DocumentTest do
  use Api.DataCase, async: true

  alias Api.Boreholes.Document

  @valid_attrs %{
    original_filename: "borehole_1.pdf",
    storage_path: "/uploads/borehole_1.pdf"
  }

  test "changeset with valid attributes is valid" do
    changeset = Document.changeset(%Document{}, @valid_attrs)
    assert changeset.valid?
  end

  test "changeset requires original_filename and storage_path" do
    changeset = Document.changeset(%Document{}, %{})

    refute changeset.valid?

    assert %{original_filename: ["can't be blank"], storage_path: ["can't be blank"]} =
             errors_on(changeset)
  end

  test "changeset defaults status to pending" do
    changeset = Document.changeset(%Document{}, @valid_attrs)
    assert get_field(changeset, :status) == "pending"
  end

  test "changeset rejects an invalid status" do
    changeset = Document.changeset(%Document{}, Map.put(@valid_attrs, :status, "bogus"))

    refute changeset.valid?
    assert %{status: ["is invalid"]} = errors_on(changeset)
  end

  test "changeset accepts all valid statuses" do
    for status <- ~w(pending processing extracted failed reviewed) do
      changeset = Document.changeset(%Document{}, Map.put(@valid_attrs, :status, status))
      assert changeset.valid?
    end
  end
end
