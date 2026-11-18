/**
 * Predicts the ground between neighbouring boreholes of a section by correlating their layers
 * (ADR-0004): the layer sequences of each neighbouring pair are aligned so that layers with the
 * same main material are connected, keeping their order (connections never cross). Layers without
 * a partner pinch out halfway between the two boreholes. Connections steeper than MAX_SLOPE_DEG
 * (at the map's 10× vertical exaggeration) are not made.
 *
 * Geometry is returned per neighbouring pair in pair coordinates: `t` runs from 0 at the left
 * borehole to 1 at the right one, depth is in metres below each borehole's start. The renderer
 * maps `t` to the space between the two columns.
 */
import { VERTICAL_EXAGGERATION, columnSegments, type ColumnSegment } from './column-model.ts';
import type { SectionBorehole } from './section.ts';

/** Where unmatched layers pinch out, as `t` between the two boreholes. */
const PINCH_T = 0.5;

/**
 * Steepest a connected layer's top and bottom may be, measured at the map's vertical
 * exaggeration (VERTICAL_EXAGGERATION): at 45° and 10×, depth may change by at most a tenth of the
 * distance between the boreholes.
 */
export const MAX_SLOPE_DEG = 45;
const MAX_DEPTH_CHANGE_PER_M = Math.tan((MAX_SLOPE_DEG * Math.PI) / 180) / VERTICAL_EXAGGERATION;

/** A predicted area between two neighbouring boreholes. */
export interface Band {
	/** `matched`: a layer connected to its partner; `pinch`: a layer wedging out. */
	kind: 'matched' | 'pinch';
	/** The layer(s) it continues: the left and/or the right borehole's segment. */
	left?: ColumnSegment;
	right?: ColumnSegment;
	/** Outline as `[t, depth]` points. */
	polygon: [number, number][];
}

export interface PairCorrelation {
	left: SectionBorehole;
	right: SectionBorehole;
	bands: Band[];
}

/** Two segments may be connected only if both have a known, identical main material. */
function sameMaterial(a: ColumnSegment, b: ColumnSegment): boolean {
	return a.material !== undefined && a.material === b.material;
}

const end = (segments: ColumnSegment[]) => segments.at(-1)?.bottom ?? 0;
const mid = (s: ColumnSegment) => (s.top + s.bottom) / 2;

/** Whether a layer's top and bottom stay within the slope limit over `distance` metres. */
function withinSlope(a: ColumnSegment, b: ColumnSegment, distance: number): boolean {
	const limit = distance * MAX_DEPTH_CHANGE_PER_M + 1e-9;
	return Math.abs(a.top - b.top) <= limit && Math.abs(a.bottom - b.bottom) <= limit;
}

/**
 * Aligns two segment sequences (Needleman–Wunsch): a match of the same material scores
 * `2 − depth difference / deeper end` (always above 1, so matching beats skipping), skipping a
 * segment scores 0. Segments that start below the other borehole's end have nothing to connect to
 * and are never matched, nor are layers whose top or bottom would be steeper than MAX_SLOPE_DEG
 * over `distance` (metres between the boreholes along the line). Returns the matched index pairs.
 */
export function alignSegments(
	a: ColumnSegment[],
	b: ColumnSegment[],
	distance: number
): [number, number][] {
	const endA = end(a);
	const endB = end(b);
	const deeper = Math.max(endA, endB, 1e-9);
	const score = (i: number, j: number) =>
		sameMaterial(a[i], b[j]) &&
		a[i].top < endB &&
		b[j].top < endA &&
		withinSlope(a[i], b[j], distance)
			? 2 - Math.abs(mid(a[i]) - mid(b[j])) / deeper
			: -Infinity;

	// best[i][j]: best score aligning a[i..] with b[j..]; filled from the end.
	const best = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
	for (let i = a.length - 1; i >= 0; i--) {
		for (let j = b.length - 1; j >= 0; j--) {
			best[i][j] = Math.max(best[i + 1][j], best[i][j + 1], score(i, j) + best[i + 1][j + 1]);
		}
	}
	const pairs: [number, number][] = [];
	let i = 0;
	let j = 0;
	while (i < a.length && j < b.length) {
		const match = score(i, j) + best[i + 1][j + 1];
		if (match >= best[i + 1][j] && match >= best[i][j + 1] && match > -Infinity) {
			pairs.push([i, j]);
			i++;
			j++;
		} else if (best[i + 1][j] >= best[i][j + 1]) i++;
		else j++;
	}
	return pairs;
}

