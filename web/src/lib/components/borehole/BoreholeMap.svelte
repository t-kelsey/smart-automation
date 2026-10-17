<script module lang="ts">
	import type { BoreholeSummary, MapPoint } from '#lib/domain/borehole.ts';
	import { createServices } from '#lib/services/index.ts';

	// The last known position, so a freshly mounted map can show the user's dot immediately.
	let lastPosition: [number, number] | undefined;

	// Loaded in the browser only and shared by all maps, so navigating between them reuses the data.
	let servicesPromise: ReturnType<typeof createServices> | undefined;
	let pointsPromise: Promise<MapPoint[]> | undefined;
	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- plain cache, nothing renders from it
	const summaryCache = new Map<string, BoreholeSummary>();

	const getServices = () => (servicesPromise ??= createServices({ fetch: globalThis.fetch }));

	function loadPoints(): Promise<MapPoint[]> {
		pointsPromise ??= getServices()
			.then(({ boreholes }) => boreholes.listMapPoints())
			.catch((error) => {
				pointsPromise = undefined;
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
	import { mount, unmount } from 'svelte';
	import BoreholeHoverCard from '#lib/components/borehole/BoreholeHoverCard.svelte';
	import Supercluster from 'supercluster';
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
		/** Called once the map has rendered its first complete view. */
		onReady?: () => void;
	}

	let {
		padding = { top: 40, bottom: 40, left: 40, right: 40 },
		centerOnUser = false,
		initialView,
		cooperative = false,
		onMapClick,
		onViewChange,
		onReady
	}: Props = $props();

	let container: HTMLDivElement;
	let mapInstance: maplibregl.Map | undefined;

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
	function showPoints(map: maplibregl.Map, points: MapPoint[], cleanups: (() => void)[]) {
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
		if (!bounds.isEmpty() && !initialView)
			map.fitBounds(bounds, { padding, maxZoom: 14, duration: 0 });

		const index = new Supercluster<{ id: string }>({ radius: 50, maxZoom: 14 }).load(features);

		// --- single boreholes: one GeoJSON source with only the unclustered points in view
		const emptyCollection: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };
		map.addSource('boreholes', { type: 'geojson', data: emptyCollection });
		map.addLayer({
			id: 'boreholes',
			type: 'circle',
			source: 'boreholes',
			paint: {
				'circle-radius': 6,
				'circle-color': ['case', ['get', 'verified'], '#22c55e', '#3b82f6'],
				'circle-stroke-width': 2,
				'circle-stroke-color': '#ffffff'
			}
		});
		const source = map.getSource<maplibregl.GeoJSONSource>('boreholes');

		// --- clusters: plain button markers
		const clusterMarkers = new Map<number, maplibregl.Marker>();
		function createClusterMarker(clusterId: number, count: number, lngLat: [number, number]) {
			const element = document.createElement('button');
			element.type = 'button';
			element.textContent = count >= 1000 ? `${Math.round(count / 100) / 10}k` : String(count);
			element.setAttribute('aria-label', `Cluster of ${count} boreholes, click to zoom in`);
			element.className =
				'flex size-9 cursor-pointer items-center justify-center rounded-full border-2 border-white bg-primary-500 text-xs font-semibold text-white shadow-md';
			element.addEventListener('click', () =>
				map.easeTo({ center: lngLat, zoom: index.getClusterExpansionZoom(clusterId) })
			);
			return new maplibregl.Marker({ element }).setLngLat(lngLat).addTo(map);
		}

		function update() {
			const b = map.getBounds();
			const items = index.getClusters(
				[b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
				Math.round(map.getZoom())
			);
			const singles: GeoJSON.Feature[] = [];
			const clusterIds = new Set<number>();
			for (const item of items) {
				const properties = item.properties;
				if ('cluster' in properties && properties.cluster) {
					clusterIds.add(properties.cluster_id);
					if (!clusterMarkers.has(properties.cluster_id))
						clusterMarkers.set(
							properties.cluster_id,
							createClusterMarker(
								properties.cluster_id,
								properties.point_count,
								item.geometry.coordinates as [number, number]
							)
						);
				} else {
					const point = byId.get((properties as { id: string }).id);
					if (point)
						singles.push({
							type: 'Feature',
							geometry: item.geometry,
							properties: { id: point.id, verified: point.verified }
						});
				}
			}
			for (const [id, marker] of clusterMarkers) {
				if (clusterIds.has(id)) continue;
				marker.remove();
				clusterMarkers.delete(id);
			}
			source?.setData({ type: 'FeatureCollection', features: singles });
		}
		update();
		map.on('moveend', update);

		// --- the shared hover card
		const cardElement = document.createElement('div');
		cardElement.className = 'z-20';
		const card = $state<{ point?: MapPoint; summary?: BoreholeSummary }>({});
		const cardComponent = mount(BoreholeHoverCard, {
			target: cardElement,
			props: {
				get point() {
					return card.point;
				},
				get summary() {
					return card.summary;
				},
				onEnter: () => clearTimeout(hideTimer),
				onLeave: () => scheduleHide()
			}
		});
		const cardMarker = new maplibregl.Marker({
			element: cardElement,
			anchor: 'bottom',
			offset: [0, -12]
		});
		cardElement.hidden = true;
		cardMarker.setLngLat([0, 0]).addTo(map);

		let hideTimer: ReturnType<typeof setTimeout>;
		function scheduleHide() {
			clearTimeout(hideTimer);
			hideTimer = setTimeout(() => {
				cardElement.hidden = true;
				card.point = undefined;
			}, 250);
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
			} catch {
				// Leave the placeholders; hovering again retries.
			}
		}
		const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
			const feature = e.features?.[0];
			if (!feature) return;
			map.getCanvas().style.cursor = 'pointer';
			void show(
				feature.properties.id as string,
				(feature.geometry as unknown as PointFeature['geometry']).coordinates
			);
		};
		const onLeave = () => {
			map.getCanvas().style.cursor = '';
			scheduleHide();
		};
		map.on('mousemove', 'boreholes', onEnter);
		map.on('mouseleave', 'boreholes', onLeave);
		// Touch has no hover: a tap opens the card, a tap on the background closes it.
		map.on('click', 'boreholes', onEnter);
		map.on('click', (e) => {
			if (!map.queryRenderedFeatures(e.point, { layers: ['boreholes'] }).length) scheduleHide();
		});

		cleanups.push(() => {
			clearTimeout(hideTimer);
			clusterMarkers.forEach((marker) => marker.remove());
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
		dot.className = 'size-4 rounded-full border-2 border-white bg-blue-500 shadow-md';
		dot.setAttribute('aria-label', 'Your location');
		const userMarker = new maplibregl.Marker({ element: dot });
		const showUser = (position: [number, number], move: boolean) => {
			userMarker.setLngLat(position).addTo(map);
			if (move) map.easeTo({ center: position, zoom: 10 });
		};
		const follow = centerOnUser && !initialView;
		if (lastPosition) showUser(lastPosition, false);
		const locate = () =>
			navigator.geolocation?.getCurrentPosition(
				({ coords }) => {
					lastPosition = [coords.longitude, coords.latitude];
					showUser(lastPosition, follow);
				},
				() => {
					// Denied or unavailable: keep the fitted view and show no dot.
				}
			);
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
			if (!disposed) showPoints(map, points, cleanups);
		});

		return () => {
			disposed = true;
			cleanups.forEach((cleanup) => cleanup());
			userMarker.remove();
			mapInstance = undefined;
			map.remove();
		};
	});
</script>

<div bind:this={container} class="size-full"></div>
