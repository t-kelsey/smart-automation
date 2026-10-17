/**
 * Wire format of the Phoenix API, as documented in docs/api-reference.md and rendered by
 * api/lib/api_web/controllers/borehole_json.ex. The backend is the source of truth (ADR-0023).
 */

export interface ApiGeoPoint {
	type: 'Point';
	/** [lon, lat] */
	coordinates: [number, number];
}

/** Decimals are serialised as strings ("18.3"). */
type Decimal = string | number;

export interface ApiBoreholeLayer {
	id: string;
	position: number;
	depth_from_m: Decimal;
	depth_to_m: Decimal;
	stratigraphy: string | null;
	petrography: string | null;
	color: string | null;
	raw_text: string | null;
	metadata: Record<string, unknown>;
}

/**
 * `storage_path` and `raw_extraction` are never exposed (ADR-0014). When `has_file` is true the
 * file is served by `GET /api/documents/:id/file` (ADR-0026).
 */
export interface ApiDocument {
	id: string;
	original_filename: string;
	mime_type: string | null;
	source_country: string | null;
	status: 'pending' | 'processing' | 'extracted' | 'failed' | 'reviewed';
	page_count: number | null;
	size_bytes: number | null;
	has_file: boolean;
}

/** Borehole columns without `location`; the properties of a GeoJSON feature. */
export interface ApiBorehole {
	id: string;
	name: string;
	external_id: string | null;
	purpose: string | null;
	place: string | null;
	client: string | null;
	drilling_method: string | null;
	drilled_at: string | null;
	end_date: string | null;
	source_coordinate_system: string | null;
	source_coordinate_raw: string | null;
	total_depth_m: Decimal | null;
	borehole_length_m: Decimal | null;
	elevation_m: Decimal | null;
	groundwater_level_m: Decimal | null;
	verified: boolean;
	metadata: Record<string, unknown>;
	inserted_at: string;
	updated_at: string;
}

/** `GET /api/boreholes/:id` → `{ data: ApiBoreholeDetail }`. */
export interface ApiBoreholeDetail extends ApiBorehole {
	location: ApiGeoPoint | null;
	layers: ApiBoreholeLayer[];
	documents: ApiDocument[];
}

/** `GET /api/documents/:id` → `{ data: ApiDocumentDetail }`. */
export interface ApiDocumentDetail extends ApiDocument {
	boreholes: { id: string; name: string }[];
}

export interface ApiItemResponse<T> {
	data: T;
}

export interface ApiFeature {
	type: 'Feature';
	/** `null` if the borehole has not been georeferenced. */
	geometry: ApiGeoPoint | null;
	properties: ApiBorehole;
	/** Only on search results (`q` given): relevance and the matching layer text. */
	score?: number;
	snippet?: string | null;
}

/** With `view=points` the properties hold only id, name and verified. */
export interface ApiPointFeature {
	type: 'Feature';
	geometry: ApiGeoPoint | null;
	properties: Pick<ApiBorehole, 'id' | 'name' | 'verified'>;
}

/**
 * `GET /api/boreholes` and `GET /api/boreholes/search`. `total`, `limit` and `offset` are
 * GeoJSON foreign members for paging.
 */
export interface ApiFeatureCollection<F = ApiFeature> {
	type: 'FeatureCollection';
	total: number;
	limit: number | null;
	offset: number;
	features: F[];
}
