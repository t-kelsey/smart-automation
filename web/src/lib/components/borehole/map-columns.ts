/**
 * The map's 3D detail view: every borehole in view as a column of its layers, extruded with
 * MapLibre `fill-extrusion` and textured with the DIN 4023 hatch of each layer. Columns rise above
 * the ground with the surface layer on top and the deepest layer on the map, VERTICAL_EXAGGERATION
 * times taller than the borehole is deep.
 */
import type * as maplibregl from 'maplibre-gl';
import {
	VERTICAL_EXAGGERATION,
	columnHeight,
	columnSegments
} from '#lib/borehole-columns/column-model.ts';
import type { MaterialKey } from '#lib/din4023/index.ts';
import type { BBox, BoreholeColumnData } from '#lib/domain/borehole.ts';
import { PATTERN_PIXEL_RATIO, patternImage, patternImageId } from './column-patterns.ts';

/** The detail view is only available from this zoom on, so one request covers few boreholes. */
export const DETAIL_MIN_ZOOM = 11;

/** Camera of the detail view; the bearing is only set if the map faces north. */
export const DETAIL_PITCH = 60;
export const DETAIL_BEARING = -20;

/**
 * Footprint radius in metres, at every zoom: the size the columns had at zoom 16. A fixed size means
 * zooming never redraws the columns.
 */
const COLUMN_RADIUS_M = 20;
/** Enough sides for a round outline; the smooth wall normals below hide the remaining edges. */
const COLUMN_SIDES = 48;
/**
 * Any rounded-corner distance makes MapLibre blend the wall normals across shallow turns, so a
 * column is shaded as one curved surface instead of separately lit faces. The 7.5° corners of the
 * outline are too shallow to be rounded themselves, so the geometry stays as it is.
 */
const SMOOTH_WALLS_M = 1;
const METRES_PER_DEGREE = 111_320;

/** The extra area loaded around the view, as a share of its size, so small pans need no request. */
const LOAD_MARGIN = 0.5;

/** The hovered segment: the theme's primary blue (cerberus primary-500), as in the profile column. */
const HIGHLIGHT_COLOR = '#2563eb';
/** The highlight is a translucent sleeve slightly wider than the column, so the hatch shows through. */
const HIGHLIGHT_WIDTH = 1.15;

export const COLUMNS_LAYER = 'borehole-columns';
const COLUMNS_SOURCE = 'borehole-columns';
const HIGHLIGHT_LAYER = 'borehole-columns-highlight';
const HIGHLIGHT_SOURCE = 'borehole-columns-highlight';

/** Properties of one segment polygon; read back from hovered features. */
export interface SegmentProperties {
	boreholeId: string;
	layerId: string;
	lon: number;
	lat: number;
	position: number;
	top: number;
	bottom: number;
	label: string;
	shortForm: string;
	color: string;
	/** Main material; absent if unclassified. */
	material?: MaterialKey;
	/** Image id of the segment's hatch tile. */
	pattern: string;
	/** Extrusion in metres above the ground. */
	base: number;
	height: number;
}

/**
 * A regular polygon approximating the column's circular footprint. The hatch wraps around the wall
 * continuously from the ring's first vertex to its last, so the only seam is where they meet: on
 * the north side, away from the detail view's camera.
 */
function footprint(lon: number, lat: number, radius: number): GeoJSON.Position[] {
	const dLat = radius / METRES_PER_DEGREE;
	const dLon = dLat / Math.max(Math.cos((lat * Math.PI) / 180), 0.01);
	const ring: GeoJSON.Position[] = [];
	for (let i = 0; i <= COLUMN_SIDES; i++) {
		const angle = Math.PI / 2 + (2 * Math.PI * (i % COLUMN_SIDES)) / COLUMN_SIDES;
		ring.push([lon + dLon * Math.cos(angle), lat + dLat * Math.sin(angle)]);
	}
	return ring;
}

