# Script for populating the database. You can run it as:
#
#     mix run priv/repo/seeds.exs
#
# Inside the script, you can read and write to any of your
# repositories directly:
#
#     Api.Repo.insert!(%Api.SomeSchema{})
#
# We recommend using the bang functions (`insert!`, `update!`
# and so on) as they will fail if something goes wrong.

alias Api.Boreholes.Borehole
alias Api.Boreholes.BoreholeLayer
alias Api.Boreholes.Document
alias Api.Repo

# Reuse real filenames already sitting in priv/storage/ (from `mix documents.backfill`) where
# available, so seeded documents point at something that actually exists on disk. Falls back to a
# made-up filename if priv/storage/ is empty (e.g. a fresh clone with no sample data loaded yet) —
# fine for seeding, nothing reads the file from disk during this script.
storage_files =
  Path.join(:code.priv_dir(:api), "storage/*")
  |> Path.wildcard()
  |> Enum.map(&Path.basename/1)
  |> Enum.reject(&(&1 in [".gitkeep", ".DS_Store"]))

storage_file = fn index -> Enum.at(storage_files, index, "placeholder-#{index}.pdf") end

# Re-running the seeds replaces the previously seeded and generated rows instead of duplicating
# them; real data (e.g. from `mix documents.backfill`) is not touched.
Api.MockData.delete_source("seed")
Api.MockData.delete_source("mock")

# Seeded boreholes are marked so the step above can find them again.
insert_borehole = fn attrs ->
  attrs = Map.update(attrs, :metadata, %{"source" => "seed"}, &Map.put(&1, "source", "seed"))
  %Borehole{} |> Borehole.changeset(attrs) |> Repo.insert!()
end

insert_layers = fn borehole, layers ->
  Enum.each(layers, fn attrs ->
    attrs =
      attrs
      |> Map.update(:depth_from_m, nil, &Decimal.new/1)
      |> Map.update(:depth_to_m, nil, &Decimal.new/1)

    %BoreholeLayer{}
    |> BoreholeLayer.changeset(attrs)
    |> Ecto.Changeset.put_change(:borehole_id, borehole.id)
    |> Repo.insert!()
  end)
end

insert_document = fn attrs ->
  %Document{} |> Document.changeset(attrs) |> Repo.insert!()
end

# The first document is the borehole's original, any others are additional information files.
attach_documents = fn borehole, [original | additional] ->
  {:ok, _links} = Api.Boreholes.attach_documents(borehole, original, additional)
end

# --- Germany: fully-filled-in borehole, modelled on the screenshot example from the task doc ---

schoenberg =
  insert_borehole.(%{
    name: "B 1/59 Schönberg- / Basler- / Carl Kistnerstrasse",
    external_id: "8012-00182",
    purpose: "Hydrogeologische Untersuchung",
    drilling_method: "Bohrung mit Ausbau",
    drilled_at: ~D[1959-09-10],
    location: %Geo.Point{coordinates: {9.17702, 48.77581}, srid: 4326},
    source_coordinate_system: "32U UTM",
    source_coordinate_raw: "412559.379, 5315392.271",
    total_depth_m: Decimal.new("18.3"),
    elevation_m: Decimal.new("262.0"),
    verified: true
  })

insert_layers.(schoenberg, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "3.5",
    stratigraphy: "Neuenburg-Formation",
    petrography: "Kies [gerundet] (steinig, schwach grobsandig, stark schluffig)",
    color: "grau"
  },
  %{
    position: 2,
    depth_from_m: "3.5",
    depth_to_m: "6.5",
    stratigraphy: "Neuenburg-Formation",
    petrography: "Kies [gerundet] (steinig, schwach sandig, schwach schluffig)",
    color: "braun"
  },
  %{
    position: 3,
    depth_from_m: "6.5",
    depth_to_m: "8.9",
    stratigraphy: "Neuenburg-Formation",
    petrography: "Kies [gerundet] (schwach grobsandig, steinig)",
    color: "grau"
  },
  %{
    position: 4,
    depth_from_m: "8.9",
    depth_to_m: "10.2",
    stratigraphy: "Neuenburg-Formation",
    petrography: "Kies [gerundet] (stark grobsandig, stark mittelsandig, steinig)",
    color: "bunt"
  },
  %{
    position: 5,
    depth_from_m: "10.2",
    depth_to_m: "11.0",
    stratigraphy: "Neuenburg-Formation",
    petrography: "Kies [gerundet] (stark grobsandig, steinig)",
    color: "graubraun"
  },
  %{
    position: 6,
    depth_from_m: "11.0",
    depth_to_m: "14.5",
    stratigraphy: "Neuenburg-Formation",
    petrography: "Kies [gerundet] (schwach grobsandig, steinig)",
    color: "bunt"
  },
  %{
    position: 7,
    depth_from_m: "14.5",
    depth_to_m: "15.6",
    stratigraphy: "Neuenburg-Formation",
    petrography: "Kies [gerundet] (stark grobsandig, steinig)",
    color: "bunt"
  },
  %{
    position: 8,
    depth_from_m: "15.6",
    depth_to_m: "18.3",
    stratigraphy: "Neuenburg-Formation",
    petrography: "Kies [gerundet] (schwach grobsandig, steinig)",
    color: "bunt"
  }
])

