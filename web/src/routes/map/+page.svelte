<script lang="ts">
	import { page } from '$app/state';
	import BoreholeMap from '#lib/components/borehole/BoreholeMap.svelte';
	import { takeMapSnapshot } from '#lib/map-handoff.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// Picture of the dashboard map; covers the first frames, then fades out once the map is drawn.
	const cover = takeMapSnapshot();
	let ready = $state(false);

	// Optional ?lat=&lon=&zoom= start the map at a given view, e.g. when opened from the dashboard.
	const initialView = $derived.by(() => {
		const params = page.url.searchParams;
		const [lat, lon, zoom] = ['lat', 'lon', 'zoom'].map((key) => Number(params.get(key) ?? NaN));
		return [lat, lon, zoom].every(Number.isFinite) ? { lat, lon, zoom } : undefined;
	});
</script>

<!-- Fill the whole viewport; the sidebar (z-10) floats above the map. -->
<div class="fixed inset-0 z-0">
	<BoreholeMap
		boreholes={data.boreholes}
		{initialView}
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