/** One extruded polygon per layer; the surface layer is on top. */
export function columnFeatures(
	columns: Iterable<BoreholeColumnData>
): GeoJSON.FeatureCollection<GeoJSON.Polygon, SegmentProperties> {
	const features: GeoJSON.Feature<GeoJSON.Polygon, SegmentProperties>[] = [];
	for (const column of columns) {
		const height = columnHeight(column);
		const ring = footprint(column.lon, column.lat, COLUMN_RADIUS_M);
		for (const segment of columnSegments(column)) {
			features.push({
				type: 'Feature',
				geometry: { type: 'Polygon', coordinates: [ring] },
				properties: {
					boreholeId: column.id,
					layerId: segment.layerId,
					lon: column.lon,
					lat: column.lat,
					position: segment.position,
					top: segment.top,
					bottom: segment.bottom,
					label: segment.label,
					shortForm: segment.shortForm,
					color: segment.color,
					material: segment.material,
					pattern: patternImageId(segment.material, segment.color),
					base: (height - segment.bottom) * VERTICAL_EXAGGERATION,
					height: (height - segment.top) * VERTICAL_EXAGGERATION
				}
			});
		}
	}
	return { type: 'FeatureCollection', features };
}

const contains = (outer: BBox, inner: BBox) =>
	outer[0] <= inner[0] && outer[1] <= inner[1] && outer[2] >= inner[2] && outer[3] >= inner[3];

const emptyCollection = (): GeoJSON.FeatureCollection => ({
	type: 'FeatureCollection',
	features: []
});

/**
 * Shows the columns of the boreholes in view and loads more as the map moves. Loaded areas and
 * columns are kept, so panning back or around within a loaded area sends no request, and the
 * columns are only redrawn when newly loaded ones arrive.
 */
export class MapColumns {
	private readonly columns = new Map<string, BoreholeColumnData>();
	private readonly loaded: BBox[] = [];
	/** Segments as last drawn, by layer id, for the highlight. */
	private readonly drawn = new Map<string, SegmentProperties>();
	private visible = false;
	private request = 0;
	private timer: ReturnType<typeof setTimeout> | undefined;
	private hovered: string | undefined;
	private marked = new Set<string>();
	/** How many columns were drawn last; the columns are only redrawn when new ones were loaded. */
	private drawnCount = -1;
	private readonly onMoveEnd = () => this.schedule();

	constructor(
		private readonly map: maplibregl.Map,
		private readonly load: (bbox: BBox) => Promise<BoreholeColumnData[]>,
		private readonly onError: (error: unknown) => void
	) {}

	show() {
		if (this.visible) return;
		this.visible = true;
		// No simplification: it would drop vertices of the small outlines at low zoom.
		this.map.addSource(COLUMNS_SOURCE, {
			type: 'geojson',
			data: emptyCollection(),
			tolerance: 0
		});
		this.map.addLayer({
			id: COLUMNS_LAYER,
			type: 'fill-extrusion',
			source: COLUMNS_SOURCE,
			layout: { 'fill-extrusion-rounded-corner-distance': SMOOTH_WALLS_M },
			paint: {
				'fill-extrusion-pattern': ['get', 'pattern'],
				'fill-extrusion-base': ['get', 'base'],
				'fill-extrusion-height': ['get', 'height'],
				'fill-extrusion-opacity': 1,
				'fill-extrusion-vertical-gradient': true
			}
		});
		this.map.addSource(HIGHLIGHT_SOURCE, {
			type: 'geojson',
			data: emptyCollection(),
			tolerance: 0
		});
		this.map.addLayer({
			id: HIGHLIGHT_LAYER,
			type: 'fill-extrusion',
			source: HIGHLIGHT_SOURCE,
			layout: { 'fill-extrusion-rounded-corner-distance': SMOOTH_WALLS_M },
			paint: {
				'fill-extrusion-color': HIGHLIGHT_COLOR,
				'fill-extrusion-base': ['get', 'base'],
				'fill-extrusion-height': ['get', 'height'],
				'fill-extrusion-opacity': 0.55
			}
		});
		this.map.on('moveend', this.onMoveEnd);
		this.render();
		this.schedule();
	}

