import { Faker, de, en, es, fr } from '@faker-js/faker';
import type {
	Borehole,
	BoreholeDocument,
	BoreholeLayer,
	DocumentStatus,
	DocumentType
} from '#lib/domain/borehole.ts';
import type { Composition, SoilKey } from '#lib/din4023/index.ts';
import din4023 from '../../../../../standards/din-4023/din-4023.json';

// Own instance so seeding here does not affect other users of faker.
const faker = new Faker({ locale: [en, de, fr, es] });
faker.seed(42);

interface LayerTemplate {
	composition: Composition;
	description: string[];
	colors: { hex: string; name: string }[];
	stratigraphy: { code: string; name: string }[];
}

const quaternary = { code: 'Q', name: 'Quaternary' };
const keuper = [
	{ code: 'km1', name: 'Gipskeuper' },
	{ code: 'ku', name: 'Lettenkeuper' }
];
const muschelkalk = [{ code: 'mo', name: 'Oberer Muschelkalk' }];

/** Soft (young) templates are used near the surface, rock templates below. */
const softTemplates: LayerTemplate[] = [
	{
		composition: {
			main: 'anthropogenic',
			breakdown: { main: 'sand', secondary: [{ material: 'gravel' }] }
		},
		description: ['Made ground, gravelly sand with brick debris', 'Fill, sand and rubble'],
		colors: [{ hex: '#a89f91', name: 'Grey-beige' }],
		stratigraphy: [quaternary]
	},
	{
		composition: { main: 'gravel', secondary: [{ material: 'sand', proportion: 'strong' }] },
		description: ['Sandy gravel, medium dense', 'Gravel, strongly sandy, dense'],
		colors: [{ hex: '#d8c27a', name: 'Yellow' }],
		stratigraphy: [quaternary]
	},
	{
		composition: { main: 'sand', secondary: [{ material: 'silt', proportion: 'weak' }] },
		description: ['Sand, slightly silty, loose', 'Slightly silty sand, medium dense'],
		colors: [{ hex: '#e0cf9b', name: 'Sand' }],
		stratigraphy: [quaternary]
	},
	{
		composition: { main: 'silt', secondary: [{ material: 'clay' }] },
		description: ['Clayey silt, soft to stiff', 'Silt, clayey'],
		colors: [{ hex: '#b9b08e', name: 'Olive' }],
		stratigraphy: [quaternary]
	},
	{
		composition: { main: 'clay', secondary: [{ material: 'silt' }] },
		description: ['Silty clay, stiff, low plasticity', 'Clay, silty, soft'],
		colors: [{ hex: '#8c7b6b', name: 'Brown-grey' }],
		stratigraphy: [quaternary]
	}
];

const triassicRocks: LayerTemplate[] = [
	{
		composition: { main: 'marlstone' },
		description: ['Marlstone, weathered, with gypsum nodules', 'Marl, grey-red, medium hard'],
		colors: [{ hex: '#b86a5a', name: 'Red-brown' }],
		stratigraphy: [keuper[0]]
	},
	{
		composition: { main: 'claystone' },
		description: ['Claystone, dark grey, fractured', 'Claystone, laminated'],
		colors: [{ hex: '#7f8a8c', name: 'Grey' }],
		stratigraphy: keuper
	},
	{
		composition: { main: 'sandstone' },
		description: ['Fine-grained sandstone, slightly weathered', 'Sandstone, medium hard'],
		colors: [{ hex: '#d9c9a3', name: 'Light beige' }],
		stratigraphy: [keuper[1]]
	},
	{
		composition: { main: 'limestone' },
		description: ['Limestone, hard, jointed', 'Limestone, massive, karstified'],
		colors: [{ hex: '#bfc5c9', name: 'Light grey' }],
		stratigraphy: muschelkalk
	}
];

const rock = (
	main: Composition['main'],
	description: string[],
	hex: string,
	colorName: string,
	stratigraphy: { code: string; name: string }[]
): LayerTemplate => ({
	composition: { main } as Composition,
	description,
	colors: [{ hex, name: colorName }],
	stratigraphy
});

