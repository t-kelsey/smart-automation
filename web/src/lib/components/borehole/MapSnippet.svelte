<script lang="ts">
	import 'maplibre-gl/dist/maplibre-gl.css';
	import * as maplibregl from 'maplibre-gl';

	interface Props {
		lat: number;
		lon: number;
	}

	let { lat, lon }: Props = $props();

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
			center: [lon, lat],
			zoom: 13,
			attributionControl: { compact: true }
		});
		map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
		const marker = new maplibregl.Marker({ color: '#dc2626' }).setLngLat([lon, lat]).addTo(map);

		return () => {
			marker.remove();
			map.remove();
		};
	});
</script>

<div
	bind:this={container}
	class="aspect-video overflow-hidden rounded-lg border border-surface-300-700"
	role="img"
	aria-label="Map showing the borehole location"
></div>
