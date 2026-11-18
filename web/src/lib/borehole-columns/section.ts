/**
 * A section (side view) along a straight line on the map: which boreholes lie within the corridor
 * around the line, and where along the line they are. Independent of any renderer (ADR-0004).
 */
import type { BBox, BoreholeColumnData } from '#lib/domain/borehole.ts';

/** Boreholes up to this distance from the line (in metres, either side and beyond its ends) count. */
export const CORRIDOR_M = 100;

const METRES_PER_DEGREE = 111_320;

/** A section line from `start` to `end`, each `[lon, lat]` in WGS84. */
export interface SectionLine {
	start: [number, number];
	end: [number, number];
}

export interface SectionBorehole {
	column: BoreholeColumnData;
	/** Distance along the line in metres, from 0 at the start to the line's length. */
	along: number;
	/** Distance from the line in metres (perpendicular, or to the nearer end beyond it). */
	offset: number;
}

export interface Section {
	line: SectionLine;
	/** Length of the line in metres. */
	length: number;
	/** Boreholes in the corridor, ordered along the line. */
	boreholes: SectionBorehole[];
}

/**
 * A local metric frame around the line's middle: an equirectangular projection, accurate to far
 * below a metre over a few kilometres. Returns metres east and north of the start.
 */
function frame(line: SectionLine) {
	const midLat = (line.start[1] + line.end[1]) / 2;
	const metresPerLon = METRES_PER_DEGREE * Math.cos((midLat * Math.PI) / 180);
	return ([lon, lat]: [number, number]): [number, number] => [
		(lon - line.start[0]) * metresPerLon,
		(lat - line.start[1]) * METRES_PER_DEGREE
	];
}

/** Length of the line in metres. */
export function lineLength(line: SectionLine): number {
	const [x, y] = frame(line)(line.end);
	return Math.hypot(x, y);
}

/**
 * Where a point lies relative to the line: `along` is its projection clamped to the line (the
 * corridor is rounded at the ends), `offset` its distance to the line segment.
 */
export function project(line: SectionLine, point: [number, number]) {
	const toMetres = frame(line);
	const [ex, ey] = toMetres(line.end);
	const [px, py] = toMetres(point);
	const length = Math.hypot(ex, ey);
	if (length === 0) return { along: 0, offset: Math.hypot(px, py) };
	const t = (px * ex + py * ey) / length;
	const along = Math.min(length, Math.max(0, t));
	const offset = Math.hypot(px - (ex * along) / length, py - (ey * along) / length);
	return { along, offset };
}

/** The boreholes of `columns` within the corridor, ordered along the line. */
export function buildSection(line: SectionLine, columns: BoreholeColumnData[]): Section {
	const boreholes = columns
		.map((column) => ({ column, ...project(line, [column.lon, column.lat]) }))
		.filter((b) => b.offset <= CORRIDOR_M)
		.sort((a, b) => a.along - b.along || a.column.name.localeCompare(b.column.name));
	return { line, length: lineLength(line), boreholes };
}

/** The area to load boreholes from: the line's bounding box widened by the corridor. */
export function sectionBBox(line: SectionLine): BBox {
	const midLat = (line.start[1] + line.end[1]) / 2;
	const dLat = CORRIDOR_M / METRES_PER_DEGREE;
	const dLon = dLat / Math.max(Math.cos((midLat * Math.PI) / 180), 0.01);
	return [
		Math.min(line.start[0], line.end[0]) - dLon,
		Math.min(line.start[1], line.end[1]) - dLat,
		Math.max(line.start[0], line.end[0]) + dLon,
		Math.max(line.start[1], line.end[1]) + dLat
	];
}

/**
 * The corridor as a closed ring of `[lon, lat]` for drawing on the map: a rectangle along the line
 * with half circles around both ends.
 */
export function corridorRing(line: SectionLine, steps = 16): [number, number][] {
	const midLat = (line.start[1] + line.end[1]) / 2;
	const metresPerLon = METRES_PER_DEGREE * Math.cos((midLat * Math.PI) / 180);
	const [ex, ey] = frame(line)(line.end);
	const heading = Math.atan2(ey, ex);
	const toLonLat = (x: number, y: number): [number, number] => [
		line.start[0] + x / metresPerLon,
		line.start[1] + y / METRES_PER_DEGREE
	];
	const ring: [number, number][] = [];
	// Around the end, from its right side to its left, then around the start back again.
	for (const [cx, cy, from] of [
		[ex, ey, heading - Math.PI / 2],
		[0, 0, heading + Math.PI / 2]
	] as const) {
		for (let i = 0; i <= steps; i++) {
			const angle = from + (Math.PI * i) / steps;
			ring.push(toLonLat(cx + CORRIDOR_M * Math.cos(angle), cy + CORRIDOR_M * Math.sin(angle)));
		}
	}
	ring.push(ring[0]);
	return ring;
}

/** URL value of a section line: `lon1,lat1,lon2,lat2` with 6 decimals (about 0.1 m). */
export function formatSectionParam(line: SectionLine): string {
	return [...line.start, ...line.end].map((v) => v.toFixed(6)).join(',');
}

/** Parses `formatSectionParam`'s output; `undefined` if the value is not four valid coordinates. */
export function parseSectionParam(value: string | null): SectionLine | undefined {
	const parts = (value ?? '').split(',').map(Number);
	if (parts.length !== 4 || !parts.every(Number.isFinite)) return undefined;
	const [lon1, lat1, lon2, lat2] = parts;
	const valid = (lon: number, lat: number) => Math.abs(lon) <= 180 && Math.abs(lat) <= 90;
	if (!valid(lon1, lat1) || !valid(lon2, lat2)) return undefined;
	return { start: [lon1, lat1], end: [lon2, lat2] };
}
