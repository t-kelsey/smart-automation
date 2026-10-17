<script lang="ts">
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import BoreholeMap from '#lib/components/borehole/BoreholeMap.svelte';
	import { setLastMapView, takeMapSnapshot } from '#lib/map-handoff.ts';
	// Picture of the dashboard map; covers the first frames, then fades out once the map is drawn.
	const cover = takeMapSnapshot();
	let ready = $state(false);

	// ?lat=&lon=&zoom= start the map at a given view, e.g. when opened from the dashboard or a shared
	// link. Read once: the map keeps the URL in sync while moving and must not restart because of it.
	const initialView = untrack(() => {
		const params = page.url.searchParams;
		const [lat, lon, zoom] = ['lat', 'lon', 'zoom'].map((key) => Number(params.get(key) ?? NaN));
		return [lat, lon, zoom].every(Number.isFinite) ? { lat, lon, zoom } : undefined;
	});

	// Keep the URL on the current view so that it can always be shared.
	function syncUrl(view: { lat: number; lon: number; zoom: number }) {
		setLastMapView(view);
		const url = new URL(page.url.href);
		url.searchParams.set('lat', view.lat.toFixed(5));
		url.searchParams.set('lon', view.lon.toFixed(5));
		url.searchParams.set('zoom', view.zoom.toFixed(2));
		// Written straight to the history entry, keeping SvelteKit's own state: SvelteKit's shallow
		// `goto` did not stick, and going back from a detail page then showed the first view again.
		history.replaceState(history.state, '', url);
	}
</script>

<!-- Fill the whole viewport; the sidebar (z-10) floats above the map. -->
<div class="fixed inset-0 z-0">
	<BoreholeMap
		{initialView}
		onViewChange={syncUrl}
		onReady={() => (ready = true)}
		padding={{ top: 80, bottom: 80, left: 340, right: 80 }}
	/>
	{#if cover}
		<img
			src={cover}
			alt=""
			class="pointer-events-none absolute inset-0 size-full transition-opacity duration-300 ease-linear"
			class:opacity-0={ready}
		/>
	{/if}
</div>
