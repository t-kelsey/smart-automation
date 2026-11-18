<script module lang="ts">
	import type { BoreholeSummary, MapPoint } from '#lib/domain/borehole.ts';
	import type { DominantLayer } from '#lib/components/borehole/dot-icons.ts';
	import { notify } from '#lib/components/toast/index.ts';
	import { createServices } from '#lib/services/index.ts';

	// The last known position, so a freshly mounted map can show the user's dot immediately.
	let lastPosition: [number, number] | undefined;

	// Loaded in the browser only and shared by all maps, so navigating between them reuses the data.
	let servicesPromise: ReturnType<typeof createServices> | undefined;
	let pointsPromise: Promise<MapPoint[]> | undefined;
	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- plain cache, nothing renders from it
	const summaryCache = new Map<string, BoreholeSummary>();
	// Dominant material per borehole, loaded only for boreholes drawn as single dots.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- plain cache, nothing renders from it
	const materials = new Map<string, DominantLayer | null>();
	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- plain lookup, nothing renders from it
	const materialsPending = new Set<string>();

	const getServices = () => (servicesPromise ??= createServices({ fetch: globalThis.fetch }));

	function loadPoints(): Promise<MapPoint[]> {
		pointsPromise ??= getServices()
			.then(({ boreholes }) => boreholes.listMapPoints())
			.catch((error) => {
				pointsPromise = undefined;
				notify.fromError(error, 'Could not load boreholes');
				throw error;
			});
		return pointsPromise;
	}

	async function loadSummary(id: string): Promise<BoreholeSummary> {
		const cached = summaryCache.get(id);
		if (cached) return cached;
		const { boreholes } = await getServices();
		const summary = await boreholes.getSummary(id);
		summaryCache.set(id, summary);
		return summary;
	}
</script>