const crystallineRocks: LayerTemplate[] = [
	rock(
		'foliatedMetamorphic',
		['Gneiss, foliated, moderately weathered', 'Schist, fractured'],
		'#8a8f94',
		'Grey',
		[{ code: 'PR', name: 'Precambrian' }]
	),
	rock(
		'plutonic',
		['Granite, fresh, massive', 'Granite, weathered, jointed'],
		'#c4a79a',
		'Pink-grey',
		[{ code: 'PZ', name: 'Palaeozoic' }]
	),
	rock('quartzite', ['Quartzite, very hard, jointed'], '#cfd2d6', 'Light grey', [
		{ code: 'PR', name: 'Precambrian' }
	])
];

const volcanicRocks: LayerTemplate[] = [
	rock('volcanic', ['Basalt, vesicular, fresh', 'Basalt, columnar, hard'], '#4d5156', 'Dark grey', [
		{ code: 'N', name: 'Neogene' }
	]),
	rock('tuff', ['Tuff, welded, weathered', 'Volcanic tuff, soft'], '#b8a58c', 'Beige', [
		{ code: 'N', name: 'Neogene' }
	]),
	rock('volcanic', ['Andesite, fractured'], '#6f6a69', 'Grey-brown', [
		{ code: 'Q', name: 'Quaternary' }
	])
];

const sedimentaryRocks: LayerTemplate[] = [
	rock(
		'sandstone',
		['Sandstone, medium grained, moderately hard', 'Sandstone, cross-bedded'],
		'#d6b98a',
		'Tan',
		[
			{ code: 'K', name: 'Cretaceous' },
			{ code: 'J', name: 'Jurassic' }
		]
	),
	rock('siltstone', ['Siltstone, thinly bedded'], '#9a9585', 'Grey-olive', [
		{ code: 'T', name: 'Triassic' }
	]),
	rock(
		'limestone',
		['Limestone, karstic, hard', 'Limestone, bedded, fossiliferous'],
		'#c9ccc7',
		'Light grey',
		[
			{ code: 'J', name: 'Jurassic' },
			{ code: 'C', name: 'Carboniferous' }
		]
	),
	rock('claystone', ['Claystone, firm, slickensided', 'Shale, laminated'], '#6f7479', 'Dark grey', [
		{ code: 'K', name: 'Cretaceous' }
	]),
	rock('dolomite', ['Dolomite, massive'], '#d9d2c0', 'Cream', [{ code: 'T', name: 'Triassic' }])
];

const rockSets = {
	triassic: triassicRocks,
	crystalline: crystallineRocks,
	volcanic: volcanicRocks,
	sedimentary: sedimentaryRocks
};

/** Table 1 soil ids of the shared standard file (ADR-0022) mapped to the drawing model keys. */
const soilKeys: Record<string, SoilKey> = {
	grosser_block: 'largeBoulder',
	block: 'boulder',
	stein: 'cobble',
	kies: 'gravel',
	grobkies: 'coarseGravel',
	mittelkies: 'mediumGravel',
	feinkies: 'fineGravel',
	sand: 'sand',
	grobsand: 'coarseSand',
	mittelsand: 'mediumSand',
	feinsand: 'fineSand',
	schluff: 'silt',
	grobschluff: 'coarseSilt',
	ton: 'clay',
	torf_humus: 'peat',
	vulkanische_aschen: 'volcanicAsh',
	braunkohle: 'lignite'
};

const dinHex = new Map(din4023.farben.map((f) => [f.name, f.hex.toLowerCase()]));

/**
 * One template per pure soil of Table 1, so every hatch and colour of the standard shows up.
 * Colour name and hex come from Annex A as listed in the standard file; the secondary
 * component (Nebenanteil) uses the German adjective of the table.
 */
const standardSoilTemplates: LayerTemplate[] = din4023.tabelle_1.bodenarten.flatMap((soil) => {
	const key = soilKeys[soil.id];
	const hex = dinHex.get(soil.farbe);
	if (!key || !hex) return [];
	const partner = soil.id === 'kies' || soil.id === 'grobkies' ? 'sand' : 'schluff';
	const partnerSoil = din4023.tabelle_1.bodenarten.find((b) => b.id === partner)!;
	const adjective = partnerSoil.benennung.nebenanteil!;
	return [
		{
			composition: { main: key, secondary: [{ material: soilKeys[partner], proportion: 'weak' }] },
			description: [`${soil.benennung.hauptanteil}, schwach ${adjective}`],
			colors: [{ hex, name: soil.farbe }],
			stratigraphy: [soil.id === 'braunkohle' ? { code: 'T', name: 'Tertiary' } : quaternary]
		}
	];
});

