<script lang="ts">
	import { page } from '$app/state';
	import { pushState, replaceState } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { untrack } from 'svelte';
	import { BoxIcon, PaintBucketIcon, RulerIcon, XIcon } from '@lucide/svelte';
	import SectionView from '#lib/components/section/SectionView.svelte';
	import {
		formatSectionParam,
		lineLength,
		parseSectionParam,
		type SectionLine
	} from '#lib/borehole-columns/section.ts';
	import BoreholeMap from '#lib/components/borehole/BoreholeMap.svelte';
	import MapHelpDrawer from '#lib/components/borehole/MapHelpDrawer.svelte';
	import MapLegend from '#lib/components/borehole/MapLegend.svelte';
	import { DETAIL_MIN_ZOOM } from '#lib/components/borehole/map-columns.ts';
	import { setLastMapView, takeMapSnapshot } from '#lib/map-handoff.svelte.ts';
	// Picture of the dashboard map; covers the first frames, then fades out once the map is drawn.
	const cover = takeMapSnapshot();
	let ready = $state(false);
	let showFill = $state(false);
	// 3D view with boreholes as columns; only from DETAIL_MIN_ZOOM on (the map leaves it below).
	let detail = $state(false);

	// ?lat=&lon=&zoom= start the map at a given view, e.g. when opened from the dashboard or a shared
	// link. Read once: the map keeps the URL in sync while moving and must not restart because of it.
	const initialView = untrack(() => {
		const params = page.url.searchParams;
		const [lat, lon, zoom] = ['lat', 'lon', 'zoom'].map((key) => Number(params.get(key) ?? NaN));
		return [lat, lon, zoom].every(Number.isFinite) ? { lat, lon, zoom } : undefined;
	});

	// --- section: drawn on the map, previewed with its corridor, then opened full screen.
	// `section=lon1,lat1,lon2,lat2` in the URL opens it; opening pushes a history entry (Back closes).
	const urlSection = untrack(() => parseSectionParam(page.url.searchParams.get('section')));
	let drawingSection = $state(false);
	let sectionLine = $state<SectionLine | undefined>(urlSection);
	let openLine = $derived(
		parseSectionParam(page.state.section ?? page.url.searchParams.get('section'))
	);

	function sectionDrawn(line: SectionLine) {
		drawingSection = false;
		sectionLine = line;
	}
	function openSection() {
		if (!sectionLine) return;
		const value = formatSectionParam(sectionLine);
		// The live URL (syncUrl keeps the view in it, outside SvelteKit's page.url).
		const url = new URL(location.href);
		url.searchParams.set('section', value);
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved path plus this page's query
		pushState(resolve('/map') + url.search, { section: value });
	}
	function closeSection() {
		// Opened here: go back to the entry before. Opened from a link or reload: drop the parameter.
		if (page.state.section) {
			history.back();
			return;
		}
		const url = new URL(location.href);
		url.searchParams.delete('section');
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved path plus this page's query
		replaceState(resolve('/map') + url.search, {});
	}
	function clearSection() {
		sectionLine = undefined;
		drawingSection = false;
	}

	let zoom = $state(untrack(() => initialView?.zoom ?? 0));
	let detailAvailable = $derived(zoom >= DETAIL_MIN_ZOOM);

	// Keep the URL on the current view so that it can always be shared.
	function syncUrl(view: { lat: number; lon: number; zoom: number }) {
		zoom = view.zoom;
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

<!-- Fill the whole viewport; the sidebar (z-10) floats above the map. Hidden, but kept, while the
	section is open. -->
<div class="fixed inset-0 z-0" class:invisible={!!openLine}>
	<BoreholeMap
		{initialView}
		onViewChange={syncUrl}
		showLocate
		{showFill}
		{detail}
		onDetailExit={() => (detail = false)}
		{drawingSection}
		{sectionLine}
		onSectionDrawn={sectionDrawn}
		onSectionDrawCancel={() => (drawingSection = false)}
		onReady={() => (ready = true)}
		padding={{ top: 80, bottom: 80, left: 340, right: 80 }}
	/>
	<!-- Left of the zoom controls. -->
	<div class="absolute top-2.5 right-14 z-10 flex items-center gap-2" class:hidden={!!openLine}>
		<button
			type="button"
			class="btn shadow-md btn-sm {drawingSection
				? 'preset-filled-primary-500'
				: 'preset-filled-surface-50-950'}"
			aria-pressed={drawingSection}
			title="Draw a line to see the boreholes along it side by side"
			onclick={() => (drawingSection = !drawingSection)}
		>
			<RulerIcon class="size-4" />
			Section
		</button>
		<button
			type="button"
			class="btn shadow-md btn-sm {detail
				? 'preset-filled-primary-500'
				: 'preset-filled-surface-50-950'}"
			aria-pressed={detail}
			disabled={!detail && !detailAvailable}
			title={detail || detailAvailable
				? 'Show boreholes as 3D columns of their layers'
				: `Zoom in to level ${DETAIL_MIN_ZOOM} to use the detail view`}
			onclick={() => (detail = !detail)}
		>
			<BoxIcon class="size-4" />
			Detail view
		</button>
		<button
			type="button"
			disabled={detail}
			class="btn shadow-md btn-sm {showFill
				? 'preset-filled-primary-500'
				: 'preset-filled-surface-50-950'}"
			aria-pressed={showFill}
			onclick={() => (showFill = !showFill)}
		>
			<PaintBucketIcon class="size-4" />
			Fill: {showFill ? 'on' : 'off'}
		</button>
		<MapHelpDrawer />
	</div>
	{#if drawingSection && !openLine}
		<p
			class="absolute top-16 left-1/2 z-10 -translate-x-1/2 rounded-full bg-surface-50-950 px-4 py-1.5 text-sm shadow-md"
		>
			Click the start, then the end of the section line · Esc to cancel
		</p>
	{:else if sectionLine && !openLine}
		<div
			class="absolute bottom-8 left-1/2 z-10 flex -translate-x-1/2 items-center gap-3 rounded-full bg-surface-50-950 py-1.5 pr-1.5 pl-4 text-sm shadow-md"
		>
			<span>Section line · {Math.round(lineLength(sectionLine))} m</span>
			<button type="button" class="btn preset-filled-primary-500 btn-sm" onclick={openSection}>
				Show section
			</button>
			<button
				type="button"
				class="btn-icon preset-tonal btn-icon-sm"
				aria-label="Remove the section line"
				title="Remove the section line"
				onclick={clearSection}
			>
				<XIcon class="size-4" />
			</button>
		</div>
	{/if}
	<!-- Bottom right, above the locate button. -->
	<div class="absolute right-2.5 bottom-20 z-10" class:hidden={!!openLine}>
		<MapLegend {showFill} showColumns={detail} />
	</div>
	{#if cover}
		<img
			src={cover}
			alt=""
			class="pointer-events-none absolute inset-0 size-full transition-opacity duration-300 ease-linear"
			class:opacity-0={ready}
		/>
	{/if}
</div>

<!-- The section replaces the map (which stays mounted underneath); the sidebar stays beside it. -->
{#if openLine}
	<div class="relative z-[5] -m-6 h-[calc(100%+3rem)] bg-surface-100-900 p-6">
		<SectionView line={openLine} onClose={closeSection} />
	</div>
{/if}
