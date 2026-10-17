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
	| 'marl'
	/** Petrography that could not be mapped to a known class. */
	| 'unknown';

export interface BoreholeLayer {
	/** Database id (uuid); use for keys and selection, not for display. */
	id: string;
	/** 1-based order of the layer within its borehole (1, 2, 3, ...); shown to users. */
	position: number;
	/** Depth below the borehole start in metres. */
	startDepth: number;
	endDepth: number;
	stratigraphy: { code: string; name: string };
	petrography: { lithology: LithologyKey; description: string };
	/** Layer colour as shown on the original log. */
	color: { hex: string; name: string };
}

export type DocumentType = 'pdf' | 'image' | 'docx';

export type DocumentStatus = 'pending' | 'processing' | 'extracted' | 'failed' | 'reviewed';

export interface BoreholeDocument {
	id: string;
	name: string;
	type: DocumentType;
	status: DocumentStatus;
	/** Source country / language of the log, if known. */
	language?: string;
	pages?: number;
	sizeKb?: number;
	/** Link to the original file. */
	url: string;
}

export interface Borehole {
	id: string;
	name: string;
	externalId?: string;
	/** ISO date (YYYY-MM-DD). */
	date?: string;
	endDate?: string;
	/** Purpose of the boring. */
	cause?: string;
	/** Height of the borehole start in metres above sea level (m ü. NN). */
	elevation: number | null;
	totalDepth: number;
	groundwaterLevel?: number;
	drillingMethod?: string;
	client?: string;
	location: { lat: number; lon: number; place?: string } | null;
	verified: boolean;
	layers: BoreholeLayer[];
	documents: BoreholeDocument[];
}

/** Lightweight representation for lists and the map. */
export type BoreholeSummary = Pick<
	Borehole,
	'id' | 'name' | 'date' | 'elevation' | 'totalDepth' | 'location' | 'verified'
>;

export interface BoreholeFilter {
	/** Matches name, external id and place. */
	search?: string;
	verified?: boolean;
	/** ISO dates (YYYY-MM-DD), inclusive, compared with the drilling date. */
	drilledFrom?: string;
	drilledTo?: string;
	minDepth?: number;
	maxDepth?: number;
}

export type BoreholeSortField = 'name' | 'date' | 'totalDepth';

export interface BoreholeSort {
	field: BoreholeSortField;
	direction: 'asc' | 'desc';
}

export interface ListParams extends BoreholeFilter {
	sort?: BoreholeSort;
	limit?: number;
	offset?: number;
}

export interface Page<T> {
	items: T[];
	/** Total number of matches across all pages. */
	total: number;
}

export interface SearchQuery {
	q: string;
	limit?: number;
	offset?: number;
}

export interface SearchHit {
	borehole: BoreholeSummary;
	/** Relevance, higher is better. */
	score: number;
	/** Matching text excerpt, if the backend provides one. */
	snippet?: string;
}