schoenberg_doc =
  insert_document.(%{
    original_filename: "B1-59_Schichtenverzeichnis.pdf",
    storage_path: storage_file.(0),
    mime_type: "image/png",
    source_country: "Germany",
    status: "reviewed"
  })

attach_documents.(schoenberg, [schoenberg_doc])

# --- Sparse record, to exercise nullability — only the required field (name) is set ---

sparse = insert_borehole.(%{name: "BH-X7 (teilweise erfasst)"})
insert_layers.(sparse, [%{position: 1, depth_from_m: "0.0", depth_to_m: "1.0"}])

# --- Australia: groundwater level, end_date, and metadata ---

melbourne =
  insert_borehole.(%{
    name: "Melbourne Water Main Drains Upgrade - Aberfeldie MD",
    external_id: "BH_AB01",
    drilling_method: "Hanjin D & B - 8D",
    drilled_at: ~D[2014-08-05],
    end_date: ~D[2014-08-05],
    location: %Geo.Point{coordinates: {144.9069, -37.7489}, srid: 4326},
    source_coordinate_system: "55H MGA94",
    source_coordinate_raw: "E: 314957.000, N: 5819600.000",
    total_depth_m: Decimal.new("1.8"),
    elevation_m: Decimal.new("35.7"),
    groundwater_level_m: Decimal.new("1.2"),
    metadata: %{"contractor" => "NTL Drilling", "driller" => "Sven P"}
  })

insert_layers.(melbourne, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "0.4",
    stratigraphy: "Topsoil",
    petrography: "Sandy CLAY, low plasticity, dark grey, fine sand",
    color: "dark grey"
  },
  %{
    position: 2,
    depth_from_m: "0.4",
    depth_to_m: "1.0",
    stratigraphy: "Natural",
    petrography: "Sandy CLAY, medium to high plasticity, dark grey, fine sand",
    color: "dark grey"
  },
  %{
    position: 3,
    depth_from_m: "1.0",
    depth_to_m: "1.8",
    stratigraphy: "Natural",
    petrography: "Clayey SAND, fine sand, dark grey, medium plasticity clay",
    color: "dark grey"
  }
])

# --- Nigeria: unverified, still processing ---

af01 =
  insert_borehole.(%{
    name: "AF01 Lagos Lagoon Crossing",
    external_id: "AF-01",
    purpose: "Site investigation for bridge foundation",
    drilling_method: "Wash boring",
    drilled_at: ~D[2003-02-18],
    location: %Geo.Point{coordinates: {3.3792, 6.5244}, srid: 4326},
    source_coordinate_system: "WGS84",
    source_coordinate_raw: "6.5244 N, 3.3792 E",
    total_depth_m: Decimal.new("22.0"),
    elevation_m: Decimal.new("2.1"),
    groundwater_level_m: Decimal.new("1.5"),
    verified: false
  })

insert_layers.(af01, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "4.0",
    stratigraphy: "Benin Formation",
    petrography: "Soft grey CLAY with organic matter",
    color: "dark grey"
  },
  %{
    position: 2,
    depth_from_m: "4.0",
    depth_to_m: "12.0",
    stratigraphy: "Benin Formation",
    petrography: "Loose to medium dense SAND, fine to medium grained",
    color: "yellow-brown"
  },
  %{
    position: 3,
    depth_from_m: "12.0",
    depth_to_m: "22.0",
    stratigraphy: "Benin Formation",
    petrography: "Dense SAND with gravel lenses",
    color: "brown"
  }
])

af01_doc =
  insert_document.(%{
    original_filename: "AF01.PDF",
    storage_path: storage_file.(1),
    mime_type: "application/pdf",
    source_country: "Nigeria",
    status: "processing"
  })

attach_documents.(af01, [af01_doc])

# --- France: multilingual stratigraphy/petrography terms ---

