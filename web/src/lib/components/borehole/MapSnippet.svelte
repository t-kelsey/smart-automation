<script lang="ts">
	import 'maplibre-gl/dist/maplibre-gl.css';
	import * as maplibregl from 'maplibre-gl';

	interface Props {
		/** The point to mark; without it the whole world is shown. */
		lat?: number;
		lon?: number;
		/** Makes the map a picker: a click reports its position (and marks it). */
		onpick?: (lon: number, lat: number) => void;
	}

	let { lat, lon, onpick }: Props = $props();

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
			center: lat === undefined || lon === undefined ? [0, 20] : [lon, lat],
			zoom: lat === undefined || lon === undefined ? 1 : 13,
			attributionControl: { compact: true }
		});
		map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
		const marker = new maplibregl.Marker({ color: '#dc2626' });
		if (lat !== undefined && lon !== undefined) marker.setLngLat([lon, lat]).addTo(map);
		if (onpick) {
			map.getCanvas().style.cursor = 'crosshair';
			map.on('click', (event) => {
				marker.setLngLat(event.lngLat).addTo(map);
				onpick(event.lngLat.lng, event.lngLat.lat);
			});
		}

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
	aria-label={onpick
		? 'Map: click the rough area of the borehole'
		: 'Map showing the borehole location'}
></div>