/** Standard soils are listed twice to weight them equally with the hand-written ones. */
const allSoftTemplates = [...softTemplates, ...standardSoilTemplates, ...standardSoilTemplates];

const topsoil: LayerTemplate = {
	composition: { main: 'topsoil' },
	description: ['Humous topsoil, dark brown'],
	colors: [{ hex: '#6b4f3a', name: 'Dark brown' }],
	stratigraphy: [quaternary]
};

const regions = [
	{
		place: 'Stuttgart, Baden-Württemberg',
		country: 'DE',
		lang: 'de',
		lat: 48.7758,
		lon: 9.177,
		elev: 310,
		rocks: 'triassic' as keyof typeof rockSets
	},
	{
		place: 'Freiburg, Baden-Württemberg',
		country: 'DE',
		lang: 'de',
		lat: 47.999,
		lon: 7.8421,
		elev: 278,
		rocks: 'triassic' as keyof typeof rockSets
	},
	{
		place: 'Zürich, Switzerland',
		country: 'CH',
		lang: 'de',
		lat: 47.3769,
		lon: 8.5417,
		elev: 408,
		rocks: 'triassic' as keyof typeof rockSets
	},
	{
		place: 'Lyon, France',
		country: 'FR',
		lang: 'fr',
		lat: 45.764,
		lon: 4.8357,
		elev: 173,
		rocks: 'triassic' as keyof typeof rockSets
	},
	{
		place: 'Madrid, Spain',
		country: 'ES',
		lang: 'es',
		lat: 40.4168,
		lon: -3.7038,
		elev: 650,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Oslo, Norway',
		country: 'NO',
		lang: 'no',
		lat: 59.9139,
		lon: 10.7522,
		elev: 23,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Stockholm, Sweden',
		country: 'SE',
		lang: 'sv',
		lat: 59.3293,
		lon: 18.0686,
		elev: 28,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'London, United Kingdom',
		country: 'GB',
		lang: 'en',
		lat: 51.5074,
		lon: -0.1278,
		elev: 15,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Milan, Italy',
		country: 'IT',
		lang: 'it',
		lat: 45.4642,
		lon: 9.19,
		elev: 120,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Naples, Italy',
		country: 'IT',
		lang: 'it',
		lat: 40.8518,
		lon: 14.2681,
		elev: 17,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Istanbul, Türkiye',
		country: 'TR',
		lang: 'tr',
		lat: 41.0082,
		lon: 28.9784,
		elev: 40,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Athens, Greece',
		country: 'GR',
		lang: 'el',
		lat: 37.9838,
		lon: 23.7275,
		elev: 70,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Warsaw, Poland',
		country: 'PL',
		lang: 'pl',
		lat: 52.2297,
		lon: 21.0122,
		elev: 100,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Reykjavik, Iceland',
		country: 'IS',
		lang: 'is',
		lat: 64.1466,
		lon: -21.9426,
		elev: 10,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Cairo, Egypt',
		country: 'EG',
		lang: 'ar',
		lat: 30.0444,
		lon: 31.2357,
		elev: 23,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Lagos, Nigeria',
		country: 'NG',
		lang: 'en',
		lat: 6.5244,
		lon: 3.3792,
		elev: 41,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Johannesburg, South Africa',
		country: 'ZA',
		lang: 'en',
		lat: -26.2041,
		lon: 28.0473,
		elev: 1753,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Nairobi, Kenya',
		country: 'KE',
		lang: 'en',
		lat: -1.2921,
		lon: 36.8219,
		elev: 1795,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Dubai, United Arab Emirates',
		country: 'AE',
		lang: 'en',
		lat: 25.2048,
		lon: 55.2708,
		elev: 5,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Riyadh, Saudi Arabia',
		country: 'SA',
		lang: 'ar',
		lat: 24.7136,
		lon: 46.6753,
		elev: 612,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Mumbai, India',
		country: 'IN',
		lang: 'en',
		lat: 19.076,
		lon: 72.8777,
		elev: 14,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Delhi, India',
		country: 'IN',
		lang: 'en',
		lat: 28.6139,
		lon: 77.209,
		elev: 216,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Bangkok, Thailand',
		country: 'TH',
		lang: 'th',
		lat: 13.7563,
		lon: 100.5018,
		elev: 2,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Singapore',
		country: 'SG',
		lang: 'en',
		lat: 1.3521,
		lon: 103.8198,
		elev: 15,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Jakarta, Indonesia',
		country: 'ID',
		lang: 'id',
		lat: -6.2088,
		lon: 106.8456,
		elev: 8,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Manila, Philippines',
		country: 'PH',
		lang: 'en',
		lat: 14.5995,
		lon: 120.9842,
		elev: 16,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Hong Kong, China',
		country: 'HK',
		lang: 'en',
		lat: 22.3193,
		lon: 114.1694,
		elev: 30,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Shanghai, China',
		country: 'CN',
		lang: 'zh',
		lat: 31.2304,
		lon: 121.4737,
		elev: 4,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Chongqing, China',
		country: 'CN',
		lang: 'zh',
		lat: 29.563,
		lon: 106.5516,
		elev: 244,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Seoul, South Korea',
		country: 'KR',
		lang: 'ko',
		lat: 37.5665,
		lon: 126.978,
		elev: 38,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Tokyo, Japan',
		country: 'JP',
		lang: 'ja',
		lat: 35.6762,
		lon: 139.6503,
		elev: 40,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Osaka, Japan',
		country: 'JP',
		lang: 'ja',
		lat: 34.6937,
		lon: 135.5023,
		elev: 10,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Sydney, Australia',
		country: 'AU',
		lang: 'en',
		lat: -33.8688,
		lon: 151.2093,
		elev: 58,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Perth, Australia',
		country: 'AU',
		lang: 'en',
		lat: -31.9505,
		lon: 115.8605,
		elev: 31,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Auckland, New Zealand',
		country: 'NZ',
		lang: 'en',
		lat: -36.8485,
		lon: 174.7633,
		elev: 26,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Vancouver, Canada',
		country: 'CA',
		lang: 'en',
		lat: 49.2827,
		lon: -123.1207,
		elev: 70,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Toronto, Canada',
		country: 'CA',
		lang: 'en',
		lat: 43.6532,
		lon: -79.3832,
		elev: 76,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Seattle, USA',
		country: 'US',
		lang: 'en',
		lat: 47.6062,
		lon: -122.3321,
		elev: 53,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Los Angeles, USA',
		country: 'US',
		lang: 'en',
		lat: 34.0522,
		lon: -118.2437,
		elev: 93,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Denver, USA',
		country: 'US',
		lang: 'en',
		lat: 39.7392,
		lon: -104.9903,
		elev: 1609,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'New York, USA',
		country: 'US',
		lang: 'en',
		lat: 40.7128,
		lon: -74.006,
		elev: 10,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Mexico City, Mexico',
		country: 'MX',
		lang: 'es',
		lat: 19.4326,
		lon: -99.1332,
		elev: 2240,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Panama City, Panama',
		country: 'PA',
		lang: 'es',
		lat: 8.9824,
		lon: -79.5199,
		elev: 12,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'Bogotá, Colombia',
		country: 'CO',
		lang: 'es',
		lat: 4.711,
		lon: -74.0721,
		elev: 2640,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Lima, Peru',
		country: 'PE',
		lang: 'es',
		lat: -12.0464,
		lon: -77.0428,
		elev: 154,
		rocks: 'sedimentary' as keyof typeof rockSets
	},
	{
		place: 'Santiago, Chile',
		country: 'CL',
		lang: 'es',
		lat: -33.4489,
		lon: -70.6693,
		elev: 520,
		rocks: 'volcanic' as keyof typeof rockSets
	},
	{
		place: 'São Paulo, Brazil',
		country: 'BR',
		lang: 'pt',
		lat: -23.5505,
		lon: -46.6333,
		elev: 760,
		rocks: 'crystalline' as keyof typeof rockSets
	},
	{
		place: 'Buenos Aires, Argentina',
		country: 'AR',
		lang: 'es',
		lat: -34.6037,
		lon: -58.3816,
		elev: 25,
		rocks: 'sedimentary' as keyof typeof rockSets
	}
];

