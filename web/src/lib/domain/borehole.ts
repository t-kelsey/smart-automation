import type { Composition } from '#lib/din4023/index.ts';

/** Where a value is written in a source document (ADR-0006). */
export interface SourceRef {
	documentId: string;
	/** 1-based page number. */
	page: number;
	/** `[x0, y0, x1, y1]` in 0–1 of the page, origin top left; `null` when only the page is known. */
	box: [number, number, number, number] | null;
}

/** A doubt about one value, raised by a plausibility rule of the API or by the validator. */
export interface FieldFlag {
	id: string;
	/** API field name (`elevation_m`, `depth_to_m`, …), `location` for the coordinates. */
	field: string;
	/** Set for a layer field. */
	layerId: string | null;
	severity: 'warning' | 'error';
	message: string;
	origin: 'rule' | 'validator';
	/** Rule id; `null` for validator flags. */
	code: string | null;
	/** ISO timestamp; `null` while the flag is open. */
	resolvedAt: string | null;
	resolvedBy: 'human' | 'rule' | null;
	/** Value the validator proposes (any JSON, e.g. `{x, y, epsg}` for `location`); `null` if none. */
	suggestion: unknown;
}

/** One change of a value; the history is append-only, a revert is a new edit. */
export interface FieldEdit {
	id: string;
	/** Like `FieldFlag.field`; `layer` for creating (old value `null`) or deleting a whole layer. */
	field: string;
	layerId: string | null;
	oldValue: unknown;
	newValue: unknown;
	source: 'validator' | 'human';
	reason: string | null;
	/** ISO timestamp. */
	createdAt: string;
}

/** Borehole fields the review page edits one by one, by API name. Coordinates are edited apart. */
export const BOREHOLE_FIELDS = [
	{ field: 'name', label: 'Name', type: 'text' },
	{ field: 'external_id', label: 'External id', type: 'text' },
	{ field: 'drilled_at', label: 'Date', type: 'date' },
	{ field: 'end_date', label: 'End date', type: 'date' },
	{ field: 'purpose', label: 'Boring cause', type: 'text' },
	{ field: 'client', label: 'Client', type: 'text' },
	{ field: 'drilling_method', label: 'Drilling method', type: 'text' },
	{ field: 'place', label: 'Place', type: 'text' },
	{ field: 'elevation_m', label: 'Height o. NN (m)', type: 'number' },
	{ field: 'total_depth_m', label: 'Total depth (m)', type: 'number' },
	{ field: 'groundwater_level_m', label: 'Groundwater (m)', type: 'number' }
] as const;

export type BoreholeField = (typeof BOREHOLE_FIELDS)[number]['field'];

/** Layer fields the review page edits, by API name. */
export type LayerField = 'depth_from_m' | 'depth_to_m' | 'stratigraphy' | 'petrography' | 'color';

/** Changes for `PATCH`: field values, and the coordinates as `x`/`y` in the system `epsg`. */
export type BoreholeChanges = Partial<Record<BoreholeField, string | number | null>> & {
	x?: number;
	y?: number;
	epsg?: number;
};

export type LayerChanges = Partial<Record<LayerField, string | number | null>>;

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
		/** The extracted text when it was no DIN 4023 term and petrography was left empty. */
		original?: string;
	};
	/** Layer colour as shown on the original log. */
	color: { hex: string; name: string };
	/** Values as stored, by API name; what the review page edits. */
	stored: Record<LayerField, string | null>;
	/** Box of the whole layer, and of single fields where the validator found them. */
	source: SourceRef | null;
	sources: Partial<Record<LayerField, SourceRef>>;
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
 * ADR-0001); `additional` files carry more information.
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
	/** ISO timestamp of the release; `null` while not verified. */
	verifiedAt: string | null;
	openFlagCount: number;
	layers: BoreholeLayer[];
	documents: BoreholeDocument[];
	/** Values as stored, by API name; what the review page edits. */
	stored: Record<BoreholeField, string | null>;
	/** Where each field is written, by API name (`location` for the coordinates). */
	sources: Record<string, SourceRef>;
	/** The coordinates as written in the document (source CRS), if known. */
	sourceCoordinates: { x: number; y: number; epsg: number } | null;
	/** Open flags first. */
	flags: FieldFlag[];
	/** Newest first. */
	edits: FieldEdit[];
}

/** Lightweight representation for lists and the map. */
export type BoreholeSummary = Pick<
	Borehole,
	'id' | 'name' | 'date' | 'elevation' | 'totalDepth' | 'location' | 'verified' | 'openFlagCount'
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

export type BoreholeSortField = 'name' | 'date' | 'totalDepth' | 'openFlags';

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

/** A search in the query language of the API (see `docs/api-reference.md`). */
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

/** A completion for the term being typed at the end of a search query. */
export interface SearchCompletion {
	/** The completed value, e.g. a place name or a key like `place:`. */
	value: string;
	/** Where the value comes from. */
	kind: 'key' | 'name' | 'place';
	/** The whole query with the term completed. */
	query: string;
}

export interface SearchPage extends Page<SearchHit> {
	/** Only when nothing was found: an autocorrected query, if the backend has one. */
	suggestion?: string;
}
