import {
	BOREHOLE_FIELDS,
	type Borehole,
	type BoreholeColumnData,
	type BoreholeDocument,
	type BoreholeField,
	type BoreholeLayer,
	type BoreholeSummary,
	type DocumentDetail,
	type DocumentType,
	type FieldEdit,
	type FieldFlag,
	type SourceRef,
	type StoredDocument,
	type MapPoint
} from '#lib/domain/borehole.ts';
import { colorKeyByName, dinColors, parseComposition } from '#lib/din4023/index.ts';
import type {
	ApiBorehole,
	ApiBoreholeDetail,
	ApiBoreholeLayer,
	ApiBoreholeDocument,
	ApiColumnFeature,
	ApiDocument,
	ApiDocumentDetail,
	ApiEdit,
	ApiFeature,
	ApiFlag,
	ApiGeoPoint,
	ApiPointFeature,
	ApiSource
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

const text = (value: string | number | null | undefined): string | null =>
	value === null || value === undefined ? null : String(value);

export const toSource = (source: ApiSource | null | undefined): SourceRef | null =>
	source ? { documentId: source.document_id, page: source.page, box: source.box ?? null } : null;

const toSources = (sources: Record<string, ApiSource | null> | null | undefined) =>
	Object.fromEntries(
		Object.entries(sources ?? {}).flatMap(([field, source]) =>
			source ? [[field, toSource(source)!]] : []
		)
	);

const toFlag = (f: ApiFlag): FieldFlag => ({
	id: f.id,
	field: f.field,
	layerId: f.layer_id,
	severity: f.severity,
	message: f.message,
	origin: f.origin,
	code: f.code,
	resolvedAt: f.resolved_at,
	resolvedBy: f.resolved_by,
	suggestion: f.suggestion ?? null
});

const toEdit = (e: ApiEdit): FieldEdit => ({
	id: e.id,
	field: e.field,
	layerId: e.layer_id,
	oldValue: e.old_value,
	newValue: e.new_value,
	source: e.source,
	reason: e.reason,
	createdAt: e.inserted_at
});

export function toLayer(layer: ApiBoreholeLayer): BoreholeLayer {
	const original = layer.metadata?.petrography_original;
	return {
		id: layer.id,
		position: layer.position,
		startDepth: Number(layer.depth_from_m),
		endDepth: Number(layer.depth_to_m),
		stratigraphy: toStratigraphy(layer.stratigraphy),
		petrography: {
			composition: parseComposition(layer.petrography),
			description: layer.petrography ?? layer.raw_text ?? '',
			original: !layer.petrography && typeof original === 'string' ? original : undefined
		},
		color: toColor(layer.color),
		stored: {
			depth_from_m: text(layer.depth_from_m),
			depth_to_m: text(layer.depth_to_m),
			stratigraphy: layer.stratigraphy,
			petrography: layer.petrography,
			color: layer.color
		},
		source: toSource(layer.source),
		sources: toSources(layer.sources)
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
		verified: b.verified,
		openFlagCount: b.open_flag_count ?? 0
	};
}

export const featureToSummary = ({ properties, geometry }: ApiFeature): BoreholeSummary =>
	toSummary(properties, geometry);

export function featureToMapPoint({ properties, geometry }: ApiPointFeature): MapPoint[] {
	if (!geometry) return [];
	const [lon, lat] = geometry.coordinates;
	return [{ id: properties.id, name: properties.name, verified: properties.verified, lon, lat }];
}

export function featureToColumn({ properties, geometry }: ApiColumnFeature): BoreholeColumnData[] {
	if (!geometry) return [];
	const [lon, lat] = geometry.coordinates;
	return [
		{
			id: properties.id,
			name: properties.name,
			verified: properties.verified,
			lon,
			lat,
			totalDepth: num(properties.total_depth_m),
			layers: properties.layers.map((layer) =>
				toLayer({ ...layer, stratigraphy: null, raw_text: null, metadata: {} })
			)
		}
	];
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
		verifiedAt: b.verified_at ?? null,
		layers,
		documents: b.documents.map((doc) => toBoreholeDocument(doc, baseUrl)),
		stored: Object.fromEntries(
			BOREHOLE_FIELDS.map(({ field }) => [field, text(b[field])])
		) as Record<BoreholeField, string | null>,
		sources: toSources(b.sources),
		sourceCoordinates:
			b.source_x != null && b.source_y != null && b.source_epsg != null
				? { x: b.source_x, y: b.source_y, epsg: b.source_epsg }
				: null,
		flags: (b.flags ?? []).map(toFlag),
		edits: (b.edits ?? []).map(toEdit)
	};
}