eur02 =
  insert_borehole.(%{
    name: "Sondage EUR02 - Bassin Parisien",
    external_id: "EUR-02",
    purpose: "Reconnaissance géotechnique",
    drilling_method: "Forage carotté",
    drilled_at: ~D[1998-05-03],
    location: %Geo.Point{coordinates: {2.3522, 48.8566}, srid: 4326},
    source_coordinate_system: "Lambert 93",
    source_coordinate_raw: "652000, 6862000",
    total_depth_m: Decimal.new("30.0"),
    elevation_m: Decimal.new("48.0"),
    verified: true
  })

insert_layers.(eur02, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "2.0",
    stratigraphy: "Remblais",
    petrography: "Remblais hétérogènes, sableux",
    color: "brun"
  },
  %{
    position: 2,
    depth_from_m: "2.0",
    depth_to_m: "9.0",
    stratigraphy: "Calcaire grossier",
    petrography: "Calcaire grossier, fissuré, blanchâtre",
    color: "blanc"
  },
  %{
    position: 3,
    depth_from_m: "9.0",
    depth_to_m: "18.0",
    stratigraphy: "Argile verte",
    petrography: "Argile plastique, verdâtre",
    color: "vert"
  },
  %{
    position: 4,
    depth_from_m: "18.0",
    depth_to_m: "30.0",
    stratigraphy: "Sables de Beauchamp",
    petrography: "Sables fins, compacts, beiges",
    color: "beige"
  }
])

# --- UAE: desert conditions, Arabic-region naming ---

mea01 =
  insert_borehole.(%{
    name: "BH-MEA-01 Dubai Marina",
    external_id: "MEA-01",
    drilling_method: "Rotary wash boring",
    drilled_at: ~D[2008-11-20],
    location: %Geo.Point{coordinates: {55.1403, 25.0772}, srid: 4326},
    source_coordinate_system: "WGS84",
    source_coordinate_raw: "25.0772 N, 55.1403 E",
    total_depth_m: Decimal.new("40.0"),
    elevation_m: Decimal.new("1.5"),
    groundwater_level_m: Decimal.new("2.0"),
    verified: false
  })

insert_layers.(mea01, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "6.0",
    stratigraphy: "Aeolian deposits",
    petrography: "Loose SAND, fine to medium, calcareous",
    color: "light brown"
  },
  %{
    position: 2,
    depth_from_m: "6.0",
    depth_to_m: "20.0",
    stratigraphy: "Fars Formation",
    petrography: "Weak to moderately weak GYPSUM/calcisiltite",
    color: "white-grey"
  },
  %{
    position: 3,
    depth_from_m: "20.0",
    depth_to_m: "40.0",
    stratigraphy: "Fars Formation",
    petrography: "Moderately strong calcareous SANDSTONE",
    color: "cream"
  }
])

# --- USA: Gulf Coast clay/sand sequence ---

nam02 =
  insert_borehole.(%{
    name: "NAM02 Houston Ship Channel",
    external_id: "NAM-02",
    drilling_method: "Hollow stem auger",
    drilled_at: ~D[2011-07-14],
    location: %Geo.Point{coordinates: {-95.2860, 29.7372}, srid: 4326},
    source_coordinate_system: "WGS84",
    source_coordinate_raw: "29.7372 N, 95.2860 W",
    total_depth_m: Decimal.new("15.0"),
    elevation_m: Decimal.new("4.0"),
    groundwater_level_m: Decimal.new("3.0"),
    verified: true
  })

insert_layers.(nam02, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "5.0",
    stratigraphy: "Beaumont Formation",
    petrography: "Stiff fat CLAY (CH), dark brown",
    color: "dark brown"
  },
  %{
    position: 2,
    depth_from_m: "5.0",
    depth_to_m: "10.0",
    stratigraphy: "Beaumont Formation",
    petrography: "Medium dense silty SAND",
    color: "tan"
  },
  %{
    position: 3,
    depth_from_m: "10.0",
    depth_to_m: "15.0",
    stratigraphy: "Beaumont Formation",
    petrography: "Very stiff sandy CLAY",
    color: "grey-brown"
  }
])

nam02_doc =
  insert_document.(%{
    original_filename: "NAM02.pdf",
    storage_path: storage_file.(2),
    mime_type: "application/pdf",
    source_country: "United States",
    status: "extracted"
  })

attach_documents.(nam02, [nam02_doc])

# --- Brazil: Portuguese terms ---