/**
 * Bands between two neighbouring boreholes. The matched pairs split both stacks into gaps of
 * unmatched layers; every gap has one pinch point at `t = PINCH_T`. Unmatched layers fan into it
 * as wedges, and the matched bands bend through the pinch points above and below them, so the
 * bands fill the space without overlaps. The gap at the top pinches out at the surface, the one
 * at the bottom at the mean end depth (layers below the shallower borehole wedge out there).
 */
export function correlatePair(left: SectionBorehole, right: SectionBorehole): PairCorrelation {
	const a = columnSegments(left.column);
	const b = columnSegments(right.column);
	const pairs = alignSegments(a, b, Math.abs(right.along - left.along));

	// Pinch depth of every gap: gap g lies between pairs[g - 1] and pairs[g].
	const pinch: number[] = [];
	const gaps: { aFrom: number; aTo: number; bFrom: number; bTo: number }[] = [];
	for (let g = 0; g <= pairs.length; g++) {
		const previous = pairs[g - 1];
		const next = pairs[g];
		const gap = {
			aFrom: previous ? previous[0] + 1 : 0,
			aTo: next ? next[0] : a.length,
			bFrom: previous ? previous[1] + 1 : 0,
			bTo: next ? next[1] : b.length
		};
		gaps.push(gap);
		// Depth range of each stack in this gap.
		const aTop = previous ? a[previous[0]].bottom : (a[0]?.top ?? 0);
		const bTop = previous ? b[previous[1]].bottom : (b[0]?.top ?? 0);
		const aBottom = next ? a[next[0]].top : end(a);
		const bBottom = next ? b[next[1]].top : end(b);
		const unmatched = gap.aTo > gap.aFrom || gap.bTo > gap.bFrom;
		if (unmatched && !previous && next) pinch.push((aTop + bTop) / 2);
		else if (unmatched && previous && !next) pinch.push((aBottom + bBottom) / 2);
		else pinch.push((aTop + bTop + aBottom + bBottom) / 4);
	}

	const bands: Band[] = [];
	pairs.forEach(([i, j], k) => {
		bands.push({
			kind: 'matched',
			left: a[i],
			right: b[j],
			polygon: [
				[0, a[i].top],
				[PINCH_T, pinch[k]],
				[1, b[j].top],
				[1, b[j].bottom],
				[PINCH_T, pinch[k + 1]],
				[0, a[i].bottom]
			]
		});
	});
	gaps.forEach((gap, g) => {
		for (let i = gap.aFrom; i < gap.aTo; i++) {
			bands.push({
				kind: 'pinch',
				left: a[i],
				polygon: [
					[0, a[i].top],
					[PINCH_T, pinch[g]],
					[0, a[i].bottom]
				]
			});
		}
		for (let j = gap.bFrom; j < gap.bTo; j++) {
			bands.push({
				kind: 'pinch',
				right: b[j],
				polygon: [
					[1, b[j].top],
					[PINCH_T, pinch[g]],
					[1, b[j].bottom]
				]
			});
		}
	});
	return { left, right, bands };
}

/** Correlations of all neighbouring pairs of a section's boreholes (ordered along the line). */
export function correlateSection(boreholes: SectionBorehole[]): PairCorrelation[] {
	const result: PairCorrelation[] = [];
	for (let k = 1; k < boreholes.length; k++)
		result.push(correlatePair(boreholes[k - 1], boreholes[k]));
	return result;
}
