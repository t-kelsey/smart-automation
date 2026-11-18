/**
 * The section line on the map (ADR-0004): drawing it with two clicks, and previewing it with its
 * corridor and rings around the boreholes it catches.
 */
import type * as maplibregl from 'maplibre-gl';
import { corridorRing, type SectionLine } from '#lib/borehole-columns/section.ts';

const SOURCE = 'section-line';
const CAUGHT_SOURCE = 'section-caught';
const CORRIDOR_LAYER = 'section-corridor';
const CORRIDOR_OUTLINE_LAYER = 'section-corridor-outline';
const LINE_LAYER = 'section-line';
const ENDS_LAYER = 'section-ends';
const CAUGHT_LAYER = 'section-caught';

/** The theme's primary blue (cerberus primary-500), as for the other highlights. */
const COLOR = '#2563eb';

const empty = (): GeoJSON.FeatureCollection => ({ type: 'FeatureCollection', features: [] });

/**
 * Draws the line, the corridor and the caught-borehole rings below the borehole dots and columns,
 * and runs the two-click drawing mode.
 */
export class MapSection {
	private drawing:
		| { start?: [number, number]; onDone: (line: SectionLine) => void; onCancel: () => void }
		| undefined;
	private line: SectionLine | undefined;
	private readonly onClick = (e: maplibregl.MapMouseEvent) => this.click(e);
	private readonly onMove = (e: maplibregl.MapMouseEvent) => this.move(e);
	private readonly onKey = (e: KeyboardEvent) => {
		if (e.key === 'Escape') this.drawing?.onCancel();
	};

	constructor(
		private readonly map: maplibregl.Map,
		/** Layer to insert below, so the section stays under the boreholes. */
		private readonly beforeLayer: string
	) {
		map.addSource(SOURCE, { type: 'geojson', data: empty() });
		map.addSource(CAUGHT_SOURCE, { type: 'geojson', data: empty() });
		const before = map.getLayer(beforeLayer) ? beforeLayer : undefined;
		map.addLayer(
			{
				id: CORRIDOR_LAYER,
				type: 'fill',
				source: SOURCE,
				filter: ['==', ['get', 'part'], 'corridor'],
				paint: { 'fill-color': COLOR, 'fill-opacity': 0.12 }
			},
			before
		);
		map.addLayer(
			{
				id: CORRIDOR_OUTLINE_LAYER,
				type: 'line',
				source: SOURCE,
				filter: ['==', ['get', 'part'], 'corridor'],
				paint: { 'line-color': COLOR, 'line-width': 1, 'line-dasharray': [3, 2] }
			},
			before
		);
		map.addLayer(
			{
				id: LINE_LAYER,
				type: 'line',
				source: SOURCE,
				filter: ['==', ['get', 'part'], 'line'],
				layout: { 'line-cap': 'round' },
				paint: { 'line-color': COLOR, 'line-width': 3 }
			},
			before
		);
		map.addLayer(
			{
				id: ENDS_LAYER,
				type: 'circle',
				source: SOURCE,
				filter: ['==', ['get', 'part'], 'end'],
				paint: {
					'circle-radius': 5,
					'circle-color': '#ffffff',
					'circle-stroke-color': COLOR,
					'circle-stroke-width': 2.5
				}
			},
			before
		);
		// Rings around the caught borehole dots; on top of the dots, which they surround.
		map.addLayer({
			id: CAUGHT_LAYER,
			type: 'circle',
			source: CAUGHT_SOURCE,
			paint: {
				'circle-radius': 17,
				'circle-opacity': 0,
				'circle-stroke-color': COLOR,
				'circle-stroke-width': 3
			}
		});
	}

	/** Shows `line` with its corridor, or nothing. */
	setLine(line: SectionLine | undefined) {
		this.line = line;
		if (!this.drawing) this.render(line);
	}

	/** Rings around these borehole positions (`[lon, lat]`); hidden while `visible` is false. */
	setCaught(positions: [number, number][], visible: boolean) {
		const features: GeoJSON.Feature[] = positions.map((coordinates) => ({
			type: 'Feature',
			geometry: { type: 'Point', coordinates },
			properties: {}
		}));
		this.map.getSource<maplibregl.GeoJSONSource>(CAUGHT_SOURCE)?.setData({
			type: 'FeatureCollection',
			features
		});
		this.map.setLayoutProperty(CAUGHT_LAYER, 'visibility', visible ? 'visible' : 'none');
	}

	get isDrawing() {
		return !!this.drawing;
	}

	/** Two-click drawing: start, then end; a rubber band follows the pointer in between. */
	startDrawing(onDone: (line: SectionLine) => void, onCancel: () => void) {
		if (this.drawing) return;
		this.drawing = { onDone, onCancel };
		this.map.getCanvas().style.cursor = 'crosshair';
		this.map.on('click', this.onClick);
		this.map.on('mousemove', this.onMove);
		window.addEventListener('keydown', this.onKey);
	}

	stopDrawing() {
		if (!this.drawing) return;
		this.drawing = undefined;
		this.map.getCanvas().style.cursor = '';
		this.map.off('click', this.onClick);
		this.map.off('mousemove', this.onMove);
		window.removeEventListener('keydown', this.onKey);
		this.render(this.line);
	}

	remove() {
		this.stopDrawing();
		for (const layer of [
			CAUGHT_LAYER,
			ENDS_LAYER,
			LINE_LAYER,
			CORRIDOR_OUTLINE_LAYER,
			CORRIDOR_LAYER
		])
			if (this.map.getLayer(layer)) this.map.removeLayer(layer);
		for (const source of [CAUGHT_SOURCE, SOURCE])
			if (this.map.getSource(source)) this.map.removeSource(source);
	}

	private click(e: maplibregl.MapMouseEvent) {
		if (!this.drawing) return;
		const point: [number, number] = [e.lngLat.lng, e.lngLat.lat];
		if (!this.drawing.start) {
			this.drawing.start = point;
			this.render({ start: point, end: point }, false);
			return;
		}
		const line = { start: this.drawing.start, end: point };
		this.drawing.onDone(line);
	}

	private move(e: maplibregl.MapMouseEvent) {
		const start = this.drawing?.start;
		if (start) this.render({ start, end: [e.lngLat.lng, e.lngLat.lat] }, true);
	}

	/** The line, its end points and (unless only the start is set) the corridor. */
	private render(line: SectionLine | undefined, corridor = true) {
		const features: GeoJSON.Feature[] = line
			? [
					...(corridor
						? [
								{
									type: 'Feature' as const,
									geometry: { type: 'Polygon' as const, coordinates: [corridorRing(line)] },
									properties: { part: 'corridor' }
								}
							]
						: []),
					{
						type: 'Feature',
						geometry: { type: 'LineString', coordinates: [line.start, line.end] },
						properties: { part: 'line' }
					},
					...[line.start, line.end].map((coordinates) => ({
						type: 'Feature' as const,
						geometry: { type: 'Point' as const, coordinates },
						properties: { part: 'end' }
					}))
				]
			: [];
		this.map.getSource<maplibregl.GeoJSONSource>(SOURCE)?.setData({
			type: 'FeatureCollection',
			features
		});
	}
}
