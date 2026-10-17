import type {
	Borehole,
	BoreholeDocument,
	BoreholeLayer,
	BoreholeSummary,
	DocumentDetail,
	DocumentType,
	StoredDocument,
	MapPoint
} from '#lib/domain/borehole.ts';
import { colorKeyByName, dinColors, parseComposition } from '#lib/din4023/index.ts';
import type {
	ApiBorehole,
	ApiBoreholeDetail,
	ApiBoreholeLayer,
	ApiBoreholeDocument,
	ApiDocument,
	ApiDocumentDetail,
	ApiFeature,
	ApiGeoPoint,
	ApiPointFeature
} from './api-types';

const num = (value: string | number | null | undefined): number | null =>
	value === null || value === undefined ? null : Number(value);

/**
 * The API stores stratigraphy as one free-text string: an abbreviation ("km1"), a name
 * ("Neuenburg-Formation") or both ("km1 Gipskeuper"). Short tokens are treated as codes.
 */
export function toStratigraphy(value: string | null): BoreholeLayer['stratigraphy'] {
	const text = (value ?? '').trim();
	if (!text) return { code: '', name: '' };
	const [first, ...rest] = text.split(/\s+/);
	if (first.length <= 5 && !first.includes('-')) return { code: first, name: rest.join(' ') };
	return { code: '', name: text };
}

/** Colour as written on the log: hex, or a German DIN 4023 colour name such as "grau". */
export function toColor(value: string | null): BoreholeLayer['color'] {
	const raw = (value ?? '').trim();
	if (/^#[0-9a-f]{3,8}$/i.test(raw)) return { hex: raw, name: raw };
	const key = colorKeyByName[raw.toLowerCase()];
	if (key) return { hex: dinColors[key].hex, name: dinColors[key].name.en };
	return { hex: '#9ca3af', name: raw || 'Unknown' };
}

export function toLayer(layer: ApiBoreholeLayer): BoreholeLayer {
	return {
		id: layer.id,
		position: layer.position,
		startDepth: Number(layer.depth_from_m),
		endDepth: Number(layer.depth_to_m),
		stratigraphy: toStratigraphy(layer.stratigraphy),
		petrography: {
			composition: parseComposition(layer.petrography),
			description: layer.petrography ?? layer.raw_text ?? ''
		},
		color: toColor(layer.color)
	};
}

function toDocumentType(mimeType: string | null, filename: string): DocumentType {
	if (mimeType === 'application/pdf') return 'pdf';
	if (mimeType?.startsWith('image/')) return 'image';
	if (mimeType?.includes('wordprocessingml') || mimeType === 'application/msword') return 'docx';
	const ext = filename.split('.').pop()?.toLowerCase();
	if (ext === 'pdf') return 'pdf';
	if (ext === 'docx' || ext === 'doc') return 'docx';
	return 'image';
}

function toBoreholeDocument(doc: ApiBoreholeDocument, baseUrl: string): BoreholeDocument {
	return { ...toDocument(doc, baseUrl), role: doc.role };
}

export function toDocumentDetail(doc: ApiDocumentDetail, baseUrl: string): DocumentDetail {
	return { ...toDocument(doc, baseUrl), boreholes: doc.boreholes };
}

export function toDocument(doc: ApiDocument, baseUrl: string): StoredDocument {
	return {
		id: doc.id,
		name: doc.original_filename,
		type: toDocumentType(doc.mime_type, doc.original_filename),
		status: doc.status,
		language: doc.source_country ?? undefined,
		pages: doc.page_count ?? undefined,
		sizeKb: doc.size_bytes === null ? undefined : Math.round(doc.size_bytes / 1024),
		url: doc.has_file ? `${baseUrl}/documents/${encodeURIComponent(doc.id)}/file` : undefined
	};
}

function toLocation(geometry: ApiGeoPoint | null, place: string | null): Borehole['location'] {
	if (!geometry) return null;
	return { lon: geometry.coordinates[0], lat: geometry.coordinates[1], place: place ?? undefined };
}

export function toSummary(b: ApiBorehole, geometry: ApiGeoPoint | null): BoreholeSummary {
	return {
		id: b.id,
		name: b.name,
		date: b.drilled_at ?? undefined,
		elevation: num(b.elevation_m),
		totalDepth: num(b.total_depth_m),
		location: toLocation(geometry, b.place),
		verified: b.verified
	};
}

export const featureToSummary = ({ properties, geometry }: ApiFeature): BoreholeSummary =>
	toSummary(properties, geometry);

export function featureToMapPoint({ properties, geometry }: ApiPointFeature): MapPoint[] {
	if (!geometry) return [];
	const [lon, lat] = geometry.coordinates;
	return [{ id: properties.id, name: properties.name, verified: properties.verified, lon, lat }];
}

/** `baseUrl` is the API base, used for links to document files. */
export function toBorehole(b: ApiBoreholeDetail, baseUrl: string): Borehole {
	const layers = b.layers.map(toLayer);
	const deepestLayer = layers.length ? Math.max(...layers.map((l) => l.endDepth)) : null;
	return {
		...toSummary(b, b.location),
		// Fall back to the deepest layer when the total depth was not extracted.
		totalDepth: num(b.total_depth_m) ?? deepestLayer,
		externalId: b.external_id ?? undefined,
		endDate: b.end_date ?? undefined,
		cause: b.purpose ?? undefined,
		client: b.client ?? undefined,
		groundwaterLevel: num(b.groundwater_level_m) ?? undefined,
		drillingMethod: b.drilling_method ?? undefined,
		layers,
		documents: b.documents.map((doc) => toBoreholeDocument(doc, baseUrl))
	};
}
