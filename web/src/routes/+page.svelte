<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import {
		ArrowRight,
		InfoIcon,
		LayersIcon,
		ListIcon,
		MapIcon,
		ScanTextIcon,
		SearchIcon
	} from '@lucide/svelte';
	import BoreholeTable from '#lib/components/borehole/BoreholeTable.svelte';
	import { notify } from '#lib/components/toast/index.ts';
	import BoreholeMap from '#lib/components/borehole/BoreholeMap.svelte';
	import { getLastMapView, setLastMapView, setMapSnapshot } from '#lib/map-handoff.svelte.ts';
	import type { Snippet } from 'svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	$effect(() => {
		if (data.loadError) notify.fromError(data.loadError, 'Could not load boreholes');
	});

	// Continues where the user left a map (this one or /map). Read once: later moves are saved but
	// must not re-centre the map.
	const initialMapView = getLastMapView();

	const features = [
		{ icon: ScanTextIcon, label: 'OCR and extraction of multilingual logs' },
		{ icon: LayersIcon, label: 'Depth, lithology and stratigraphy per layer' },
		{ icon: MapIcon, label: 'Map and borehole profiles after DIN 4023' },
		{ icon: SearchIcon, label: 'Search to find the right log quickly' }
	];

	let expanding = $state(false);
	let mapCard = $state<HTMLElement>();
	let mapHost = $state<HTMLElement>();
	let mapBox = $state<HTMLElement>();
	let mapRef = $state<ReturnType<typeof BoreholeMap>>();

	// Let the map card itself grow to fill the viewport with a linear animation, then navigate.
	async function openMap(view: { lat: number; lon: number; zoom: number }) {
		if (expanding) return;
		// Hand the current view over so the big map continues where the small one is.
		const query = new URLSearchParams(Object.entries(view).map(([k, v]) => [k, String(v)]));
		const target = `${resolve('/map')}?${query}`;
		if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
			// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved above, only a query is added
			await goto(target);
			return;
		}
		const card = mapCard;
		const host = mapHost;
		const box = mapBox;
		if (!card || !host || !box) return;
		expanding = true;
		const rect = card.getBoundingClientRect();
		const hostRect = host.getBoundingClientRect();
		const { innerWidth: vw, innerHeight: vh } = window;
		// The header above the map fades out; the map area ends up at the top of the viewport.
		const headerHeight = hostRect.top - rect.top;

		// Resizing the map every frame makes it flicker. Resize it once to its final size instead and
		// slide it so the map area keeps showing the same centre; the card then only reveals more of it.
		Object.assign(box.style, {
			inset: 'auto',
			top: '0',
			left: '0',
			width: `${vw}px`,
			height: `${vh}px`
		});
		const fromX = (hostRect.width - vw) / 2;
		const fromY = (hostRect.height - vh) / 2;
		box.style.translate = `${fromX}px ${fromY}px`;

		// Take the card out of the grid flow; its wrapper keeps the cell's space.
		Object.assign(card.style, {
			position: 'fixed',
			top: `${rect.top}px`,
			left: `${rect.left}px`,
			width: `${rect.width}px`,
			height: `${rect.height}px`,
			// Above the other cards, below the sidebar (z-10).
			zIndex: '5'
		});
		const timing: KeyframeAnimationOptions = { duration: 500, easing: 'linear', fill: 'forwards' };
		box.animate(
			[{ translate: `${fromX}px ${fromY}px` }, { translate: `0px ${-headerHeight}px` }],
			timing
		);
		await card.animate(
			{ top: '0px', left: '0px', width: '100vw', height: '100vh', borderRadius: '0px' },
			timing
		).finished;
		// The big map starts empty; let it show this picture until its own tiles are drawn.
		setMapSnapshot(mapRef?.snapshot());
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved above, only a query is added
		await goto(target);
	}
</script>

<svelte:head>
	<title>Dashboard · Borehole Atlas</title>
</svelte:head>