<script lang="ts">
	import 'maplibre-gl/dist/maplibre-gl.css';
	import * as maplibregl from 'maplibre-gl';
	// maplibre-gl locates its worker next to its own module via import.meta.url. Vite does not emit
	// that file in the production build (404, "Worker failed to load"), so ship and point to it explicitly.
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
	import { mount, unmount } from 'svelte';
	import BoreholeHoverCard from '#lib/components/borehole/BoreholeHoverCard.svelte';
	import { LocateFixedIcon } from '@lucide/svelte';
	import Supercluster from 'supercluster';
	import { mapColors } from './map-colors.ts';
	import {
		colorIconSvg,
		iconSize,
		dominantLayer,
		iconPixelRatio,
		patternIconSvg,
		plainIconSvg,
		renderIcon
	} from './dot-icons.ts';
	import {
		COLUMNS_LAYER,
		DETAIL_BEARING,
		DETAIL_MIN_ZOOM,
		DETAIL_PITCH,
		MapColumns,
		type SegmentProperties
	} from './map-columns.ts';
	import type { HoveredLayer } from './BoreholeHoverCard.svelte';
	import { MapSection } from './map-section.ts';
	import { CORRIDOR_M, project, type SectionLine } from '#lib/borehole-columns/section.ts';
	interface MapView {
		lat: number;
		lon: number;
		zoom: number;
	}

	interface PointFeature {
		type: 'Feature';
		properties: { id: string };
		geometry: { type: 'Point'; coordinates: [number, number] };
	}

	interface Props {
		/** Space kept free around the boreholes when fitting the initial view. */
		padding?: maplibregl.PaddingOptions;
		/** Move to the user's current location once the browser grants it; keeps the fitted view otherwise. */
		centerOnUser?: boolean;
		/** Start at this view instead of fitting all boreholes. */
		initialView?: MapView;
		/** Embedded use: page scrolling wins; zoom with Ctrl/Cmd + scroll, pan with two fingers on touch. */
		cooperative?: boolean;
		/** Called with the current view when the map background is clicked. */
		onMapClick?: (view: MapView) => void;
		/** Called with the new view whenever the map has finished moving. */
		onViewChange?: (view: MapView) => void;
		/** Show a button in the lower right corner that moves the map to the user's location. */
		showLocate?: boolean;
		/** Fill each dot with the hatch of its biggest layer; off shows the plain verified/unverified colour. */
		showFill?: boolean;
		/** Called once the map has rendered its first complete view. */
		onReady?: () => void;
		/**
		 * 3D detail view: the map tilts and every borehole is a column of its layers. Only from zoom
		 * DETAIL_MIN_ZOOM on; zooming out further leaves it and calls `onDetailExit`.
		 */
		detail?: boolean;
		/** Called when the map left the detail view by itself (zoomed out too far). */
		onDetailExit?: () => void;
		/** Section drawing mode: two clicks draw a line, Esc cancels. */
		drawingSection?: boolean;
		/** The section line to preview, with its corridor and the boreholes it catches. */
		sectionLine?: SectionLine;
		/** Called with the drawn line after the second click. */
		onSectionDrawn?: (line: SectionLine) => void;
		/** Called when drawing is cancelled with Esc. */
		onSectionDrawCancel?: () => void;
	}

	let {
		padding = { top: 40, bottom: 40, left: 40, right: 40 },
		centerOnUser = false,
		initialView,
		cooperative = false,
		onMapClick,
		onViewChange,
		showLocate = false,
		showFill = false,
		onReady,
		detail = false,
		onDetailExit,
		drawingSection = false,
		sectionLine,
		onSectionDrawn,
		onSectionDrawCancel
	}: Props = $props();

	let container: HTMLDivElement;
	maplibregl.setWorkerUrl(workerUrl);

	let mapInstance: maplibregl.Map | undefined;
	let locateNow: (() => void) | undefined;
	let redrawDots: (() => void) | undefined;
	let applyDetail: ((on: boolean) => void) | undefined;
	let applySection: ((line: SectionLine | undefined) => void) | undefined;
	let applyDrawing: ((on: boolean) => void) | undefined;

	// Preview the section line and start or stop drawing when the props change.
	$effect(() => {
		const line = sectionLine;
		applySection?.(line);
	});
	$effect(() => {
		const on = drawingSection;
		applyDrawing?.(on);
	});

	// Switch the detail view on or off when the prop changes.
	$effect(() => {
		const on = detail;
		applyDetail?.(on);
	});

	// Redraw the dots when the fill is switched on or off.
	$effect(() => {
		void showFill;
		redrawDots?.();
	});
	let locating = $state(false);

	/** A picture of what the map currently shows, or undefined if it cannot be taken. */
	export function snapshot(): string | undefined {
		try {
			return mapInstance?.getCanvas().toDataURL('image/jpeg', 0.92);
		} catch {
			return undefined;
		}
	}

	/**
	 * Clusters are plain buttons, single boreholes a WebGL circle layer, and one shared card shows
	 * the hovered borehole: thousands of boreholes cost a few hundred DOM nodes at most.
	 */
	/* eslint-disable svelte/prefer-svelte-reactivity -- plain caches and lookups, nothing renders from them */
	function showPoints(
		map: maplibregl.Map,
		points: MapPoint[],
		cleanups: (() => void)[],
		fit: boolean
	) {
		const byId = new Map<string, MapPoint>();
		const features: PointFeature[] = [];
		const bounds = new maplibregl.LngLatBounds();
		for (const point of points) {
			byId.set(point.id, point);
			bounds.extend([point.lon, point.lat]);
			features.push({
				type: 'Feature',
				properties: { id: point.id },
				geometry: { type: 'Point', coordinates: [point.lon, point.lat] }
			});
		}
		if (!bounds.isEmpty() && fit) map.fitBounds(bounds, { padding, maxZoom: 14, duration: 0 });

		const index = new Supercluster<{ id: string }>({ radius: 50, maxZoom: 14 }).load(features);
		// The detail view (see below) draws columns instead of dots while this is set.
		let detailActive = false;

		// --- single boreholes: one GeoJSON source with only the unclustered points in view
		const emptyCollection: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };
		map.addSource('boreholes', { type: 'geojson', data: emptyCollection });
		map.addLayer({
			id: 'boreholes',
			type: 'symbol',
			source: 'boreholes',
			layout: {
				'icon-image': ['get', 'icon'],
				'icon-allow-overlap': true,
				'icon-ignore-placement': true
			}
		});
		const source = map.getSource<maplibregl.GeoJSONSource>('boreholes');
		// The section line and its corridor, drawn below the dots.
		const section = new MapSection(map, 'boreholes');

		// --- dots: the inner circle is the hatch of the dominant material, or the verified colour until it is loaded
		const iconPending = new Set<string>();
		let refreshTimer: ReturnType<typeof setTimeout> | undefined;
		let active = true;
		// Redraws the dots once icons or materials arrive; a burst of responses shares one redraw
		function scheduleRefresh() {
			if (!active || refreshTimer) return;
			refreshTimer = setTimeout(() => {
				refreshTimer = undefined;
				update();
			}, 100);
		}
		// Adds the icon once it is rasterised; true when it can be drawn now
		function ensureIcon(id: string, svg: () => string): boolean {
			if (map.hasImage(id)) return true;
			if (!iconPending.has(id)) {
				iconPending.add(id);
				renderIcon(svg())
					.then((image) => {
						if (active && !map.hasImage(id))
							map.addImage(id, image, { pixelRatio: iconPixelRatio });
					})
					.catch(() => {})
					.finally(() => {
						iconPending.delete(id);
						scheduleRefresh();
					});
			}
			return false;
		}
		// The material's hatch once known, else the verified colour
		function resolveIcon(point: MapPoint, layer: DominantLayer | null | undefined): string {
			const ring = '#ffffff';
			if (layer) {
				const id = `dot-pattern-${layer.material}-${layer.color}-${point.verified}`;
				if (ensureIcon(id, () => patternIconSvg(layer, ring))) return id;
			}
			const id = `dot-color-${point.verified}`;
			ensureIcon(id, () =>
				colorIconSvg(point.verified ? mapColors.verified : mapColors.unverified, ring)
			);
			return id;
		}
		// Verified boreholes filled, unverified ones hollow, on a white rim, without the material fill
		function resolvePlainIcon(point: MapPoint): string {
			const id = `dot-plain-${point.verified}`;
			ensureIcon(id, () =>
				plainIconSvg(point.verified ? mapColors.verified : mapColors.unverified, point.verified)
			);
			return id;
		}
		// Loads the dominant material of a borehole once; the map points do not carry it
		function requestMaterial(id: string) {
			if (materials.has(id) || materialsPending.has(id)) return;
			materialsPending.add(id);
			getServices()
				.then(({ boreholes }) => boreholes.getById(id))
				.then((borehole) => {
					materials.set(id, dominantLayer(borehole) ?? null);
				})
				.catch(() => {
					materials.set(id, null);
				})
				.finally(() => {
					materialsPending.delete(id);
					scheduleRefresh();
				});
		}

		// --- markers: plain button markers for clusters, and for single boreholes at zoom 5 or less
		const markers = new Map<string, maplibregl.Marker>();
		// Size grows with log(count): 70% of the 36px base for small clusters, 170% for all boreholes
		const markerBaseSize = 36;
		const markerScaleMax = Math.log10(Math.max(points.length, 2));
		// Zoom scales it linearly too: 100% at zoom 5, 300% at zoom 15
		function applyMarkerSize(element: HTMLElement, count: number) {
			const t = Math.min(1, Math.log10(Math.max(count, 1)) / markerScaleMax);
			const zoomScale = Math.min(3, Math.max(1, 1 + (map.getZoom() - 5) / 5));
			const size = Math.round(markerBaseSize * (0.7 + 1.0 * t) * zoomScale);
			element.style.width = element.style.height = `${size}px`;
			// The 12px label on the 36px base keeps its ratio as the circle grows
			element.style.fontSize = `${size / 3}px`;
		}
		function createCountMarker(count: number, lngLat: [number, number], onClick: () => void) {
			const element = document.createElement('button');
			element.type = 'button';
			element.textContent = count >= 1000 ? `${Math.round(count / 100) / 10}k` : String(count);
			element.setAttribute(
				'aria-label',
				`${count === 1 ? 'Borehole' : `Cluster of ${count} boreholes`}, click to zoom in`
			);
			element.dataset.count = String(count);
			applyMarkerSize(element, count);
			element.className =
				'flex cursor-pointer items-center justify-center rounded-full border-2 border-white bg-primary-500 text-xs font-semibold text-white shadow-md';
			element.addEventListener('click', onClick);
			return new maplibregl.Marker({ element }).setLngLat(lngLat).addTo(map);
		}

		// Whether the dot layer holds data; the detail view empties it once, not on every move.
		let dotsShown = false;
		function update() {
			// The detail view draws columns instead of clusters and dots.
			if (detailActive) {
				markers.forEach((marker) => marker.remove());
				markers.clear();
				if (dotsShown) source?.setData(emptyCollection);
				dotsShown = false;
				return;
			}
			dotsShown = true;
			const b = map.getBounds();
			const zoom = map.getZoom();
			const grouped = zoom <= 5;
			const items = index.getClusters(
				[b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
				Math.round(zoom)
			);
			const singles: GeoJSON.Feature[] = [];
			const seen = new Set<string>();
			for (const item of items) {
				const properties = item.properties;
				const lngLat = item.geometry.coordinates as [number, number];
				if ('cluster' in properties && properties.cluster) {
					const key = `cluster:${properties.cluster_id}`;
					seen.add(key);
					if (!markers.has(key))
						markers.set(
							key,
							createCountMarker(properties.point_count, lngLat, () =>
								map.easeTo({
									center: lngLat,
									zoom: index.getClusterExpansionZoom(properties.cluster_id)
								})
							)
						);
				} else {
					const point = byId.get((properties as { id: string }).id);
					if (!point) continue;
					if (grouped) {
						const key = `point:${point.id}`;
						seen.add(key);
						if (!markers.has(key))
							markers.set(
								key,
								createCountMarker(1, lngLat, () => map.easeTo({ center: lngLat, zoom: 6 }))
							);
					} else {
						if (showFill) requestMaterial(point.id);
						singles.push({
							type: 'Feature',
							geometry: item.geometry,
							properties: {
								id: point.id,
								icon: showFill
									? resolveIcon(point, materials.get(point.id))
									: resolvePlainIcon(point)
							}
						});
					}
				}
			}
			for (const [key, marker] of markers) {
				const element = marker.getElement();
				if (seen.has(key)) {
					applyMarkerSize(element, Number(element.dataset.count));
					continue;
				}
				marker.remove();
				markers.delete(key);
			}
			source?.setData({ type: 'FeatureCollection', features: singles });
		}
		update();
		redrawDots = update;
		map.on('moveend', update);

		// --- the shared hover card
		const cardElement = document.createElement('div');
		cardElement.className = 'z-20';
		const card = $state<{ point?: MapPoint; summary?: BoreholeSummary; layer?: HoveredLayer }>({});
		const cardComponent = mount(BoreholeHoverCard, {
			target: cardElement,
			props: {
				get point() {
					return card.point;
				},
				get summary() {
					return card.summary;
				},
				get layer() {
					return card.layer;
				},
				onEnter: () => {
					overCard = true;
					clearTimeout(hideTimer);
				},
				onLeave: () => {
					overCard = false;
					scheduleHide();
				}
			}
		});
		// Above the dot; in the detail view right of the pointer, so the column's other layers stay
		// reachable. Markers cannot change their anchor, so the marker is replaced when switching.
		const cardMarkerFor = (side: boolean) =>
			new maplibregl.Marker(
				side
					? { element: cardElement, anchor: 'left', offset: [16, 0] }
					: { element: cardElement, anchor: 'bottom', offset: [0, -(iconSize / 2 + 4)] }
			)
				.setLngLat([0, 0])
				.addTo(map);
		cardElement.hidden = true;
		let cardMarker = cardMarkerFor(false);

		// The card stays while the pointer is on it. Map events reach the map through the card (it
		// sits in the canvas container), so they are ignored there and cannot hide or move it.
		let overCard = false;
		const onCard = (e: maplibregl.MapMouseEvent) =>
			e.originalEvent.target instanceof Element &&
			!!e.originalEvent.target.closest('[role=tooltip]');
		let hideTimer: ReturnType<typeof setTimeout>;
		function scheduleHide() {
			clearTimeout(hideTimer);
			if (overCard) return;
			// Long enough to move the pointer from the dot or column onto the card.
			hideTimer = setTimeout(() => {
				if (overCard) return;
				cardElement.hidden = true;
				card.point = undefined;
				card.layer = undefined;
				columns.highlight(undefined);
			}, 600);
		}
		async function show(id: string, lngLat: [number, number]) {
			clearTimeout(hideTimer);
			const point = byId.get(id);
			if (!point) return;
			if (card.point?.id !== id) {
				card.point = point;
				card.summary = summaryCache.get(id);
			}
			cardMarker.setLngLat(lngLat);
			cardElement.hidden = false;
			if (card.summary) return;
			try {
				const summary = await loadSummary(id);
				if (card.point?.id === id) card.summary = summary;
			} catch (e) {
				// Leave the placeholders; hovering again retries.
				notify.fromError(e, 'Could not load borehole details');
			}
		}
		const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
			const feature = e.features?.[0];
			if (!feature || onCard(e) || section.isDrawing) return;
			map.getCanvas().style.cursor = 'pointer';
			card.layer = undefined;
			void show(
				feature.properties.id as string,
				(feature.geometry as unknown as PointFeature['geometry']).coordinates
			);
		};
		const onLeave = (e: maplibregl.MapMouseEvent) => {
			map.getCanvas().style.cursor = '';
			if (!onCard(e)) scheduleHide();
		};
		map.on('mousemove', 'boreholes', onEnter);
		map.on('mouseleave', 'boreholes', onLeave);
		// Touch has no hover: a tap opens the card, a tap on the background closes it.
		map.on('click', 'boreholes', onEnter);
		map.on('click', (e) => {
			// Clicks on the card reach the map too: they must not close it
			if (onCard(e)) return;
			const layers = [detailActive ? COLUMNS_LAYER : 'boreholes'];
			if (!map.queryRenderedFeatures(e.point, { layers }).length) scheduleHide();
		});

		// --- detail view: columns instead of dots, on a tilted map
		const columns = new MapColumns(
			map,
			(bbox) => getServices().then(({ boreholes }) => boreholes.listColumns(bbox)),
			(error) => notify.fromError(error, 'Could not load borehole columns')
		);
		// The hovered segment is highlighted and shown in the card, which opens right of the pointer
		// and follows it from layer to layer, but not within a layer, so it can be reached.
		let cardLayerId: string | undefined;
		const onColumnMove = (e: maplibregl.MapLayerMouseEvent) => {
			const feature = e.features?.[0];
			if (!feature || onCard(e) || section.isDrawing) return;
			const segment = feature.properties as SegmentProperties;
			map.getCanvas().style.cursor = 'pointer';
			columns.highlight(segment.layerId);
			const moved = segment.layerId !== cardLayerId || cardElement.hidden;
			cardLayerId = segment.layerId;
			card.layer = {
				position: segment.position,
				top: segment.top,
				bottom: segment.bottom,
				label: segment.label,
				shortForm: segment.shortForm,
				color: segment.color
			};
			if (moved) void show(segment.boreholeId, [e.lngLat.lng, e.lngLat.lat]);
			else clearTimeout(hideTimer);
		};
		const onColumnLeave = (e: maplibregl.MapMouseEvent) => {
			map.getCanvas().style.cursor = '';
			if (onCard(e)) return;
			scheduleHide();
		};
		function setDetail(on: boolean) {
			if (on && map.getZoom() < DETAIL_MIN_ZOOM) {
				onDetailExit?.();
				return;
			}
			if (on === detailActive) return;
			detailActive = on;
			clearTimeout(hideTimer);
			cardElement.hidden = true;
			card.point = undefined;
			card.layer = undefined;
			cardLayerId = undefined;
			overCard = false;
			cardMarker.remove();
			cardMarker = cardMarkerFor(on);
			if (on) {
				columns.show();
				map.on('mousemove', COLUMNS_LAYER, onColumnMove);
				map.on('mouseleave', COLUMNS_LAYER, onColumnLeave);
				map.on('click', COLUMNS_LAYER, onColumnMove);
				const bearing = map.getBearing() === 0 ? DETAIL_BEARING : map.getBearing();
				map.easeTo({ pitch: DETAIL_PITCH, bearing, duration: 800 });
			} else {
				map.off('mousemove', COLUMNS_LAYER, onColumnMove);
				map.off('mouseleave', COLUMNS_LAYER, onColumnLeave);
				map.off('click', COLUMNS_LAYER, onColumnMove);
				columns.hide();
				map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
			}
			update();
			showSection(currentLine);
		}

		// --- section line: preview with the caught boreholes (rings on dots, sleeves on columns)
		let currentLine: SectionLine | undefined;
		function showSection(line: SectionLine | undefined) {
			currentLine = line;
			section.setLine(line);
			const caught = line
				? points.filter((p) => project(line, [p.lon, p.lat]).offset <= CORRIDOR_M)
				: [];
			section.setCaught(
				caught.map((p) => [p.lon, p.lat]),
				!detailActive
			);
			columns.mark(new Set(caught.map((p) => p.id)));
		}
		function setDrawing(on: boolean) {
			if (on) {
				clearTimeout(hideTimer);
				cardElement.hidden = true;
				section.startDrawing(
					(line) => onSectionDrawn?.(line),
					() => onSectionDrawCancel?.()
				);
			} else section.stopDrawing();
		}
		// Too far out for columns: back to the flat map with dots.
		const onZoomEnd = () => {
			if (!detailActive || map.getZoom() >= DETAIL_MIN_ZOOM) return;
			setDetail(false);
			onDetailExit?.();
			notify.info(
				'Detail view closed',
				`Zoom in to level ${DETAIL_MIN_ZOOM} or closer to see borehole columns.`
			);
		};
		map.on('zoomend', onZoomEnd);
		applyDetail = setDetail;
		setDetail(detail);
		applySection = showSection;
		showSection(sectionLine);
		applyDrawing = setDrawing;
		setDrawing(drawingSection);

		cleanups.push(() => {
			clearTimeout(hideTimer);
			active = false;
			redrawDots = undefined;
			applyDetail = undefined;
			applySection = undefined;
			applyDrawing = undefined;
			section.remove();
			map.off('zoomend', onZoomEnd);
			columns.hide();
			clearTimeout(refreshTimer);
			markers.forEach((marker) => marker.remove());
			cardMarker.remove();
			unmount(cardComponent);
		});
	}
	/* eslint-enable svelte/prefer-svelte-reactivity */

	$effect(() => {
		const map = new maplibregl.Map({
			container,
			style: {
				version: 8,
				sources: {
					osm: {
						type: 'raster',
						tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
						tileSize: 256,
						attribution: '&copy; OpenStreetMap contributors'
					}
				},
				layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
			},
			center: initialView ? [initialView.lon, initialView.lat] : [9.0, 48.5],
			zoom: initialView?.zoom ?? 6,
			cooperativeGestures: cooperative,
			// Needed to take a snapshot of the embedded map when handing over to the big one.
			canvasContextAttributes: { preserveDrawingBuffer: cooperative }
		});
		mapInstance = map;
		map.once('idle', () => onReady?.());
		const currentView = (): MapView => {
			const { lat, lng } = map.getCenter();
			return { lat, lon: lng, zoom: map.getZoom() };
		};
		map.on('moveend', () => onViewChange?.(currentView()));
		map.on('click', (e) => {
			// Markers and controls are not the background.
			if (e.originalEvent.target instanceof HTMLCanvasElement) onMapClick?.(currentView());
		});

		map.addControl(new maplibregl.NavigationControl(), 'top-right');
		// Show the user's position as a dot, and move there if asked to.
		const dot = document.createElement('div');
		dot.className = 'size-4 rounded-full border-2 border-white shadow-md';
		dot.style.background = mapColors.location;
		dot.style.boxShadow = `0 0 0 6px ${mapColors.location}40`;
		dot.setAttribute('aria-label', 'Your location');
		const userMarker = new maplibregl.Marker({ element: dot });
		const showUser = (position: [number, number], move: boolean) => {
			userMarker.setLngLat(position).addTo(map);
			if (move) {
				centered = true;
				map.easeTo({ center: position, zoom: 10 });
			}
		};
		const follow = centerOnUser && !initialView;
		// Set once the map moved to the user, so the later arriving points do not fit the view over it.
		let centered = false;
		if (lastPosition) showUser(lastPosition, false);
		const locate = () =>
			navigator.geolocation?.getCurrentPosition(
				({ coords }) => {
					lastPosition = [coords.longitude, coords.latitude];
					showUser(lastPosition, follow);
				},
				() => {
					// Denied or unavailable: keep the fitted view and show no dot.
					if (follow) notify.warning('Location unavailable', 'Showing the default map view.');
				}
			);
		// The locate button always asks, so a denial is reported.
		locateNow = () => {
			if (!navigator.geolocation) {
				notify.warning('Location unavailable', 'This browser cannot determine your position.');
				return;
			}
			locating = true;
			navigator.geolocation.getCurrentPosition(
				({ coords }) => {
					locating = false;
					lastPosition = [coords.longitude, coords.latitude];
					userMarker.setLngLat(lastPosition).addTo(map);
					map.easeTo({ center: lastPosition, zoom: Math.max(map.getZoom(), 13) });
				},
				() => {
					locating = false;
					notify.warning('Location unavailable', 'Allow location access to find your position.');
				}
			);
		};
		// Only ask for permission when the map should move there; otherwise reuse a granted one.
		if (follow) locate();
		else
			navigator.permissions
				?.query({ name: 'geolocation' })
				.then((status) => status.state === 'granted' && locate())
				.catch(() => {});

		let disposed = false;
		const cleanups: (() => void)[] = [];
		// Sources can only be added once the style is loaded.
		const styleLoaded = new Promise<void>((resolve) => map.once('style.load', () => resolve()));
		void Promise.all([loadPoints(), styleLoaded]).then(([points]) => {
			if (!disposed) showPoints(map, points, cleanups, !initialView && !centered);
		});

		return () => {
			disposed = true;
			cleanups.forEach((cleanup) => cleanup());
			userMarker.remove();
			mapInstance = undefined;
			locateNow = undefined;
			map.remove();
		};
	});
</script>

<div class="relative size-full">
	<div bind:this={container} class="size-full"></div>
	{#if showLocate}
		<!-- Above the attribution, in line with the zoom controls. -->
		<button
			type="button"
			class="absolute right-2.5 bottom-9 z-10 btn-icon preset-filled-surface-50-950 shadow-md"
			title="Show my location"
			aria-label="Show my location"
			disabled={locating}
			onclick={() => locateNow?.()}
		>
			<LocateFixedIcon class="size-5 {locating ? 'animate-pulse' : ''}" />
		</button>
	{/if}
</div>
