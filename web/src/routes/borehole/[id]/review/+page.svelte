<script lang="ts">
	import { tick } from 'svelte';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import {
		BadgeCheckIcon,
		Columns2Icon,
		InfoIcon,
		ListIcon,
		SkipForwardIcon,
		Undo2Icon
	} from '@lucide/svelte';
	import BoreholePageHeader from '#lib/components/borehole/BoreholePageHeader.svelte';
	import CrossSection from '#lib/components/borehole/CrossSection.svelte';
	import HelpDrawer from '#lib/components/borehole/HelpDrawer.svelte';
	import PatternDefs from '#lib/components/borehole/PatternDefs.svelte';
	import { DocumentPane } from '#lib/components/document/index.ts';
	import CoreDataEditor from '#lib/components/review/CoreDataEditor.svelte';
	import LayerEditor from '#lib/components/review/LayerEditor.svelte';
	import { Review } from '#lib/components/review/review.ts';
	import { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let borehole = $derived(data.borehole);
	let review = $derived(new Review(borehole, data.service));

	let tab = $state('core-data');
	// Keyed by id only, so that reloading the borehole after an edit keeps the highlight.
	let boreholeId = $derived(borehole.id);
	// Click selection is stored per borehole, so it carries over between details and review.
	let selection = $derived(new LayerSelection(boreholeId));
	$effect(() => selection.restore());

	// The document follows the hovered field or layer.
	let hoveredLayer = $derived(borehole.layers.find((l) => l.id === selection.hoveredId));
	let source = $derived(selection.source ?? hoveredLayer?.source ?? null);

	let openFlags = $derived(borehole.flags.filter((f) => !f.resolvedAt));
	let flagIndex = 0;

	/** Walks the open flags: shows the field's tab, scrolls to and focuses it, shows its source. */
	async function nextFlag() {
		const flag = openFlags[flagIndex++ % openFlags.length];
		if (!flag) return;
		tab = flag.layerId ? 'layers' : 'core-data';
		selection.showSource(review.source(flag.field, flag.layerId));
		await tick();
		const scope = flag.layerId ?? 'borehole';
		const target =
			document.querySelector(`[data-review-target="${scope}:${flag.field}"]`) ??
			document.querySelector(`[data-review-target="${scope}:*"]`);
		target?.scrollIntoView({ block: 'center', behavior: 'smooth' });
		target?.querySelector<HTMLElement>('input, button')?.focus({ preventScroll: true });
	}

	function setVerified(verified: boolean) {
		const n = openFlags.length;
		if (
			verified &&
			n &&
			!confirm(`${n} open ${n === 1 ? 'flag is' : 'flags are'} left. Release the borehole anyway?`)
		)
			return;
		void review.run((s) => s.setVerified(borehole.id, verified));
	}
</script>

<svelte:head>
	<title>Review {borehole.name}</title>
</svelte:head>

<PatternDefs />

<div class="-m-6 flex h-screen flex-col">
	<BoreholePageHeader {borehole} view="review">
		<button
			type="button"
			class="btn preset-tonal-warning"
			disabled={!openFlags.length}
			title="Go to the next open flag"
			onclick={nextFlag}
		>
			<SkipForwardIcon class="size-4" />
			Next flag
		</button>
		{#if borehole.verified}
			<button type="button" class="btn preset-tonal" onclick={() => setVerified(false)}>
				<Undo2Icon class="size-4" />
				Withdraw release
			</button>
		{:else}
			<button type="button" class="btn preset-filled-success-500" onclick={() => setVerified(true)}>
				<BadgeCheckIcon class="size-4" />
				Verify & release
			</button>
		{/if}
		<HelpDrawer layers={borehole.layers} />
	</BoreholePageHeader>

	<div class="grid min-h-0 flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-2">
		<!-- Extracted data, edited in place -->
		<Tabs
			value={tab}
			onValueChange={(details) => (tab = details.value)}
			class="flex min-h-0 flex-col card border border-surface-200-800 bg-surface-50-950"
		>
			<Tabs.List class="px-4 pt-2">
				<Tabs.Trigger value="core-data" class="flex items-center gap-2">
					<InfoIcon class="size-4" />
					Core data
				</Tabs.Trigger>
				<Tabs.Trigger value="cross-section" class="flex items-center gap-2">
					<Columns2Icon class="size-4" />
					Cross section
				</Tabs.Trigger>
				<Tabs.Trigger value="layers" class="flex items-center gap-2">
					<ListIcon class="size-4" />
					Layers
				</Tabs.Trigger>
				<Tabs.Indicator />
			</Tabs.List>
			<div class="min-h-0 flex-1 overflow-y-auto p-4">
				<Tabs.Content value="core-data">
					<CoreDataEditor {review} {selection} />
				</Tabs.Content>
				<Tabs.Content value="cross-section" class="h-full">
					<CrossSection {borehole} {selection} flagOf={review.layerSeverity} />
				</Tabs.Content>
				<Tabs.Content value="layers">
					<LayerEditor {review} {selection} />
				</Tabs.Content>
			</div>
		</Tabs>

		<!-- Original document, with the additional files to switch to -->
		<DocumentPane documents={borehole.documents} {source} class="min-h-0" />
	</div>
</div>
