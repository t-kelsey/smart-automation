/** Lithology classes that have a hatch pattern in the cross-section drawing. */
export type LithologyKey =
	| 'topsoil'
	| 'fill'
	| 'clay'
	| 'silt'
	| 'sand'
	| 'gravel'
	| 'sandstone'
	| 'claystone'
	| 'limestone'
	| 'marl';

export interface BoreholeLayer {
	id: string;
	/** Depth below the borehole start in metres. */
	startDepth: number;
	endDepth: number;
	stratigraphy: { code: string; name: string };
	petrography: { lithology: LithologyKey; description: string };
	/** Layer colour as shown on the original log. */
	color: { hex: string; name: string };
}

export interface BoreholeDocument {
	id: string;
	name: string;
	type: 'pdf' | 'image' | 'docx';
	language: string;
	pages?: number;
	sizeKb: number;
	/** Link to the original file. */
	url: string;
}

export interface Borehole {
	id: string;
	name: string;
	date: string;
	cause: string;
	/** Height of the borehole start in metres above sea level (m ü. NN). */
	elevation: number;
	totalDepth: number;
	drillingMethod: string;
	client: string;
	location: { lat: number; lon: number; place: string };
	layers: BoreholeLayer[];
	documents: BoreholeDocument[];
}
