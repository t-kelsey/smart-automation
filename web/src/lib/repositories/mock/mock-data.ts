import { Faker, de, en, es, fr } from '@faker-js/faker';
import type {
	Borehole,
	BoreholeDocument,
	BoreholeLayer,
	DocumentStatus,
	DocumentType,
	LithologyKey
} from '#lib/domain/borehole.ts';

// Own instance so seeding here does not affect other users of faker.
const faker = new Faker({ locale: [en, de, fr, es] });
faker.seed(42);

interface LayerTemplate {
	lithology: LithologyKey;
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
		lithology: 'fill',
		description: ['Made ground, gravelly sand with brick debris', 'Fill, mixed sand and rubble'],
		colors: [{ hex: '#a89f91', name: 'Grey-beige' }],
		stratigraphy: [quaternary]
	},
	{
		lithology: 'gravel',
		description: ['Sandy gravel, medium dense', 'Gravel, rounded, dense'],
		colors: [{ hex: '#d8c27a', name: 'Yellow' }],
		stratigraphy: [quaternary]
	},
	{
		lithology: 'sand',
		description: ['Fine to medium sand, loose', 'Silty sand, medium dense'],
		colors: [{ hex: '#e0cf9b', name: 'Sand' }],
		stratigraphy: [quaternary]
	},
	{
		lithology: 'silt',
		description: ['Clayey silt, soft to stiff', 'Silt, slightly sandy'],
		colors: [{ hex: '#b9b08e', name: 'Olive' }],
		stratigraphy: [quaternary]
	},
	{
		lithology: 'clay',
		description: ['Clay, stiff, low plasticity', 'Silty clay, soft'],
		colors: [{ hex: '#8c7b6b', name: 'Brown-grey' }],
		stratigraphy: [quaternary]
	}
];

const rockTemplates: LayerTemplate[] = [
	{
		lithology: 'marl',
		description: ['Marlstone, weathered, with gypsum nodules', 'Marl, grey-red, medium hard'],
		colors: [{ hex: '#b86a5a', name: 'Red-brown' }],
		stratigraphy: [keuper[0]]
	},
	{
		lithology: 'claystone',
		description: ['Claystone, dark grey, fractured', 'Claystone, laminated'],
		colors: [{ hex: '#7f8a8c', name: 'Grey' }],
		stratigraphy: keuper
	},
	{
		lithology: 'sandstone',
		description: ['Fine-grained sandstone, slightly weathered', 'Sandstone, medium hard'],
		colors: [{ hex: '#d9c9a3', name: 'Light beige' }],
		stratigraphy: [keuper[1]]
	},
	{
		lithology: 'limestone',
		description: ['Limestone, hard, jointed', 'Limestone, massive, karstified'],
		colors: [{ hex: '#bfc5c9', name: 'Light grey' }],
		stratigraphy: muschelkalk
	}
];

const topsoil: LayerTemplate = {
	lithology: 'topsoil',
	description: ['Humous topsoil, dark brown'],
	colors: [{ hex: '#6b4f3a', name: 'Dark brown' }],
	stratigraphy: [quaternary]
};

const regions = [
	{ place: 'Stuttgart, Baden-Württemberg', country: 'DE', lat: 48.7758, lon: 9.177, elev: 310 },
	{ place: 'Freiburg, Baden-Württemberg', country: 'DE', lat: 47.999, lon: 7.8421, elev: 278 },
	{ place: 'Zürich, Switzerland', country: 'CH', lat: 47.3769, lon: 8.5417, elev: 408 },
	{ place: 'Lyon, France', country: 'FR', lat: 45.764, lon: 4.8357, elev: 173 },
	{ place: 'Madrid, Spain', country: 'ES', lat: 40.4168, lon: -3.7038, elev: 650 }
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

function makeLayers(totalDepth: number): BoreholeLayer[] {
	const count = faker.number.int({ min: 4, max: 10 });
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
					? faker.helpers.arrayElement(softTemplates)
					: faker.helpers.arrayElement(rockTemplates);
		return {
			id: faker.string.uuid(),
			position: index + 1,
			startDepth,
			endDepth: bounds[index + 1],
			stratigraphy: faker.helpers.arrayElement(template.stratigraphy),
			petrography: {
				lithology: template.lithology,
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

	return {
		id,
		name,
		externalId: faker.string.alphanumeric({ length: 8, casing: 'upper' }),
		date: drilled.toISOString().slice(0, 10),
		endDate: end.toISOString().slice(0, 10),
		cause: faker.helpers.arrayElement(purposes),
		elevation: round(region.elev + faker.number.float({ min: -40, max: 40 }), 2),
		totalDepth,
		groundwaterLevel: round(faker.number.float({ min: 0.5, max: totalDepth * 0.6 })),
		drillingMethod: faker.helpers.arrayElement(methods),
		client: faker.helpers.arrayElement(clients),
		location: {
			lat: round(region.lat + faker.number.float({ min: -0.2, max: 0.2 }), 5),
			lon: round(region.lon + faker.number.float({ min: -0.2, max: 0.2 }), 5),
			place: region.place
		},
		verified: faker.datatype.boolean(),
		layers: makeLayers(totalDepth),
		documents: makeDocuments(id, name, region.country)
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
	layers: [
		['topsoil', 0, 0.6, quaternary, 'Humous topsoil, dark brown', '#6b4f3a', 'Dark brown'],
		[
			'fill',
			0.6,
			3.2,
			quaternary,
			'Made ground, gravelly sand with brick debris',
			'#a89f91',
			'Grey-beige'
		],
		['gravel', 3.2, 7.5, quaternary, 'Sandy gravel, medium dense', '#d8c27a', 'Yellow'],
		['silt', 7.5, 10, quaternary, 'Clayey silt, soft to stiff', '#b9b08e', 'Olive'],
		[
			'marl',
			10,
			14.8,
			keuper[0],
			'Marlstone, weathered, with gypsum nodules',
			'#b86a5a',
			'Red-brown'
		],
		['claystone', 14.8, 19.5, keuper[1], 'Claystone, dark grey, fractured', '#7f8a8c', 'Grey'],
		[
			'sandstone',
			19.5,
			21.5,
			keuper[1],
			'Fine-grained sandstone, slightly weathered',
			'#d9c9a3',
			'Light beige'
		],
		['limestone', 21.5, 24, muschelkalk[0], 'Limestone, hard, jointed', '#bfc5c9', 'Light grey']
	].map(([lithology, startDepth, endDepth, stratigraphy, description, hex, colorName], i) => ({
		id: `00000000-0000-4000-8000-${String(1042000 + i + 1).padStart(12, '0')}`,
		position: i + 1,
		startDepth: startDepth as number,
		endDepth: endDepth as number,
		stratigraphy: stratigraphy as BoreholeLayer['stratigraphy'],
		petrography: { lithology: lithology as LithologyKey, description: description as string },
		color: { hex: hex as string, name: colorName as string }
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

/** 20 boreholes with layers and documents; deterministic across runs. */
export const mockBoreholes: Borehole[] = [
	bk1042,
	...Array.from({ length: 19 }, (_, i) => makeBorehole(i + 1))
];