sam01 =
  insert_borehole.(%{
    name: "SAM01 Resende - Vale do Paraíba",
    external_id: "SAM-01",
    purpose: "Investigação geotécnica",
    drilling_method: "Sondagem a percussão (SPT)",
    drilled_at: ~D[2005-03-22],
    location: %Geo.Point{coordinates: {-44.4489, -22.4697}, srid: 4326},
    source_coordinate_system: "SIRGAS 2000 / UTM 23S",
    source_coordinate_raw: "7513000, 419000",
    total_depth_m: Decimal.new("12.5"),
    elevation_m: Decimal.new("410.0"),
    verified: false
  })

insert_layers.(sam01, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "3.0",
    stratigraphy: "Formação Resende",
    petrography: "Argila silto-arenosa, mole, marrom",
    color: "marrom"
  },
  %{
    position: 2,
    depth_from_m: "3.0",
    depth_to_m: "8.0",
    stratigraphy: "Formação Resende",
    petrography: "Areia argilosa, medianamente compacta",
    color: "amarelo"
  },
  %{
    position: 3,
    depth_from_m: "8.0",
    depth_to_m: "12.5",
    stratigraphy: "Embasamento cristalino",
    petrography: "Gnaisse alterado, duro",
    color: "cinza"
  }
])

# --- Indonesia: shared document that also covers sam01 above, to exercise the documents<->boreholes
#     many-to-many from the document side (one report covering multiple sites) ---

sea01 =
  insert_borehole.(%{
    name: "SEA01 Jakarta Alluvial Plain",
    external_id: "SEA-01",
    drilling_method: "Rotary drilling",
    drilled_at: ~D[2016-09-09],
    location: %Geo.Point{coordinates: {106.8456, -6.2088}, srid: 4326},
    source_coordinate_system: "WGS84",
    source_coordinate_raw: "6.2088 S, 106.8456 E",
    total_depth_m: Decimal.new("25.0"),
    elevation_m: Decimal.new("8.0"),
    groundwater_level_m: Decimal.new("1.0"),
    verified: false
  })

insert_layers.(sea01, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "10.0",
    stratigraphy: "Jakarta Alluvium",
    petrography: "Very soft CLAY, grey, high plasticity",
    color: "grey"
  },
  %{
    position: 2,
    depth_from_m: "10.0",
    depth_to_m: "25.0",
    stratigraphy: "Jakarta Alluvium",
    petrography: "Loose silty SAND with occasional peat",
    color: "dark grey"
  }
])

regional_summary_doc =
  insert_document.(%{
    original_filename: "FullReport01.pdf",
    storage_path: storage_file.(3),
    mime_type: "application/pdf",
    source_country: "Indonesia",
    status: "reviewed"
  })

attach_documents.(sam01, [regional_summary_doc])
attach_documents.(sea01, [regional_summary_doc])

# --- The "tough one": handwritten, hard to read, multiple source files, still failed ---

tough_one =
  insert_borehole.(%{
    name: "ToughOne-1 (handwritten log, low quality scan)",
    drilled_at: ~D[1962-04-01],
    verified: false
  })

insert_layers.(tough_one, [
  %{
    position: 1,
    depth_from_m: "0.0",
    depth_to_m: "2.0",
    stratigraphy: "?",
    petrography: nil,
    color: nil,
    raw_text: "0,0-2,0 unleserlich"
  },
  %{
    position: 2,
    depth_from_m: "2.0",
    depth_to_m: "5.4",
    stratigraphy: nil,
    petrography: "vermutlich Kies",
    color: "grau?",
    raw_text: "2,0-5,4(?) Kies grau?"
  }
])

tough_one_scan =
  insert_document.(%{
    original_filename: "ToughOne1.pdf",
    storage_path: storage_file.(4),
    mime_type: "application/pdf",
    status: "failed"
  })

tough_one_scan_2 =
  insert_document.(%{
    original_filename: "ToughOne2.pdf",
    storage_path: storage_file.(5),
    mime_type: "application/pdf",
    status: "failed"
  })

attach_documents.(tough_one, [tough_one_scan, tough_one_scan_2])

# Plus generated boreholes for lists, search and the map: MOCK_BOREHOLES=10000 for the maximum.
mock_count = String.to_integer(System.get_env("MOCK_BOREHOLES", "1000"))
Api.MockData.generate(min(mock_count, Api.MockData.max_count()))

IO.puts(
  "Seeded #{Repo.aggregate(Borehole, :count)} boreholes, " <>
    "#{Repo.aggregate(BoreholeLayer, :count)} layers, " <>
    "#{Repo.aggregate(Document, :count)} documents."
)
