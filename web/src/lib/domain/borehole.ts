import type { Composition } from '#lib/din4023/index.ts';

/** Layer of a borehole; soil and rock are described after DIN 4023 (see `#lib/din4023`). */
export interface BoreholeLayer {
	/** Database id (uuid); use for keys and selection, not for display. */
	id: string;
	/** 1-based order of the layer within its borehole (1, 2, 3, ...); shown to users. */
	position: number;
	/** Depth below the borehole start in metres. */
	startDepth: number;
	endDepth: number;
	stratigraphy: { code: string; name: string };
	petrography: {
		/** Structured soil/rock description; `undefined` when the text could not be classified. */
		composition?: Composition;
		/** Description as written on the original log. */
		description: string;
	};
	/** Layer colour as shown on the original log. */
	color: { hex: string; name: string };
}

export type DocumentType = 'pdf' | 'image' | 'docx';

export type DocumentStatus = 'pending' | 'processing' | 'extracted' | 'failed' | 'reviewed';

/** A stored file of a borehole's documentation, independent of the borehole it is shown for. */
export interface StoredDocument {
	id: string;
	name: string;
	type: DocumentType;
	status: DocumentStatus;
	/** Source country / language of the log, if known. */
	language?: string;
	pages?: number;
	sizeKb?: number;
	/** Link to the original file (shown inline; add `?download=1` to save it); absent if no file is stored. */
	url?: string;
}

/**
 * `original` is the one source log a borehole was extracted from (at most one per borehole, see
 * ADR-0028); `additional` files carry more information.
 */
export type DocumentRole = 'original' | 'additional';

/** A document as linked to one borehole. */
export interface BoreholeDocument extends StoredDocument {
	role: DocumentRole;
}

/** A document with the boreholes it is linked to. */
export interface DocumentDetail extends StoredDocument {
	boreholes: { id: string; name: string }[];
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
	/** Depth of the borehole in metres; `null` if neither the log nor its layers state it. */
	totalDepth: number | null;
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

/** Minimal data to place a borehole on the map; details are loaded on demand. */
export interface MapPoint {
	id: string;
	name: string;
	lon: number;
	lat: number;
	verified: boolean;
}

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
	/** Relevance, higher is better; absent if the backend does not rank hits. */
	score?: number;
	/** Matching text excerpt, if the backend provides one. */
	snippet?: string;
}