	hide() {
		if (!this.visible) return;
		this.visible = false;
		this.request++;
		clearTimeout(this.timer);
		this.hovered = undefined;
		this.drawnCount = -1;
		this.drawn.clear();
		this.map.off('moveend', this.onMoveEnd);
		for (const layer of [HIGHLIGHT_LAYER, COLUMNS_LAYER])
			if (this.map.getLayer(layer)) this.map.removeLayer(layer);
		for (const source of [HIGHLIGHT_SOURCE, COLUMNS_SOURCE])
			if (this.map.getSource(source)) this.map.removeSource(source);
	}

	/** Highlights one segment, or none. */
	highlight(layerId: string | undefined) {
		if (!this.visible || layerId === this.hovered) return;
		this.hovered = layerId;
		this.renderHighlight();
	}

	/** Marks whole columns, e.g. the boreholes caught by a section line; an empty set clears it. */
	mark(boreholeIds: Set<string>) {
		this.marked = boreholeIds;
		if (this.visible) this.renderHighlight();
	}

	private viewBox(): BBox {
		const b = this.map.getBounds();
		return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
	}

	private schedule() {
		clearTimeout(this.timer);
		this.timer = setTimeout(() => void this.loadView(), 200);
	}

	private async loadView() {
		if (!this.visible) return;
		const view = this.viewBox();
		if (this.loaded.some((area) => contains(area, view))) return;
		const width = view[2] - view[0];
		const height = view[3] - view[1];
		const area: BBox = [
			Math.max(-180, view[0] - width * LOAD_MARGIN),
			Math.max(-90, view[1] - height * LOAD_MARGIN),
			Math.min(180, view[2] + width * LOAD_MARGIN),
			Math.min(90, view[3] + height * LOAD_MARGIN)
		];
		const request = ++this.request;
		try {
			const columns = await this.load(area);
			// A newer view or hiding the columns makes this answer stale.
			if (request !== this.request || !this.visible) return;
			for (const column of columns) this.columns.set(column.id, column);
			this.loaded.push(area);
			this.render();
		} catch (error) {
			if (request === this.request) this.onError(error);
		}
	}

	/** Adds the hatch tiles the segments need; drawn synchronously, so they are there for this frame. */
	private ensurePatterns(segments: Iterable<SegmentProperties>) {
		for (const segment of segments) {
			if (this.map.hasImage(segment.pattern)) continue;
			this.map.addImage(segment.pattern, patternImage(segment.material, segment.color), {
				pixelRatio: PATTERN_PIXEL_RATIO
			});
		}
	}

	/**
	 * Draws every loaded column. Columns are only ever added, so the data is rebuilt only when new
	 * ones arrived; moving or zooming the map never redraws them.
	 */
	private render() {
		if (!this.visible || this.columns.size === this.drawnCount) return;
		this.drawnCount = this.columns.size;
		const collection = columnFeatures(this.columns.values());
		this.drawn.clear();
		for (const feature of collection.features)
			this.drawn.set(feature.properties.layerId, feature.properties);
		this.ensurePatterns(this.drawn.values());
		this.map.getSource<maplibregl.GeoJSONSource>(COLUMNS_SOURCE)?.setData(collection);
		this.renderHighlight();
	}

	/** The hovered segment as a slightly wider translucent sleeve at the current footprint size. */
	/**
	 * Blue translucent sleeves, slightly wider than the column: around
	 * the hovered segment and around the whole column of every marked borehole.
	 */
	private renderHighlight() {
		const radius = COLUMN_RADIUS_M * HIGHLIGHT_WIDTH;
		const sleeve = (lon: number, lat: number, base: number, height: number): GeoJSON.Feature => ({
			type: 'Feature',
			geometry: { type: 'Polygon', coordinates: [footprint(lon, lat, radius)] },
			properties: { base, height }
		});
		const features: GeoJSON.Feature[] = [];
		const segment = this.hovered ? this.drawn.get(this.hovered) : undefined;
		if (segment) features.push(sleeve(segment.lon, segment.lat, segment.base, segment.height));
		for (const id of this.marked) {
			const column = this.columns.get(id);
			if (column)
				features.push(
					sleeve(column.lon, column.lat, 0, columnHeight(column) * VERTICAL_EXAGGERATION)
				);
		}
		this.map
			.getSource<maplibregl.GeoJSONSource>(HIGHLIGHT_SOURCE)
			?.setData({ type: 'FeatureCollection', features });
	}
}
