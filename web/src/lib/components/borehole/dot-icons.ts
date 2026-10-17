import { columnFill, patterns } from '#lib/din4023/index.ts';
import type { MaterialKey, Shape } from '#lib/din4023/index.ts';
import type { Borehole } from '#lib/domain/borehole.ts';

/** Icon edge in CSS pixels, and the device pixel ratio it is rendered at. */
export const iconSize = 39;
export const iconPixelRatio = 2;

/** Edge of the hatch tile in icon pixels; the DIN tile is scaled to this. */
const tileSize = 15;

/** Main material of a layer and the colour it has on the original log. */
export interface DominantLayer {
	material: MaterialKey;
	color: string;
}

/**
 * The thickest layer, the one that fills most of the borehole, with its material and colour. Falls
 * back to the next thickest layer when that one has no structured description.
 */
export function dominantLayer(borehole: Borehole): DominantLayer | undefined {
	const thickest = [...borehole.layers].sort(
		(a, b) => b.endDepth - b.startDepth - (a.endDepth - a.startDepth)
	);
	for (const layer of thickest) {
		const composition = layer.petrography.composition;
		if (composition)
			return { material: columnFill(composition).main, color: layer.color.hex || '#ffffff' };
	}
	return undefined;
}

/** A dot whose inner circle is the DIN hatch of `material` on the layer's colour, inside a `ring`. */
export function patternIconSvg({ material, color }: DominantLayer, ring: string): string {
	const def = patterns[material];
	const defs = `<pattern id="hatch" width="${def.width}" height="${def.height}" patternUnits="userSpaceOnUse" patternTransform="scale(${tileSize / def.width})"><g stroke="#000" stroke-width="1.4" fill="none">${def.shapes.map(shapeMarkup).join('')}</g></pattern>`;
	return iconSvg(
		`<rect width="${iconSize}" height="${iconSize}" fill="${color}"/><rect width="${iconSize}" height="${iconSize}" fill="url(#hatch)"/>`,
		ring,
		defs
	);
}

/** A plain dot in `color`, inside a `ring`. */
export function colorIconSvg(color: string, ring: string): string {
	return iconSvg(`<rect width="${iconSize}" height="${iconSize}" fill="${color}"/>`, ring);
}

/** The ring is the outer edge; the fill is clipped to the inner circle so the ring stays unbroken. */
function iconSvg(fill: string, ring: string, defs = ''): string {
	const center = iconSize / 2;
	// Inner fill 25% larger than before (8px); a thin black rim sits between it and the white outer ring.
	const innerRadius = 10;
	const rimRadius = innerRadius + 0.75;
	const ringRadius = 13.5;
	return `<svg xmlns="http://www.w3.org/2000/svg" width="${iconSize}" height="${iconSize}" viewBox="0 0 ${iconSize} ${iconSize}"><defs>${defs}<clipPath id="dot"><circle cx="${center}" cy="${center}" r="${innerRadius}"/></clipPath></defs><circle cx="${center}" cy="${center}" r="${ringRadius}" fill="${ring}"/><circle cx="${center}" cy="${center}" r="${rimRadius}" fill="#000"/><g clip-path="url(#dot)">${fill}</g></svg>`;
}

function shapeMarkup(shape: Shape): string {
	const fill = (filled?: boolean) => (filled ? '#000' : 'none');
	switch (shape.type) {
		case 'circle':
			return `<circle cx="${shape.cx}" cy="${shape.cy}" r="${shape.r}" fill="${fill(shape.filled)}"/>`;
		case 'rect':
			return `<rect x="${shape.x}" y="${shape.y}" width="${shape.width}" height="${shape.height}" fill="${fill(shape.filled)}"/>`;
		case 'path':
			return `<path d="${shape.d}" fill="${fill(shape.filled)}"${shape.strokeWidth ? ` stroke-width="${shape.strokeWidth}"` : ''}/>`;
		case 'text':
			return `<text x="${shape.x}" y="${shape.y}" font-size="${shape.size}" fill="#000" stroke="none">${escapeXml(shape.text)}</text>`;
	}
}

function escapeXml(text: string): string {
	return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/** Rasterises an icon SVG at the device pixel ratio, ready for `map.addImage`. */
export async function renderIcon(svg: string): Promise<ImageData> {
	const image = new Image();
	image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
	await image.decode();
	const size = iconSize * iconPixelRatio;
	const canvas = document.createElement('canvas');
	canvas.width = size;
	canvas.height = size;
	const context = canvas.getContext('2d');
	if (!context) throw new Error('Canvas 2D is not available');
	context.drawImage(image, 0, 0, size, size);
	return context.getImageData(0, 0, size, size);
}

/** A plain dot in `color` with a white rim, for when the material fill is off. */
export function plainIconSvg(color: string): string {
	const center = iconSize / 2;
	return `<svg xmlns="http://www.w3.org/2000/svg" width="${iconSize}" height="${iconSize}" viewBox="0 0 ${iconSize} ${iconSize}"><circle cx="${center}" cy="${center}" r="13.5" fill="#fff"/><circle cx="${center}" cy="${center}" r="10" fill="${color}"/></svg>`;
}
