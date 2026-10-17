defmodule Api.MockDataTest do
  use Api.DataCase, async: false

  alias Api.Boreholes
  alias Api.Boreholes.Document
  alias Api.Boreholes.BoreholeLayer
  alias Api.MockData

  @standard "../standards/din-4023/din-4023.json"
            |> Path.expand(File.cwd!())
            |> File.read!()
            |> Jason.decode!()

  # Colour names and the words of the designations (Table 1 main/minor forms, hatch sheet) of the
  # shared standard file; "schwach"/"stark" are the DIN proportion words.
  defp standard_colors, do: Enum.map(@standard["farben"], & &1["name"])

  defp standard_words do
    names =
      Enum.flat_map(@standard["tabelle_1"]["bodenarten"], fn b ->
        [b["benennung"]["hauptanteil"], b["benennung"]["nebenanteil"]]
      end) ++ Enum.map(@standard["schraffuren"], & &1["bezeichnung"])

    (["schwach", "stark"] ++ Enum.flat_map(Enum.reject(names, &is_nil/1), &words/1))
    |> MapSet.new()
  end

  defp words(text), do: text |> String.downcase() |> String.split(~r/[^\p{L}]+/u, trim: true)

  defp assert_standard_layers(layers) do
    allowed = standard_words()
    assert layers != []

    for %{petrography: petrography, color: color} <- layers, not is_nil(petrography) do
      assert color in standard_colors(), "colour #{inspect(color)} is not in the DIN 4023 colours"

      for word <- words(petrography) do
        assert word in allowed, "#{inspect(word)} in #{inspect(petrography)} is not DIN 4023"
      end
    end
  end

  test "generated layers only use the DIN 4023 vocabulary, in every country" do
    MockData.generate(300, seed: 3)
    layers = Repo.all(BoreholeLayer)
    assert_standard_layers(layers)
  end

  test "seeded layers only use the DIN 4023 vocabulary" do
    System.put_env("MOCK_BOREHOLES", "0")
    ExUnit.CaptureIO.capture_io(fn -> Code.eval_file("priv/repo/seeds.exs") end)
    assert_standard_layers(Repo.all(BoreholeLayer))
  end

  test "every mock document points at the one stored example file" do
    assert %{documents: documents} = MockData.generate(5, seed: 1)
    assert documents > 0

    docs = Repo.all(Document)
    assert length(docs) == documents
    assert docs |> Enum.map(& &1.storage_path) |> Enum.uniq() |> length() == 1
    assert docs |> Enum.map(& &1.original_filename) |> Enum.uniq() |> length() > 1

    for doc <- docs do
      assert doc.mime_type == "application/pdf"
      assert doc |> Boreholes.document_file_path() |> File.regular?()
    end
  end

  test "without boreholes nothing is installed or inserted" do
    File.rm(Path.join(Boreholes.storage_dir(), "mock_borehole_log_example.pdf"))
    assert %{boreholes: 0, documents: 0} = MockData.generate(0)
    refute File.exists?(Path.join(Boreholes.storage_dir(), "mock_borehole_log_example.pdf"))
  end
end
