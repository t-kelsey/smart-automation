/** Wire format of the Phoenix API (snake_case, mirrors the Ecto schemas in api/lib/api/boreholes). */

export interface ApiGeoPoint {
	type: 'Point';
	/** [lon, lat] */
	coordinates: [number, number];
}

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
}

export interface ApiDocument {
	id: string;
	original_filename: string;
	storage_path: string;
	source_country: string | null;
	status: 'pending' | 'processing' | 'extracted' | 'failed' | 'reviewed';
}

export interface ApiBorehole {
	id: string;
	name: string;
	external_id: string | null;
	purpose: string | null;
	drilling_method: string | null;
	drilled_at: string | null;
	end_date: string | null;
	location: ApiGeoPoint | null;
	total_depth_m: Decimal | null;
	borehole_length_m: Decimal | null;
	elevation_m: Decimal | null;
	groundwater_level_m: Decimal | null;
	verified: boolean;
	document?: ApiDocument | null;
	borehole_layers?: ApiBoreholeLayer[];
}

/** Expected response envelope: `{ data: ... }` for GET /api/boreholes/:id, `{ data: [...], total }` for the list. */
export interface ApiItemResponse<T> {
	data: T;
}
export interface ApiListResponse<T> {
	data: T[];
	total: number;
}

/** Item of `GET /api/search?q=&limit=&offset=` → `{ data: [ApiSearchHit], total }`. */
export interface ApiSearchHit {
	borehole: ApiBorehole;
	score: number;
	snippet: string | null;
}
