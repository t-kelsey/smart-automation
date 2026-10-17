<script lang="ts">
	import 'maplibre-gl/dist/maplibre-gl.css';
	import * as maplibregl from 'maplibre-gl';
	import { mount, unmount } from 'svelte';
	import BoreholeMarker from '#lib/components/borehole/BoreholeMarker.svelte';
	import Supercluster from 'supercluster';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import type { BoreholeSummary } from '#lib/domain/borehole.ts';
	import type { PageProps } from './$types';

	interface PointFeature {
		type: 'Feature';
		properties: { id: string };
		geometry: { type: 'Point'; coordinates: [number, number] };
	}

	let { data }: PageProps = $props();

	let container: HTMLDivElement;

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
			center: [9.0, 48.5],
			zoom: 6
		});
		map.addControl(new maplibregl.NavigationControl(), 'top-right');

		const bounds = new maplibregl.LngLatBounds();
		const byId = new SvelteMap<string, BoreholeSummary>();
		const points: PointFeature[] = [];
		for (const borehole of data.boreholes) {
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
		if (!bounds.isEmpty())
			map.fitBounds(bounds, {
				padding: { top: 80, bottom: 80, left: 340, right: 80 },
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
			visible.forEach((entry) => entry.destroy());
			map.remove();
		};
	});
</script>

<!-- Fill the whole viewport; the sidebar (z-10) floats above the map. -->
<div class="fixed inset-0 z-0">
	<!-- MapLibre sets position: relative on its container, so it can't be the fixed element. -->
	<div bind:this={container} class="h-full w-full"></div>
</div>
