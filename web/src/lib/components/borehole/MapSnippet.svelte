<script lang="ts">
	import { MapPinIcon } from '@lucide/svelte';

	interface Props {
		lat: number;
		lon: number;
	}

	let { lat, lon }: Props = $props();
</script>

<!-- TODO: replace the placeholder with a MapLibre map centred on the borehole. -->
<div
	class="relative aspect-video overflow-hidden rounded-lg border border-surface-300-700 bg-surface-100-900"
	role="img"
	aria-label="Map showing the borehole location"
>
	<svg class="absolute inset-0 size-full text-surface-300-700" aria-hidden="true">
		<defs>
			<pattern id="map-grid" width="32" height="32" patternUnits="userSpaceOnUse">
				<path d="M32 0 H0 V32" fill="none" stroke="currentColor" stroke-width="1" />
			</pattern>
		</defs>
		<rect width="100%" height="100%" fill="url(#map-grid)" />
	</svg>
	<MapPinIcon
		class="absolute top-1/2 left-1/2 size-8 -translate-x-1/2 -translate-y-full text-error-500"
	/>
	<span class="absolute right-2 bottom-2 rounded bg-surface-50-950/80 px-2 py-0.5 text-xs">
		{lat.toFixed(5)}, {lon.toFixed(5)}
	</span>
</div>