const purposes = [
	'Ground investigation for tunnel alignment',
	'Foundation investigation',
	'Groundwater monitoring well',
	'Geotechnical survey for road construction',
	'Raw material exploration'
];
const methods = ['Rotary core drilling', 'Auger drilling', 'Percussion drilling', 'Wash boring'];
const clients = ['Example Construction Authority', 'Stadtwerke Beispiel', 'Ministry of Transport'];

const round = (value: number, digits = 1) => Number(value.toFixed(digits));

function makeLayers(totalDepth: number, rocks: LayerTemplate[]): BoreholeLayer[] {
	const count = faker.number.int({ min: 4, max: 15 });
	// Random cut points give contiguous layers that end exactly at the total depth.
	const cuts = new Set<number>();
	while (cuts.size < count - 1)
		cuts.add(round(faker.number.float({ min: 0.3, max: totalDepth - 0.3 })));
	const bounds = [0, ...[...cuts].sort((a, b) => a - b), totalDepth];

	const softCount = Math.max(1, Math.round((count - 1) / 2));
	return bounds.slice(0, -1).map((startDepth, index) => {
		const template =
			index === 0
				? topsoil
				: index <= softCount
					? faker.helpers.arrayElement(allSoftTemplates)
					: faker.helpers.arrayElement(rocks);
		return {
			id: faker.string.uuid(),
			position: index + 1,
			startDepth,
			endDepth: bounds[index + 1],
			stratigraphy: faker.helpers.arrayElement(template.stratigraphy),
			petrography: {
				composition: template.composition,
				description: faker.helpers.arrayElement(template.description)
			},
			color: faker.helpers.arrayElement(template.colors)
		};
	});
}

