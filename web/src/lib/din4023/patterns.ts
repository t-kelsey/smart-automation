import type { MaterialKey, PatternDef, Shape } from './types.ts';

/** Hatch patterns after DIN 4023:2023-02 Tables 1 to 3, drawn as tiles in column units. */

const circle = (cx: number, cy: number, r: number, filled = false): Shape => ({
	type: 'circle',
	cx,
	cy,
	r,
	filled
});
const path = (d: string, filled = false, strokeWidth?: number): Shape => ({
	type: 'path',
	d,
	filled,
	strokeWidth
});
const rect = (x: number, y: number, width: number, height: number, filled = false): Shape => ({
	type: 'rect',
	x,
	y,
	width,
	height,
	filled
});
const text = (x: number, y: number, t: string, size: number): Shape => ({
	type: 'text',
	x,
	y,
	text: t,
	size
});

/** Irregular polygon (stones and blocks); `seed` varies the outline. */
const jitter = [1, 0.78, 1.1, 0.85, 1.05, 0.9];
function stone(cx: number, cy: number, r: number, seed = 0): Shape {
	const sides = 5 + (seed % 2);
	const points = Array.from({ length: sides }, (_, i) => {
		const angle = ((i / sides) * 2 + seed * 0.37) * Math.PI;
		const radius = r * jitter[(i + seed) % jitter.length];
		return `${(cx + Math.cos(angle) * radius).toFixed(2)} ${(cy + Math.sin(angle) * radius).toFixed(2)}`;
	});
	return path(`M${points.join(' L')} Z`);
}

const dots = (r: number, points: [number, number][]): Shape[] =>
	points.map(([x, y]) => circle(x, y, r, true));
const dashes = (items: [number, number, number][], strokeWidth?: number): Shape =>
	path(items.map(([x, y, length]) => `M${x} ${y} h${length}`).join(' '), false, strokeWidth);
/** Pair of small domes standing on a baseline: the silt symbol. */
const humps = (items: [number, number][]): Shape =>
	path(
		items
			.map(([x, y]) => `M${x} ${y} a1.5 1.5 0 0 1 3 0 Z M${x + 3.8} ${y} a1.5 1.5 0 0 1 3 0 Z`)
			.join(' '),
		true
	);
const arcs = (r: number, items: [number, number][]): Shape =>
	path(items.map(([x, y]) => `M${x} ${y} a${r} ${r} 0 0 0 ${2 * r} 0`).join(' '));
const iMark = (x: number, y: number, h = 4): Shape =>
	path(`M${x - 1.2} ${y} h2.4 M${x} ${y} v${h} M${x - 1.2} ${y + h} h2.4`);

/** 45° lines rising to the right, one per 7 units; used by loam, debris and till. */
const diagonals = path('M0 7 L7 0 M0 14 L14 0 M7 14 L14 7 M-1 1 L1 -1 M13 15 L15 13');

const tile = (width: number, height: number, ...shapes: (Shape | Shape[])[]): PatternDef => ({
	width,
	height,
	shapes: shapes.flat()
});

