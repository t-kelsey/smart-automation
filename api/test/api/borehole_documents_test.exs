defmodule Api.BoreholeDocumentsTest do
  use Api.DataCase, async: true

  alias Api.Boreholes
  alias Api.Boreholes.{Borehole, Document}

  defp borehole(name), do: Repo.insert!(%Borehole{name: name})

  defp document(filename) do
    Repo.insert!(%Document{original_filename: filename, storage_path: "#{filename}"})
  end

  test "get_borehole lists the original document first, then additional ones by name" do
    borehole = borehole("BK 1")
    {original, a, b} = {document("z-original.pdf"), document("a.pdf"), document("b.pdf")}

    {:ok, _} = Boreholes.attach_documents(borehole, original, [b, a])

    assert [
             %{original_filename: "z-original.pdf", role: "original"},
             %{original_filename: "a.pdf", role: "additional"},
             %{original_filename: "b.pdf", role: "additional"}
           ] = Boreholes.get_borehole(borehole.id).documents
  end

  test "a borehole can have only one original document" do
    borehole = borehole("BK 2")
    {:ok, _} = Boreholes.attach_documents(borehole, document("one.pdf"))

    assert {:error, changeset} = Boreholes.attach_documents(borehole, document("two.pdf"))
    assert %{borehole_id: ["already has an original document"]} = errors_on(changeset)
  end

  test "a document can be the original of one borehole and additional for another" do
    shared = document("shared.pdf")
    first = borehole("BK 3")
    second = borehole("BK 4")

    {:ok, _} = Boreholes.attach_documents(first, shared)
    {:ok, _} = Boreholes.attach_documents(second, document("own.pdf"), [shared])

    assert [%{role: "original"}] = Boreholes.get_borehole(first.id).documents

    assert Enum.find(Boreholes.get_borehole(second.id).documents, &(&1.id == shared.id)).role ==
             "additional"
  end
end
