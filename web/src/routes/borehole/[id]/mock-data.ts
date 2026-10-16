import type { Borehole } from '#lib/components/borehole/types.ts';

// TODO: replace with an API call once the API and data model exist.
export const mockBorehole: Borehole = {
	id: 'BK-1042',
	name: 'BK 1042',
	date: '1987-06-12',
	cause: 'Ground investigation for tunnel alignment',
	elevation: 312.4,
	totalDepth: 24,
	drillingMethod: 'Rotary core drilling',
	client: 'Example Construction Authority',
	location: { lat: 48.77581, lon: 9.17702, place: 'Stuttgart, Baden-Württemberg' },
	layers: [
		{
			id: 'L1',
			startDepth: 0,
			endDepth: 0.6,
			stratigraphy: { code: 'Q', name: 'Quaternary' },
			petrography: { lithology: 'topsoil', description: 'Humous topsoil, dark brown' },
			color: { hex: '#6b4f3a', name: 'Dark brown' }
		},
		{
			id: 'L2',
			startDepth: 0.6,
			endDepth: 3.2,
			stratigraphy: { code: 'Q', name: 'Quaternary' },
			petrography: {
				lithology: 'fill',
				description: 'Made ground, gravelly sand with brick debris'
			},
			color: { hex: '#a89f91', name: 'Grey-beige' }
		},
		{
			id: 'L3',
			startDepth: 3.2,
			endDepth: 7.5,
			stratigraphy: { code: 'Q', name: 'Quaternary' },
			petrography: { lithology: 'gravel', description: 'Sandy gravel, medium dense' },
			color: { hex: '#d8c27a', name: 'Yellow' }
		},
		{
			id: 'L4',
			startDepth: 7.5,
			endDepth: 10,
			stratigraphy: { code: 'Q', name: 'Quaternary' },
			petrography: { lithology: 'silt', description: 'Clayey silt, soft to stiff' },
			color: { hex: '#b9b08e', name: 'Olive' }
		},
		{
			id: 'L5',
			startDepth: 10,
			endDepth: 14.8,
			stratigraphy: { code: 'km1', name: 'Gipskeuper' },
			petrography: { lithology: 'marl', description: 'Marlstone, weathered, with gypsum nodules' },
			color: { hex: '#b86a5a', name: 'Red-brown' }
		},
		{
			id: 'L6',
			startDepth: 14.8,
			endDepth: 19.5,
			stratigraphy: { code: 'ku', name: 'Lettenkeuper' },
			petrography: { lithology: 'claystone', description: 'Claystone, dark grey, fractured' },
			color: { hex: '#7f8a8c', name: 'Grey' }
		},
		{
			id: 'L7',
			startDepth: 19.5,
			endDepth: 21.5,
			stratigraphy: { code: 'ku', name: 'Lettenkeuper' },
			petrography: {
				lithology: 'sandstone',
				description: 'Fine-grained sandstone, slightly weathered'
			},
			color: { hex: '#d9c9a3', name: 'Light beige' }
		},
		{
			id: 'L8',
			startDepth: 21.5,
			endDepth: 24,
			stratigraphy: { code: 'mo', name: 'Oberer Muschelkalk' },
			petrography: { lithology: 'limestone', description: 'Limestone, hard, jointed' },
			color: { hex: '#bfc5c9', name: 'Light grey' }
		}
	],
	documents: [
		{
			id: 'D1',
			name: 'BK1042_Schichtenverzeichnis.pdf',
			type: 'pdf',
			language: 'de',
			pages: 3,
			sizeKb: 1240,
			url: '#'
		},
		{
			id: 'D2',
			name: 'BK1042_Kernfoto_Kasten1-4.jpg',
			type: 'image',
			language: '–',
			sizeKb: 3860,
			url: '#'
		},
		{
			id: 'D3',
			name: 'BK1042_Bohrbericht.docx',
			type: 'docx',
			language: 'de',
			pages: 7,
			sizeKb: 410,
			url: '#'
		}
	]
};
