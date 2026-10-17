defmodule Api.MockData do
  @moduledoc """
  Generates realistic-looking but invented boreholes with layers and documents for development
  and demos (`mix boreholes.mock`, also used by `priv/repo/seeds.exs`).

  The output is deterministic for a given seed. Generated rows are marked with
  `metadata.source = "mock"` on boreholes, so they can be removed again without touching real
  data. Every mock document, however it is named, points at the same example log
  (`priv/repo/assets/borehole_log_example.pdf`), which `install_example_file/0` copies into the
  document storage directory whenever mock data is created.

  Like the real logs, the `raw_text` of a layer is in the local language of each region (German,
  English, French, Spanish, Portuguese), as are the stratigraphy names. The standardised fields
  (`petrography`, `color`) only use the DIN 4023 vocabulary of `standards/din-4023/din-4023.json`,
  for every country.
  """

  import Ecto.Query

  alias Api.Boreholes
  alias Api.Boreholes.{Borehole, BoreholeDocument, BoreholeLayer, Document}
  alias Api.Repo

  # The one file behind every mock document, and the name it is stored under.
  @example_asset "repo/assets/borehole_log_example.pdf"
  @example_storage_name "mock_borehole_log_example.pdf"

  @max_count 1_000_000

  # The hackathon takes place near Offenburg, so every non-empty data set contains a few
  # boreholes there: {place, lat, lon, elevation_m}.
  @local_spots [
    {"Offenburg", 48.4733, 7.9441, 164},
    {"Offenburg", 48.4651, 7.9298, 160},
    {"Gengenbach", 48.4059, 8.0164, 160}
  ]
  @chunk 1_000

  # -- Vocabulary -------------------------------------------------------------------------------

  @regions [
    %{
      country: "Germany",
      lang: :de,
      crs: "32U UTM",
      places: [
        {"Stuttgart", 48.7758, 9.1770, 245},
        {"Karlsruhe", 49.0069, 8.4037, 115},
        {"Freiburg im Breisgau", 47.9990, 7.8421, 278},
        {"München", 48.1351, 11.5820, 519},
        {"Frankfurt am Main", 50.1109, 8.6821, 112},
        {"Hamburg", 53.5511, 9.9937, 6}
      ]
    },
    %{
      country: "Switzerland",
      lang: :de,
      crs: "CH1903+ / LV95",
      places: [
        {"Zürich", 47.3769, 8.5417, 408},
        {"Basel", 47.5596, 7.5886, 260},
        {"Bern", 46.9480, 7.4474, 540}
      ]
    },
    %{
      country: "Austria",
      lang: :de,
      crs: "MGI / Austria GK",
      places: [{"Wien", 48.2082, 16.3738, 190}, {"Innsbruck", 47.2692, 11.4041, 574}]
    },
    %{
      country: "France",
      lang: :fr,
      crs: "Lambert 93",
      places: [
        {"Paris", 48.8566, 2.3522, 35},
        {"Lyon", 45.7640, 4.8357, 173},
        {"Marseille", 43.2965, 5.3698, 12},
        {"Lille", 50.6292, 3.0573, 20}
      ]
    },
    %{
      country: "Spain",
      lang: :es,
      crs: "ETRS89 / UTM 30N",
      places: [
        {"Madrid", 40.4168, -3.7038, 650},
        {"Barcelona", 41.3874, 2.1686, 12},
        {"Sevilla", 37.3891, -5.9845, 7},
        {"Bilbao", 43.2630, -2.9350, 19}
      ]
    },
    %{
      country: "Brazil",
      lang: :pt,
      crs: "SIRGAS 2000 / UTM 23S",
      places: [
        {"São Paulo", -23.5505, -46.6333, 760},
        {"Rio de Janeiro", -22.9068, -43.1729, 5},
        {"Belo Horizonte", -19.9167, -43.9345, 852}
      ]
    },
    %{
      country: "United Kingdom",
      lang: :en,
      crs: "OSGB36 / British National Grid",
      places: [
        {"London", 51.5072, -0.1276, 11},
        {"Manchester", 53.4808, -2.2426, 38},
        {"Birmingham", 52.4862, -1.8904, 140}
      ]
    },
    %{
      country: "United States",
      lang: :en,
      crs: "NAD83 / UTM 15N",
      places: [
        {"Houston", 29.7604, -95.3698, 15},
        {"Seattle", 47.6062, -122.3321, 50},
        {"New York", 40.7128, -74.0060, 10}
      ]
    },
    %{
      country: "Australia",
      lang: :en,
      crs: "GDA2020 / MGA 55",
      places: [{"Melbourne", -37.8136, 144.9631, 31}, {"Sydney", -33.8688, 151.2093, 58}]
    },
    %{
      country: "Singapore",
      lang: :en,
      crs: "SVY21",
      places: [{"Singapore", 1.3521, 103.8198, 15}]
    },
    %{
      country: "United Arab Emirates",
      lang: :en,
      crs: "WGS 84 / UTM 40N",
      places: [{"Dubai", 25.2048, 55.2708, 5}]
    }
  ]

  # Per lithology: the designation in the DIN 4023 vocabulary (`standard`, German, the same for every
  # country, see standards/din-4023/din-4023.json), plausible colours, whether it is rock, and the
  # description as a local log would word it (`text`, only used for `raw_text`).
  @lithologies %{
    topsoil: %{
      rock: false,
      colors: [:dark_brown],
      standard: ["Mutterboden", "Mutterboden, schwach tonig, humos"],
      text: %{
        de: ["Mutterboden, humos", "Oberboden, schwach tonig, humos"],
        en: ["Topsoil, humous"],
        fr: ["Terre végétale"],
        es: ["Tierra vegetal"],
        pt: ["Solo orgânico"]
      }
    },
    fill: %{
      rock: false,
      colors: [:grey, :brown],
      standard: ["Auffüllung, Kies, sandig", "Auffüllung, Sand, kiesig"],
      text: %{
        de: ["Auffüllung, Kies, sandig, mit Ziegelresten", "Auffüllung, Sand, kiesig"],
        en: ["Made ground, gravelly sand with brick fragments"],
        fr: ["Remblai sablo-graveleux"],
        es: ["Relleno antrópico, arena con gravas"],
        pt: ["Aterro, areia com cascalho"]
      }
    },
    gravel: %{
      rock: false,
      colors: [:grey, :brown, :yellow],
      standard: [
        "Kies, steinig, schwach grobsandig",
        "Kies, sandig, schwach schluffig",
        "Kies, stark sandig"
      ],
      text: %{
        de: [
          "Kies [gerundet] (steinig, schwach grobsandig)",
          "Kies, sandig, schwach schluffig",
          "Kies, stark sandig"
        ],
        en: ["Sandy gravel, medium dense", "Gravel, rounded, slightly silty"],
        fr: ["Grave sableuse", "Graves et galets"],
        es: ["Grava arenosa", "Gravas con cantos rodados"],
        pt: ["Cascalho arenoso"]
      }
    },
    sand: %{
      rock: false,
      colors: [:yellow, :beige, :brown],
      standard: ["Mittelsand, schwach kiesig", "Feinsand, schluffig", "Sand, schwach kiesig"],
      text: %{
        de: ["Sand, mittelsandig, schwach kiesig", "Feinsand, schluffig"],
        en: ["Fine to medium sand, loose", "Silty sand, medium dense"],
        fr: ["Sable fin limoneux", "Sable moyen"],
        es: ["Arena fina limosa", "Arena media"],
        pt: ["Areia fina siltosa", "Areia média"]
      }
    },
    silt: %{
      rock: false,
      colors: [:olive, :grey, :beige],
      standard: ["Schluff, tonig", "Schluff, schwach feinsandig"],
      text: %{
        de: ["Schluff, tonig, steif", "Schluff, schwach feinsandig"],
        en: ["Clayey silt, soft to firm"],
        fr: ["Limon argileux"],
        es: ["Limo arcilloso"],
        pt: ["Silte argiloso"]
      }
    },
    clay: %{
      rock: false,
      colors: [:grey, :brown, :olive],
      standard: ["Ton, schluffig", "Ton, schwach sandig"],
      text: %{
        de: ["Ton, schluffig, steif bis halbfest", "Ton, schwach sandig"],
        en: ["Stiff clay, high plasticity", "Silty clay, soft"],
        fr: ["Argile plastique", "Argile limoneuse"],
        es: ["Arcilla plástica", "Arcilla limosa"],
        pt: ["Argila plástica"]
      }
    },
    sandstone: %{
      rock: true,
      colors: [:beige, :red_brown, :yellow],
      standard: ["Sandstein"],
      text: %{
        de: ["Sandstein, feinkörnig, mürbe", "Sandstein, mittelkörnig, fest"],
        en: ["Sandstone, fine grained, moderately weathered"],
        fr: ["Grès fin"],
        es: ["Arenisca de grano fino"],
        pt: ["Arenito fino"]
      }
    },
    claystone: %{
      rock: true,
      colors: [:dark_grey, :grey, :red_brown],
      standard: ["Tonstein"],
      text: %{
        de: ["Tonstein, geschichtet, angewittert", "Tonstein, klüftig"],
        en: ["Mudstone, laminated", "Claystone, fissured"],
        fr: ["Argilite feuilletée"],
        es: ["Argilita laminada"],
        pt: ["Argilito laminado"]
      }
    },
    limestone: %{
      rock: true,
      colors: [:light_grey, :beige],
      standard: ["Kalkstein"],
      text: %{
        de: ["Kalkstein, fest, klüftig", "Kalkstein, verkarstet"],
        en: ["Limestone, strong, jointed", "Chalk, weak, with flints"],
        fr: ["Calcaire grossier", "Calcaire marneux"],
        es: ["Caliza fracturada"],
        pt: ["Calcário fraturado"]
      }
    },
    marl: %{
      rock: true,
      colors: [:red_brown, :grey, :olive],
      standard: ["Mergelstein"],
      text: %{
        de: ["Mergelstein, verwittert, mit Gipsknollen", "Mergel, tonig"],
        en: ["Marl, weathered"],
        fr: ["Marnes vertes", "Marne argileuse"],
        es: ["Marga gris"],
        pt: ["Marga cinza"]
      }
    }
  }

  @colors %{
    de: %{
      grey: "grau",
      dark_grey: "dunkelgrau",
      light_grey: "hellgrau",
      brown: "braun",
      dark_brown: "dunkelbraun",
      red_brown: "rotbraun",
      yellow: "gelb",
      beige: "beige",
      olive: "oliv"
    },
    en: %{
      grey: "grey",
      dark_grey: "dark grey",
      light_grey: "light grey",
      brown: "brown",
      dark_brown: "dark brown",
      red_brown: "reddish brown",
      yellow: "yellow",
      beige: "beige",
      olive: "olive"
    },
    fr: %{
      grey: "gris",
      dark_grey: "gris foncé",
      light_grey: "gris clair",
      brown: "brun",
      dark_brown: "brun foncé",
      red_brown: "brun rouge",
      yellow: "jaune",
      beige: "beige",
      olive: "olive"
    },
    es: %{
      grey: "gris",
      dark_grey: "gris oscuro",
      light_grey: "gris claro",
      brown: "marrón",
      dark_brown: "marrón oscuro",
      red_brown: "pardo rojizo",
      yellow: "amarillo",
      beige: "beige",
      olive: "oliva"
    },
    pt: %{
      grey: "cinza",
      dark_grey: "cinza escuro",
      light_grey: "cinza claro",
      brown: "marrom",
      dark_brown: "marrom escuro",
      red_brown: "marrom avermelhado",
      yellow: "amarelo",
      beige: "bege",
      olive: "oliva"
    }
  }

  # `layer.color` only holds colour names of the DIN 4023 standard file (`farben`); the local
  # colour words above only appear in `raw_text`.
  @standard_colors %{
    grey: "grau",
    dark_grey: "grau",
    light_grey: "grau",
    brown: "gelblichbraun",
    dark_brown: "dunkelbraun",
    red_brown: "rot",
    yellow: "gelb",
    beige: "gelb",
    olive: "oliv"
  }

  # Young (soil) and old (rock) units, as they would appear on local logs.
  @stratigraphy %{
    de: %{
      soft: ["qh Holozän", "qp Pleistozän", "Neuenburg-Formation", "qw Würm-Schotter"],
      rock: [
        "km1 Gipskeuper",
        "ku Lettenkeuper",
        "mo Oberer Muschelkalk",
        "jo Oberjura",
        "tOM Obere Meeresmolasse"
      ]
    },
    en: %{
      soft: ["Alluvium", "Glacial Till", "River Terrace Deposits", "Made Ground"],
      rock: ["London Clay Formation", "Chalk Group", "Mercia Mudstone Group", "Coal Measures"]
    },
    fr: %{
      soft: ["Alluvions modernes", "Limons des plateaux", "Alluvions anciennes"],
      rock: ["Calcaire grossier (Lutétien)", "Marnes et caillasses", "Craie blanche"]
    },
    es: %{
      soft: ["Aluvial cuaternario", "Terraza fluvial"],
      rock: ["Margas terciarias", "Facies Madrid", "Yesos miocenos"]
    },
    pt: %{
      soft: ["Aluvião", "Coluvião"],
      rock: ["Formação Resende", "Grupo Bauru", "Embasamento gnáissico"]
    }
  }

  @names %{
    de: ["B", "BK", "KB", "RKS"],
    en: ["BH", "WS", "CP"],
    fr: ["SC", "SP", "F"],
    es: ["S", "SR"],
    pt: ["SP", "SM"]
  }

  @purposes %{
    de: [
      "Baugrunderkundung",
      "Hydrogeologische Untersuchung",
      "Erkundung für Tunneltrasse",
      "Grundwassermessstelle"
    ],
    en: [
      "Site investigation",
      "Tunnel alignment investigation",
      "Groundwater monitoring well",
      "Foundation design"
    ],
    fr: ["Reconnaissance géotechnique", "Étude de tracé de tunnel", "Piézomètre"],
    es: ["Estudio geotécnico", "Investigación para túnel", "Piezómetro"],
    pt: ["Sondagem geotécnica", "Investigação para túnel", "Poço de monitoramento"]
  }

  @methods %{
    de: ["Kernbohrung", "Rammkernsondierung", "Spülbohrung", "Bohrung mit Ausbau"],
    en: ["Rotary core drilling", "Cable percussion", "Hollow stem auger"],
    fr: ["Carottage rotatif", "Tarière", "Destructif"],
    es: ["Perforación a rotación con testigo", "Barrena helicoidal"],
    pt: ["Sondagem rotativa", "Sondagem a percussão (SPT)"]
  }

  @clients %{
    de: ["Stadtwerke", "Landesamt für Straßenbau", "Deutsche Bahn Netz AG", "Tiefbauamt"],
    en: ["Transport Authority", "City Council", "Water Corporation", "Highways Agency"],
    fr: ["Société du Grand Paris", "SNCF Réseau", "Métropole"],
    es: ["Ayuntamiento", "ADIF", "Canal de Isabel II"],
    pt: ["Prefeitura Municipal", "Metrô", "DNIT"]
  }

  @doc_kinds ["Schichtenverzeichnis", "Bohrprofil", "Kernfoto", "Bohrbericht"]

  @statuses ~w(pending processing extracted failed reviewed)

  # -- Public API -------------------------------------------------------------------------------

  @doc "Upper limit for `generate/2`; generation builds all rows in memory first, so very large counts need a lot of RAM."
  def max_count, do: @max_count

  @doc """
  Copies the example log into the document storage directory (see `Api.Boreholes.storage_dir/0`)
  and returns its `storage_path`, size and page count. Called whenever mock data is created.
  """
  def install_example_file do
    source = Path.join(:code.priv_dir(:api), @example_asset)
    target = Path.join(Boreholes.storage_dir(), @example_storage_name)

    File.mkdir_p!(Path.dirname(target))
    File.cp!(source, target)

    pdf = File.read!(source)

    %{
      storage_path: @example_storage_name,
      size_bytes: byte_size(pdf),
      # Counts page objects (not the `/Pages` tree); good enough for the example file.
      page_count: max(1, length(Regex.scan(~r{/Type\s*/Page[^s]}, pdf)))
    }
  end

  @doc """
  Inserts `count` mock boreholes (capped at #{@max_count}) with layers and documents.
  The first three are located near Offenburg
  (Baden-Württemberg). Options: `:seed` (default 42). Returns `%{boreholes:, layers:, documents:}` counts.
  """
  def generate(count, opts \\ []) do
    count = count |> max(0) |> min(@max_count)
    seed = Keyword.get(opts, :seed, 42)
    :rand.seed(:exsss, {seed, seed * 7 + 1, seed * 13 + 2})
    now = DateTime.utc_now() |> DateTime.truncate(:second)
    example = if count > 0, do: install_example_file()

    germany = Enum.find(@regions, &(&1.country == "Germany"))
    local = Enum.take(@local_spots, count)

    records =
      Enum.map(1..count//1, fn index ->
        case Enum.at(local, index - 1) do
          nil -> build_borehole(index, now, example)
          spot -> build_borehole(index, now, example, germany, spot, 0.02)
        end
      end)

    Repo.transaction(
      fn ->
        insert_chunked(Borehole, Enum.map(records, & &1.borehole))
        insert_chunked(BoreholeLayer, Enum.flat_map(records, & &1.layers))
        insert_chunked(Document, Enum.flat_map(records, & &1.documents))
        insert_chunked(BoreholeDocument, Enum.flat_map(records, & &1.links))
      end,
      timeout: :infinity
    )

    %{
      boreholes: count,
      layers: Enum.sum_by(records, &length(&1.layers)),
      documents: Enum.sum_by(records, &length(&1.documents))
    }
  end

  @doc """
  Deletes boreholes whose `metadata.source` equals `source` ("mock" or "seed"), their layers,
  and documents that are linked only to such boreholes. Returns the number of boreholes deleted.
  """
  def delete_source(source) do
    ids =
      from(b in Borehole, where: fragment("?->>'source' = ?", b.metadata, ^source), select: b.id)

    Repo.transaction(fn ->
      document_ids =
        from(bd in BoreholeDocument,
          where: bd.borehole_id in subquery(ids),
          select: bd.document_id
        )
        |> Repo.all()

      {deleted, _} = Repo.delete_all(from(b in Borehole, where: b.id in subquery(ids)))

      # Documents still linked to other boreholes (or real ones) are kept.
      from(d in Document,
        where: d.id in ^document_ids,
        where: d.id not in subquery(from(bd in BoreholeDocument, select: bd.document_id))
      )
      |> Repo.delete_all()

      deleted
    end)
    |> elem(1)
  end

  # -- Generation -------------------------------------------------------------------------------

  defp build_borehole(index, now, example) do
    region = pick(@regions)
    build_borehole(index, now, example, region, pick(region.places), 0.25)
  end

  defp build_borehole(index, now, example, region, {place, lat, lon, elevation}, spread) do
    lang = region.lang
    id = Ecto.UUID.generate()
    total_depth = round1(uniform(5.0, 80.0))
    drilled_at = Date.add(~D[1950-01-01], :rand.uniform(27_000))
    name = "#{pick(@names[lang])} #{100 + index}/#{rem(drilled_at.year, 100) |> pad2()} #{place}"
    layers = build_layers(id, lang, total_depth, now)

    borehole = %{
      id: id,
      name: name,
      external_id: "#{region.country |> String.slice(0, 2) |> String.upcase()}-#{10_000 + index}",
      purpose: pick(@purposes[lang]),
      place: place,
      client: pick(@clients[lang]),
      drilling_method: pick(@methods[lang]),
      drilled_at: drilled_at,
      end_date: if(:rand.uniform() < 0.7, do: Date.add(drilled_at, :rand.uniform(14) - 1)),
      location: %Geo.Point{
        coordinates:
          {round5(lon + uniform(-spread, spread)), round5(lat + uniform(-spread, spread))},
        srid: 4326
      },
      source_coordinate_system: region.crs,
      source_coordinate_raw: nil,
      total_depth_m: decimal(total_depth),
      borehole_length_m: nil,
      elevation_m: decimal(max(0.0, elevation + uniform(-30.0, 30.0) * spread * 4), 2),
      groundwater_level_m:
        if(:rand.uniform() < 0.6, do: decimal(uniform(0.5, total_depth * 0.7))),
      verified: :rand.uniform() < 0.4,
      metadata: %{"source" => "mock"},
      inserted_at: now,
      updated_at: now
    }

    documents = build_documents(name, region.country, example, now)

    %{
      borehole: borehole,
      layers: layers,
      documents: documents,
      links:
        documents
        |> Enum.with_index()
        |> Enum.map(fn {doc, index} ->
          %{
            id: Ecto.UUID.generate(),
            borehole_id: id,
            document_id: doc.id,
            # The first document is the borehole's original, any others are additional (ADR-0028).
            role: if(index == 0, do: "original", else: "additional"),
            inserted_at: now,
            updated_at: now
          }
        end)
    }
  end

  # Contiguous layers from 0 m to the total depth; soils on top, rock below.
  defp build_layers(borehole_id, lang, total_depth, now) do
    count = 3 + :rand.uniform(8)

    cuts =
      Stream.repeatedly(fn -> round1(uniform(0.3, total_depth - 0.3)) end)
      |> Stream.uniq()
      |> Enum.take(count - 1)
      |> Enum.sort()

    bounds = [0.0 | cuts] ++ [total_depth]
    soft_count = max(1, div(count, 2))

    soft =
      Enum.filter(@lithologies, fn {_k, l} -> not l.rock end)
      |> Enum.map(&elem(&1, 0))
      |> List.delete(:topsoil)

    rock = Enum.filter(@lithologies, fn {_k, l} -> l.rock end) |> Enum.map(&elem(&1, 0))

    bounds
    |> Enum.chunk_every(2, 1, :discard)
    |> Enum.with_index(1)
    |> Enum.map(fn {[from, to], position} ->
      key =
        cond do
          position == 1 -> :topsoil
          position <= soft_count -> pick(soft)
          true -> pick(rock)
        end

      lithology = @lithologies[key]
      color_key = pick(lithology.colors)
      petrography = pick(lithology.standard)
      color = @standard_colors[color_key]
      raw_petrography = pick(lithology.text[lang])
      raw_color = @colors[lang][color_key]
      stratigraphy = pick(@stratigraphy[lang][if(lithology.rock, do: :rock, else: :soft)])

      %{
        id: Ecto.UUID.generate(),
        borehole_id: borehole_id,
        position: position,
        depth_from_m: decimal(from),
        depth_to_m: decimal(to),
        stratigraphy: stratigraphy,
        petrography: petrography,
        color: color,
        raw_text:
          "#{format_depth(from, lang)}-#{format_depth(to, lang)} #{raw_petrography}, #{raw_color}",
        metadata: %{},
        inserted_at: now,
        updated_at: now
      }
    end)
  end

  defp build_documents(name, country, example, now) do
    stem = name |> String.replace(~r/[^\w]+/u, "_") |> String.trim("_")

    @doc_kinds
    |> Enum.take_random(:rand.uniform(2))
    |> Enum.map(fn kind ->
      %{
        id: Ecto.UUID.generate(),
        original_filename: "#{stem}_#{kind}.pdf",
        storage_path: example.storage_path,
        mime_type: "application/pdf",
        source_country: country,
        status: pick(@statuses),
        page_count: example.page_count,
        size_bytes: example.size_bytes,
        raw_extraction: nil,
        inserted_at: now,
        updated_at: now
      }
    end)
  end

  defp insert_chunked(schema, rows) do
    rows
    |> Enum.chunk_every(@chunk)
    |> Enum.each(&Repo.insert_all(schema, &1))
  end

  # -- Helpers ----------------------------------------------------------------------------------

  defp pick(list), do: Enum.at(list, :rand.uniform(length(list)) - 1)
  defp uniform(min, max), do: min + :rand.uniform() * (max - min)
  defp round1(x), do: Float.round(x, 1)
  defp round5(x), do: Float.round(x, 5)
  defp decimal(x, places \\ 1), do: x |> Float.round(places) |> Decimal.from_float()
  defp pad2(n), do: n |> Integer.to_string() |> String.pad_leading(2, "0")

  # German and French logs write decimal commas.
  defp format_depth(x, lang) when lang in [:de, :fr, :es, :pt],
    do: x |> :erlang.float_to_binary(decimals: 1) |> String.replace(".", ",")

  defp format_depth(x, _lang), do: :erlang.float_to_binary(x, decimals: 1)
end
