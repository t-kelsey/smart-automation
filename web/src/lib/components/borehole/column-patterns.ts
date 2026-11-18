/**
 * Hatch tiles for the map's detail view columns: the DIN 4023 hatch of a layer's main material on
 * its DIN colour, drawn with Canvas 2D so the map can add them synchronously before drawing.
 */
import { patterns } from '#lib/din4023/index.ts';
import type { MaterialKey, Shape } from '#lib/din4023/index.ts';

/** CSS pixels per pattern unit; the profile column draws 60 units as 90 px, the same scale. */
const SCALE = 1.5;
/** Device pixels per CSS pixel the tiles are rendered at. */
export const PATTERN_PIXEL_RATIO = 2;
/** Size of the plain tile used for layers without a material. */
const PLAIN_TILE = 16;
/** The colour is tinted like in the profile column, so the black hatch stays readable on dark colours. */
const TINT_OPACITY = 0.5;

/** Image id of a tile in the map's style. */
export const patternImageId = (material: MaterialKey | undefined, color: string) =>
	`column-${material ?? 'none'}-${color}`;

function drawShape(context: CanvasRenderingContext2D, shape: Shape) {
	switch (shape.type) {
		case 'circle': {
			context.beginPath();
			context.arc(shape.cx, shape.cy, shape.r, 0, 2 * Math.PI);
			if (shape.filled) context.fill();
			context.stroke();
			return;
		}
		case 'rect':
			if (shape.filled) context.fillRect(shape.x, shape.y, shape.width, shape.height);
			context.strokeRect(shape.x, shape.y, shape.width, shape.height);
			return;
		case 'path': {
			const path = new Path2D(shape.d);
			if (shape.filled) context.fill(path);
			context.save();
			if (shape.strokeWidth) context.lineWidth = shape.strokeWidth;
			context.stroke(path);
			context.restore();
			return;
		}
		case 'text':
			context.font = `${shape.size}px sans-serif`;
			context.fillText(shape.text, shape.x, shape.y);
			return;
	}
}

/** One seamless tile: the tinted colour, and the material's hatch if it has one. */
export function patternTile(material: MaterialKey | undefined, color: string): HTMLCanvasElement {
	const def = material ? patterns[material] : undefined;
	const ratio = PATTERN_PIXEL_RATIO;
	const width = def ? Math.round(def.width * SCALE * ratio) : PLAIN_TILE * ratio;
	const height = def ? Math.round(def.height * SCALE * ratio) : PLAIN_TILE * ratio;
	const canvas = document.createElement('canvas');
	canvas.width = width;
	canvas.height = height;
	const context = canvas.getContext('2d');
	if (!context) throw new Error('Canvas 2D is not available');
	context.fillStyle = '#ffffff';
	context.fillRect(0, 0, width, height);
	context.globalAlpha = def ? TINT_OPACITY : 1;
	context.fillStyle = color;
	context.fillRect(0, 0, width, height);
	context.globalAlpha = 1;
	if (def) {
		// Scale non-uniformly by the rounding error so the tile repeats without seams.
		context.scale(width / def.width, height / def.height);
		context.strokeStyle = '#000000';
		context.fillStyle = '#000000';
		context.lineWidth = 0.9;
		for (const shape of def.shapes) drawShape(context, shape);
	}
	return canvas;
}

/** The tile as `ImageData`, ready for `map.addImage` with `pixelRatio: PATTERN_PIXEL_RATIO`. */
export function patternImage(material: MaterialKey | undefined, color: string): ImageData {
	const canvas = patternTile(material, color);
	return canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height);
}