export const patterns: Record<MaterialKey, PatternDef> = {
	// Table 1 – soils
	largeBoulder: tile(
		32,
		28,
		stone(7, 7, 4.6, 0),
		stone(23, 9, 4, 1),
		stone(12, 21, 4.4, 2),
		stone(27, 22, 3.6, 3)
	),
	boulder: tile(
		26,
		22,
		stone(5, 5, 3.2, 0),
		stone(17, 4, 2.6, 1),
		stone(10, 14, 3.4, 2),
		stone(21, 16, 2.4, 3),
		stone(3, 18, 1.5, 4)
	),
	cobble: tile(
		22,
		18,
		stone(4, 4, 2.2, 0),
		stone(13, 3, 1.4, 1),
		stone(8, 11, 2.4, 2),
		stone(18, 12, 1.8, 3),
		stone(3, 15, 1.2, 4)
	),
	gravel: tile(
		24,
		20,
		circle(4, 4, 2),
		circle(13, 3, 1.4),
		circle(20, 6, 1.8),
		circle(8, 11, 1.5),
		circle(16, 13, 2.2),
		circle(3, 17, 1.2),
		circle(22, 17, 1.2),
		circle(11, 18, 1)
	),
	coarseGravel: tile(
		26,
		22,
		circle(5, 5, 2.6),
		circle(5, 5, 0.5, true),
		circle(17, 4, 2.6),
		circle(17, 4, 0.5, true),
		circle(10, 15, 2.6),
		circle(10, 15, 0.5, true),
		circle(22, 17, 2.6),
		circle(22, 17, 0.5, true)
	),
	mediumGravel: tile(
		26,
		22,
		circle(5, 5, 2.8),
		circle(17, 4, 2.8),
		circle(10, 15, 2.8),
		circle(22, 17, 2.8)
	),
	fineGravel: tile(
		16,
		14,
		circle(3, 3, 1.3),
		circle(10, 2.5, 1.3),
		circle(14, 8, 1.3),
		circle(6.5, 8.5, 1.3),
		circle(2, 12, 1.3),
		circle(11, 12.5, 1.3)
	),
	sand: tile(
		20,
		20,
		dots(0.7, [
			[3, 3],
			[17, 7],
			[10, 17]
		]),
		dots(1.1, [
			[11, 2],
			[7, 9],
			[18, 18]
		]),
		dots(0.9, [
			[2, 15],
			[14, 13]
		])
	),
	coarseSand: tile(
		22,
		20,
		dots(1.7, [
			[4, 4],
			[15, 3],
			[9, 11],
			[18, 16],
			[3, 16]
		])
	),
	mediumSand: tile(
		16,
		14,
		dots(1, [
			[3, 3],
			[11, 2],
			[7, 8],
			[14, 10],
			[2, 11]
		])
	),
	fineSand: tile(
		12,
		12,
		dots(0.45, [
			[2, 2],
			[8, 3],
			[5, 7],
			[10, 9],
			[1.5, 10],
			[6, 11]
		])
	),
	silt: tile(
		24,
		18,
		humps([
			[2, 5],
			[13, 3],
			[16, 12],
			[3, 15]
		])
	),
	coarseSilt: tile(
		24,
		18,
		humps([
			[2, 5],
			[13, 3],
			[16, 12],
			[3, 15]
		])
	),
	clay: tile(
		26,
		14,
		dashes([
			[2, 2, 12],
			[17, 5, 8],
			[5, 8, 10],
			[19, 11, 6],
			[1, 12, 5]
		])
	),
	peat: tile(
		26,
		14,
		dashes(
			[
				[1, 3, 10],
				[14, 5, 10],
				[4, 9, 8],
				[15, 11, 7]
			],
			1.4
		)
	),
	volcanicAsh: tile(
		24,
		16,
		arcs(2.6, [
			[2, 3],
			[14, 2],
			[8, 10],
			[18, 11]
		])
	),
	lignite: tile(
		32,
		18,
		rect(2, 2, 14, 2.6, true),
		rect(15, 8, 13, 2.6, true),
		rect(5, 14, 14, 2.6, true)
	),

	// Table 2 – rocks (regular arrangement)
	conglomerate: tile(14, 12, circle(3.5, 3, 2.6), circle(10.5, 9, 2.6)),
	breccia: tile(
		16,
		14,
		path('M2 6 L3.6 2.6 L6 5.4 Z M10 3 L13 3.4 L12 6.6 L9.4 6 Z M6 13 L8.6 9.4 L10.4 12.6 Z')
	),
	sandstone: tile(
		14,
		12,
		dots(0.9, [
			[3, 3],
			[10, 9]
		])
	),
	siltstone: tile(
		22,
		12,
		humps([
			[2, 5],
			[12, 11]
		])
	),
	claystone: tile(
		22,
		10,
		dashes([
			[1, 2.5, 10],
			[12, 7.5, 9]
		])
	),
	marlstone: tile(14, 10, path('M1 3 h4 M3 3 v3 M8 8 h4 M10 8 v-3')),
	limestone: tile(16, 10, path('M0 0.4 H16 M0 5.4 H16 M4 0.4 V5.4 M12 5.4 V10')),
	dolomite: tile(18, 10, path('M0 0.4 H18 M0 5.4 H18 M4 5.4 L7 0.4 M13 10 L16 5.4')),
	anhydrite: tile(20, 14, path('M1 7 L5 1 L9 7 Z M11 13 L15 7 L19 13 Z')),
	gypsum: tile(20, 14, path('M1 1 L5 7 L9 1 Z M11 7 L15 13 L19 7 Z')),
	rockSalt: tile(14, 12, rect(2, 2, 3.6, 3.6), rect(9, 8, 3.6, 3.6)),
	tuff: tile(
		20,
		14,
		arcs(3.4, [
			[2, 3],
			[11, 9]
		])
	),
	hardCoal: tile(40, 20, path('M11 9 q3 -3 6 0 t6 0 v4 q-3 -3 -6 0 t-6 0 Z', true)),
	quartzite: tile(
		14,
		10,
		dots(0.6, [
			[2, 1.5],
			[5, 1.5],
			[8, 1.5],
			[2, 8.5],
			[5, 8.5],
			[8, 8.5]
		]),
		path('M10 0.5 h4 l-2 6 Z', true)
	),
	volcanic: tile(16, 12, path('M1.8 3 h4.4 M4 0.8 v4.4 M9.8 9 h4.4 M12 6.8 v4.4')),
	plutonic: tile(16, 14, path('M2 1 L4 4 L6 1 M4 4 V7 M10 8 L12 11 L14 8 M12 11 V14')),
	massiveMetamorphic: tile(12, 8, path('M0.5 1.5 L3 4 L5.5 1.5 M6.5 5.5 L9 8 L11.5 5.5')),
	foliatedMetamorphic: tile(14, 12, path('M1 3 q1.5 -2.4 3 0 t3 0 M8 9 q1.5 -2.4 3 0 t3 0')),

	// Table 3 – geological terms
	topsoil: tile(26, 14, text(2, 9, 'Mu', 6)),
	weatheringLoam: tile(14, 14, diagonals),
	slopeDebris: tile(14, 14, diagonals, stone(5.25, 5.25, 1.8, 0), stone(10, 7.5, 1.6, 1)),
	tillLoam: tile(14, 14, diagonals, circle(5.25, 5.25, 1.5), circle(10, 7.5, 1.5)),
	tillMarl: tile(14, 14, diagonals, circle(5.25, 5.25, 1.3), iMark(10.2, 5.6, 4)),
	loess: tile(
		20,
		20,
		iMark(4, 4, 4),
		iMark(15, 12, 4),
		rect(10, 1.5, 1.4, 5, true),
		rect(2, 13, 1.4, 5, true),
		rect(17.5, 3, 1.4, 4, true)
	),
	loessLoam: tile(
		14,
		14,
		diagonals,
		dots(0.95, [
			[3.5, 3.5],
			[10.5, 10.5]
		])
	),
	marshClay: tile(
		20,
		14,
		dashes([[2, 5, 6]]),
		dots(0.8, [[5, 2]]),
		dashes([[11, 11, 6]]),
		dots(0.8, [[14, 8.5]]),
		dots(0.8, [[1.5, 12]])
	),
	lakeMarl: tile(20, 12, path('M2 3.5 H9 M9 3.5 L7.2 1.8 M11 9.5 H18 M18 9.5 L16.2 7.8')),
	bandedClay: tile(
		20,
		16,
		path('M0 0.4 H20 M0 8.4 H20'),
		dots(0.7, [
			[2, 4.4],
			[6, 4.4],
			[10, 4.4],
			[10, 12.4],
			[14, 12.4],
			[18, 12.4]
		])
	),
	mud: tile(
		20,
		14,
		dashes([[2, 5, 6]]),
		path('M3.4 5 a1.4 1.4 0 0 1 2.8 0 Z', true),
		dashes([[11, 12, 6]]),
		path('M13.4 12 a1.4 1.4 0 0 1 2.8 0 Z', true)
	),
	anthropogenic: tile(26, 14, text(3, 10, 'A', 8)),
	chalk: tile(16, 12, iMark(3.5, 1.5, 3.5), iMark(11.5, 7.5, 3.5)),
	calcTufa: tile(
		16,
		12,
		iMark(2.3, 1.5, 3.5),
		iMark(4.9, 1.5, 3.5),
		iMark(10.3, 7.5, 3.5),
		iMark(12.9, 7.5, 3.5)
	)
};

/** `a` is the base tile, `b` is shifted by half a tile so two patterns can overlap without clashing. */
export type PatternVariant = 'a' | 'b';
export const patternId = (key: MaterialKey, variant: PatternVariant = 'a') =>
	`din-${key}-${variant}`;
