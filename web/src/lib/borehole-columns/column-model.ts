/**
 * Renderer-independent model of a borehole drawn as a column of its layers: one segment per layer
 * with its depth range and the DIN colour of its main material. Used by the map's 3D detail view
 * and meant for the planned side-on section view (ADR-0004).
 */
import { columnFill, describe, materialHex, materials, shortForm } from '#lib/din4023/index.ts';
import type { MaterialKey } from '#lib/din4023/index.ts';
import type { BoreholeColumnData } from '#lib/domain/borehole.ts';

/** Columns are drawn this many times taller than the borehole is deep. */
export const VERTICAL_EXAGGERATION = 10;

/** Colour of layers whose material could not be recognised. */
export const UNKNOWN_COLOR = '#9ca3af';

/** Colour of materials the standard gives no colour (matches the map legend). */
export const UNCOLORED_MATERIAL = '#ffffff';

export interface ColumnSegment {
	layerId: string;
	/** 1-based layer number, as shown to users. */
	position: number;
	/** Depths below the borehole start in metres; `top < bottom`. */
	top: number;
	bottom: number;
	/** Main material; `undefined` when the layer text could not be classified. */
	material?: MaterialKey;
	/** Hex colour to draw the segment with. */
	color: string;
	/** Short label, e.g. "Sand" or "unknown". */
	label: string;
	/** Longer description: the DIN description, or the original text if unclassified. */
	description: string;
	/** DIN short form (e.g. `S, u'`), empty if unclassified. */
	shortForm: string;
}

/**
 * One segment per layer, ordered by depth. Layers with an unknown material are grey; depth gaps
 * between layers produce no segment, so they stay empty in the drawing.
 */
export function columnSegments(column: BoreholeColumnData): ColumnSegment[] {
	return column.layers
		.filter((layer) => layer.endDepth > layer.startDepth)
		.map((layer) => {
			const composition = layer.petrography.composition;
			const material = composition ? columnFill(composition).main : undefined;
			return {
				layerId: layer.id,
				position: layer.position,
				top: layer.startDepth,
				bottom: layer.endDepth,
				material,
				color: material ? (materialHex(material) ?? UNCOLORED_MATERIAL) : UNKNOWN_COLOR,
				label: material ? materials[material].name.en : 'unknown',
				description: composition ? describe(composition) : layer.petrography.description,
				shortForm: composition ? shortForm(composition) : ''
			};
		})
		.sort((a, b) => a.top - b.top);
}

/** Depth the column represents: the stated total depth, or the deepest layer if that is deeper. */
export function columnHeight(column: BoreholeColumnData): number {
	const deepest = column.layers.reduce((max, layer) => Math.max(max, layer.endDepth), 0);
	return Math.max(column.totalDepth ?? 0, deepest);
}
