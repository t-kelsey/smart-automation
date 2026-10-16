<script lang="ts">
	import 'maplibre-gl/dist/maplibre-gl.css';
	import * as maplibregl from 'maplibre-gl';

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

		return () => map.remove();
	});
</script>

<!-- Fill the whole viewport; the sidebar (z-10) floats above the map. -->
<div class="fixed inset-0 z-0">
	<!-- MapLibre sets position: relative on its container, so it can't be the fixed element. -->
	<div bind:this={container} class="h-full w-full"></div>
</div>