const documentTypes: { ext: string; type: DocumentType }[] = [
	{ ext: 'pdf', type: 'pdf' },
	{ ext: 'jpg', type: 'image' },
	{ ext: 'docx', type: 'docx' }
];
const statuses: DocumentStatus[] = ['pending', 'processing', 'extracted', 'failed', 'reviewed'];

function makeDocuments(boreholeId: string, name: string, country: string): BoreholeDocument[] {
	const stem = name.replace(/\s+/g, '');
	return faker.helpers.arrayElements(documentTypes, { min: 1, max: 3 }).map(({ ext, type }) => ({
		id: `${boreholeId}-D-${ext}`,
		name: `${stem}_${faker.word.noun()}.${ext}`,
		type,
		status: faker.helpers.arrayElement(statuses),
		language: country,
		pages: type === 'image' ? undefined : faker.number.int({ min: 1, max: 12 }),
		sizeKb: faker.number.int({ min: 120, max: 5000 }),
		url: '#'
	}));
}

function makeBorehole(index: number): Borehole {
	const region = faker.helpers.arrayElement(regions);
	const totalDepth = round(faker.number.float({ min: 8, max: 60 }));
	const drilled = faker.date.between({ from: '1960-01-01', to: '2020-12-31' });
	const end = new Date(drilled.getTime() + faker.number.int({ min: 0, max: 14 }) * 86_400_000);
	const id = faker.string.uuid();
	const name = `BK ${1000 + index * 7 + faker.number.int({ min: 0, max: 6 })}`;
	const groundwaterLevel = round(faker.number.float({ min: 0.5, max: totalDepth * 0.6 }));

	return {
		id,
		name,
		externalId: faker.string.alphanumeric({ length: 8, casing: 'upper' }),
		date: drilled.toISOString().slice(0, 10),
		endDate: end.toISOString().slice(0, 10),
		cause: faker.helpers.arrayElement(purposes),
		elevation: round(
			Math.max(
				0.5,
				region.elev + faker.number.float({ min: -40, max: 40 }) * Math.min(1, region.elev / 100)
			),
			2
		),
		totalDepth,
		groundwaterLevel,
		drillingMethod: faker.helpers.arrayElement(methods),
		client: faker.helpers.arrayElement(clients),
		location: {
			lat: round(region.lat + faker.number.float({ min: -0.2, max: 0.2 }), 5),
			lon: round(region.lon + faker.number.float({ min: -0.2, max: 0.2 }), 5),
			place: region.place
		},
		verified: faker.datatype.boolean(),
		layers: makeLayers(totalDepth, rockSets[region.rocks]),
		documents: makeDocuments(id, name, region.lang)
	};
}