{#snippet openLabel()}
	Open
	<ArrowRight
		class="size-4 transition-transform duration-300 ease-linear group-hover:translate-x-1"
	/>
{/snippet}

{#snippet cardHeader(Icon: typeof MapIcon, title: string, subtitle: string, action: Snippet)}
	<div class="flex items-center gap-3 border-b border-surface-200-800 px-5 py-3">
		<span class="flex size-9 items-center justify-center rounded-lg preset-filled-primary-500">
			<Icon class="size-5" />
		</span>
		<div class="min-w-0 flex-1">
			<h2 class="h5 leading-tight">{title}</h2>
			<p class="truncate text-xs opacity-70">{subtitle}</p>
		</div>
		{@render action()}
	</div>
{/snippet}

{#snippet staticAction()}
	<span class="flex items-center gap-1 text-sm font-semibold text-primary-500">
		{@render openLabel()}
	</span>
{/snippet}

{#snippet listAction()}
	<a
		href={resolve('/borehole')}
		class="flex items-center gap-1 text-sm font-semibold text-primary-500 hover:underline"
	>
		{@render openLabel()}
	</a>
{/snippet}

{#snippet aboutCard(classes: string)}
	<div class={classes}>
		<a
			href={resolve('/about')}
			class="group flex size-full flex-col overflow-hidden card preset-filled-surface-100-900 shadow-sm transition-shadow duration-300 ease-linear hover:shadow-xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
		>
			{@render cardHeader(InfoIcon, 'About', 'Borehole Atlas', staticAction)}
			<div class="space-y-3 p-5 text-sm">
				<p>
					Turns legacy borehole logs, from scanned paper to native digital, into a structured,
					searchable geodatabase that feeds real geology into tunnel design.
				</p>
				<ul class="grid gap-x-6 gap-y-2 opacity-80 sm:grid-cols-2">
					{#each features as feature (feature.label)}
						<li class="flex items-center gap-2">
							<feature.icon class="size-4 shrink-0 text-primary-500" />
							{feature.label}
						</li>
					{/each}
				</ul>
			</div>
		</a>
	</div>
{/snippet}

<div class="h-full">
	<nav
		class="grid h-full min-h-[44rem] gap-6 lg:min-h-0 lg:grid-cols-2 lg:grid-rows-2"
		aria-label="Main sections"
	>
		<!-- Clicking the map background opens the big map at the same view. -->
		<div class="min-h-80 lg:row-span-2">
			<section
				bind:this={mapCard}
				class="group flex size-full flex-col overflow-hidden card preset-filled-surface-100-900 shadow-sm will-change-[top,left,width,height]"
				class:pointer-events-none={expanding}
			>
				<div bind:this={mapHost} class="relative min-h-0 flex-1 overflow-hidden">
					<div bind:this={mapBox} class="absolute inset-0">
						<BoreholeMap
							bind:this={mapRef}
							initialView={initialMapView}
							centerOnUser
							cooperative
							onMapClick={openMap}
							onViewChange={setLastMapView}
						/>
					</div>
				</div>
			</section>
		</div>
		{@render aboutCard('min-h-60')}
		<!-- The rows link to the detail pages, so the card is not a link itself; only "Open" is. -->
		<section
			class="group relative flex min-h-80 flex-col overflow-hidden card preset-filled-surface-100-900 shadow-sm"
		>
			{@render cardHeader(ListIcon, 'Boreholes', 'Latest logs', listAction)}
			<div class="relative min-h-0 flex-1 overflow-hidden">
				<BoreholeTable items={data.boreholes} />
				<div class="fade"></div>
			</div>
		</section>
	</nav>
</div>

<style>
	/* Fade out the cropped preview towards the card's bottom edge. */
	.fade {
		position: absolute;
		inset: auto 0 0 0;
		height: 4rem;
		background: linear-gradient(to bottom, transparent, var(--color-surface-100-900));
		pointer-events: none;
	}
</style>
