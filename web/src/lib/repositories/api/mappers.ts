import type {
	Borehole,
	BoreholeDocument,
	BoreholeLayer,
	BoreholeSummary,
	DocumentType
} from '#lib/domain/borehole.ts';
import { parseComposition } from '#lib/din4023/index.ts';
import type { ApiBorehole, ApiBoreholeLayer, ApiDocument } from './api-types';

const num = (value: string | number | null | undefined): number | null =>
	value === null || value === undefined ? null : Number(value);

/** The API stores stratigraphy as one string, e.g. "km1" or "km1 Gipskeuper". */
function toStratigraphy(value: string | null): BoreholeLayer['stratigraphy'] {
	const [code = '', ...name] = (value ?? '').trim().split(/\s+/);
	return { code, name: name.join(' ') };
}

function toColor(value: string | null): BoreholeLayer['color'] {
	const raw = (value ?? '').trim();
	return /^#[0-9a-f]{3,8}$/i.test(raw)
		? { hex: raw, name: raw }
		: { hex: '#9ca3af', name: raw || 'Unknown' };
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

function toDocumentType(filename: string): DocumentType {
	const ext = filename.split('.').pop()?.toLowerCase();
	if (ext === 'pdf') return 'pdf';
	if (ext === 'docx' || ext === 'doc') return 'docx';
	return 'image';
}

export function toDocument(doc: ApiDocument): BoreholeDocument {
	return {
		id: doc.id,
		name: doc.original_filename,
		type: toDocumentType(doc.original_filename),
		status: doc.status,
		language: doc.source_country ?? undefined,
		// TODO: replace with a download endpoint once the API exposes one.
		url: doc.storage_path
	};
}

function toLocation(location: ApiBorehole['location']): Borehole['location'] {
	return location ? { lon: location.coordinates[0], lat: location.coordinates[1] } : null;
}

export function toSummary(b: ApiBorehole): BoreholeSummary {
	return {
		id: b.id,
		name: b.name,
		date: b.drilled_at ?? undefined,
		elevation: num(b.elevation_m),
		totalDepth: num(b.total_depth_m) ?? 0,
		location: toLocation(b.location),
		verified: b.verified
	};
}

export function toBorehole(b: ApiBorehole): Borehole {
	const layers = (b.borehole_layers ?? []).map(toLayer);
	return {
		...toSummary(b),
		// Fall back to the deepest layer when the total depth was not extracted.
		totalDepth: num(b.total_depth_m) ?? Math.max(0, ...layers.map((l) => l.endDepth)),
		externalId: b.external_id ?? undefined,
		endDate: b.end_date ?? undefined,
		cause: b.purpose ?? undefined,
		groundwaterLevel: num(b.groundwater_level_m) ?? undefined,
		drillingMethod: b.drilling_method ?? undefined,
		layers,
		documents: b.document ? [toDocument(b.document)] : []
	};
}