/** Borehole BK 1042 as used before the data layer existed; kept first and stable. */
const bk1042: Borehole = {
	id: 'BK-1042',
	name: 'BK 1042',
	date: '1987-06-12',
	cause: 'Ground investigation for tunnel alignment',
	elevation: 312.4,
	totalDepth: 24,
	drillingMethod: 'Rotary core drilling',
	client: 'Example Construction Authority',
	location: { lat: 48.77581, lon: 9.17702, place: 'Stuttgart, Baden-Württemberg' },
	verified: true,
	groundwaterLevel: 8.2,
	layers: (
		[
			{
				startDepth: 0,
				endDepth: 0.6,
				stratigraphy: quaternary,
				petrography: {
					composition: { main: 'topsoil' },
					description: 'Humous topsoil, dark brown'
				},
				color: { hex: '#6b4f3a', name: 'Dark brown' }
			},
			{
				startDepth: 0.6,
				endDepth: 3.2,
				stratigraphy: quaternary,
				petrography: {
					composition: {
						main: 'anthropogenic',
						breakdown: { main: 'sand', secondary: [{ material: 'gravel' }] }
					},
					description: 'Made ground, gravelly sand with brick debris'
				},
				color: { hex: '#a89f91', name: 'Grey-beige' }
			},
			{
				startDepth: 3.2,
				endDepth: 7.5,
				stratigraphy: quaternary,
				petrography: {
					composition: {
						main: 'gravel',
						coMain: 'sand',
						secondary: [{ material: 'silt', proportion: 'weak' }]
					},
					description: 'Sandy gravel with slightly silty fines, medium dense'
				},
				color: { hex: '#d8c27a', name: 'Yellow' }
			},
			{
				startDepth: 7.5,
				endDepth: 10,
				stratigraphy: quaternary,
				petrography: {
					composition: {
						main: 'silt',
						secondary: [{ material: 'clay' }, { material: 'fineSand', proportion: 'weak' }]
					},
					description: 'Clayey silt, soft to stiff'
				},
				color: { hex: '#b9b08e', name: 'Olive' }
			},
			{
				startDepth: 10,
				endDepth: 14.8,
				stratigraphy: keuper[0],
				petrography: {
					composition: { main: 'marlstone', breakdown: { main: 'clay' } },
					description: 'Marlstone, weathered, with gypsum nodules'
				},
				color: { hex: '#b86a5a', name: 'Red-brown' }
			},
			{
				startDepth: 14.8,
				endDepth: 19.5,
				stratigraphy: keuper[1],
				petrography: {
					composition: { main: 'claystone' },
					description: 'Claystone, dark grey, fractured'
				},
				color: { hex: '#7f8a8c', name: 'Grey' }
			},
			{
				startDepth: 19.5,
				endDepth: 21.5,
				stratigraphy: keuper[1],
				petrography: {
					composition: { main: 'sandstone' },
					description: 'Fine-grained sandstone, slightly weathered'
				},
				color: { hex: '#d9c9a3', name: 'Light beige' }
			},
			{
				startDepth: 21.5,
				endDepth: 24,
				stratigraphy: muschelkalk[0],
				petrography: {
					composition: { main: 'limestone' },
					description: 'Limestone, hard, jointed'
				},
				color: { hex: '#bfc5c9', name: 'Light grey' }
			}
		] as Omit<BoreholeLayer, 'id' | 'position'>[]
	).map((layer, i) => ({
		...layer,
		id: `00000000-0000-4000-8000-${String(1042000 + i + 1).padStart(12, '0')}`,
		position: i + 1
	})),
	documents: [
		{
			id: 'D1',
			name: 'BK1042_Schichtenverzeichnis.pdf',
			type: 'pdf',
			status: 'reviewed',
			language: 'de',
			pages: 3,
			sizeKb: 1240,
			url: '#'
		},
		{
			id: 'D2',
			name: 'BK1042_Kernfoto_Kasten1-4.jpg',
			type: 'image',
			status: 'extracted',
			sizeKb: 3860,
			url: '#'
		},
		{
			id: 'D3',
			name: 'BK1042_Bohrbericht.docx',
			type: 'docx',
			status: 'pending',
			language: 'de',
			pages: 7,
			sizeKb: 410,
			url: '#'
		}
	]
};

/** 261 boreholes worldwide with layers and documents; deterministic across runs. */
export const mockBoreholes: Borehole[] = [
	bk1042,
	...Array.from({ length: 10000 }, (_, i) => makeBorehole(i + 1))
];
