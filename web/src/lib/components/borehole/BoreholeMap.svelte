<script module lang="ts">
	// The last known position, so a freshly mounted map can show the user's dot immediately.
	let lastPosition: [number, number] | undefined;
</script>

<script lang="ts">
	import 'maplibre-gl/dist/maplibre-gl.css';
	import * as maplibregl from 'maplibre-gl';
	import { mount, unmount } from 'svelte';
	import BoreholeMarker from '#lib/components/borehole/BoreholeMarker.svelte';
	import Supercluster from 'supercluster';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import type { BoreholeSummary } from '#lib/domain/borehole.ts';

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
		boreholes: BoreholeSummary[];
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
		boreholes,
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

		const bounds = new maplibregl.LngLatBounds();
		const byId = new SvelteMap<string, BoreholeSummary>();
		const points: PointFeature[] = [];
		for (const borehole of boreholes) {
			if (!borehole.location) continue;
			const lngLat: [number, number] = [borehole.location.lon, borehole.location.lat];
			byId.set(borehole.id, borehole);
			bounds.extend(lngLat);
			points.push({
				type: 'Feature',
				properties: { id: borehole.id },
				geometry: { type: 'Point', coordinates: lngLat }
			});
		}
		if (!bounds.isEmpty() && !initialView)
			map.fitBounds(bounds, {
				padding,
				maxZoom: 14,
				duration: 0
			});

		const index = new Supercluster<{ id: string }>({ radius: 50, maxZoom: 14 }).load(points);

		// Markers currently on the map, keyed by cluster or borehole id.
		const visible = new SvelteMap<string, { destroy: () => void }>();

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
			const marker = new maplibregl.Marker({ element }).setLngLat(lngLat).addTo(map);
			return { destroy: () => marker.remove() };
		}

		function createBoreholeMarker(borehole: BoreholeSummary, lngLat: [number, number]) {
			const element = document.createElement('div');
			const component = mount(BoreholeMarker, { target: element, props: { borehole } });
			const marker = new maplibregl.Marker({ element }).setLngLat(lngLat).addTo(map);
			return {
				destroy: () => {
					marker.remove();
					unmount(component);
				}
			};
		}

		// Sync the HTML markers with the clusters and single points in the viewport.
		function updateMarkers() {
			const b = map.getBounds();
			const clusters = index.getClusters(
				[b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
				Math.round(map.getZoom())
			);
			const next = new SvelteSet<string>();
			for (const feature of clusters) {
				const lngLat = feature.geometry.coordinates as [number, number];
				const properties = feature.properties;
				if ('cluster' in properties && properties.cluster) {
					const key = `c:${properties.cluster_id}`;
					next.add(key);
					if (!visible.has(key))
						visible.set(
							key,
							createClusterMarker(properties.cluster_id, properties.point_count, lngLat)
						);
				} else {
					const borehole = byId.get((properties as { id: string }).id);
					if (!borehole) continue;
					const key = `b:${borehole.id}`;
					next.add(key);
					if (!visible.has(key)) visible.set(key, createBoreholeMarker(borehole, lngLat));
				}
			}
			for (const [key, entry] of visible) {
				if (next.has(key)) continue;
				entry.destroy();
				visible.delete(key);
			}
		}

		updateMarkers();
		map.on('moveend', updateMarkers);

		return () => {
			userMarker.remove();
			mapInstance = undefined;
			visible.forEach((entry) => entry.destroy());
			map.remove();
		};
	});
</script>

<div bind:this={container} class="size-full"></div>
