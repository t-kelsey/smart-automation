<script lang="ts">
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import { Columns2Icon, InfoIcon, ListIcon } from '@lucide/svelte';
	import BoreholePageHeader from '#lib/components/borehole/BoreholePageHeader.svelte';
	import CoreData from '#lib/components/borehole/CoreData.svelte';
	import CrossSection from '#lib/components/borehole/CrossSection.svelte';
	import HelpDrawer from '#lib/components/borehole/HelpDrawer.svelte';
	import LayersTable from '#lib/components/borehole/LayersTable.svelte';
	import PatternDefs from '#lib/components/borehole/PatternDefs.svelte';
	import { DocumentPane } from '#lib/components/document/index.ts';
	import { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let borehole = $derived(data.borehole);

	let tab = $state('cross-section');
	// Click selection is stored per borehole, so it carries over between details and review.
	let selection = $derived(new LayerSelection(borehole.id));
	$effect(() => selection.restore());
</script>

<svelte:head>
	<title>Review {borehole.name}</title>
</svelte:head>

<PatternDefs />

<div class="-m-6 flex h-screen flex-col">
	<BoreholePageHeader {borehole} view="review">
		<HelpDrawer layers={borehole.layers} />
	</BoreholePageHeader>

	<div class="grid min-h-0 flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-2">
		<!-- Extracted data -->
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
					<CoreData {borehole} />
				</Tabs.Content>
				<Tabs.Content value="cross-section" class="h-full">
					<CrossSection {borehole} {selection} />
				</Tabs.Content>
				<Tabs.Content value="layers">
					<LayersTable layers={borehole.layers} {selection} />
				</Tabs.Content>
			</div>
		</Tabs>

		<!-- Original document, with the additional files to switch to -->
		<DocumentPane documents={borehole.documents} class="min-h-0" />
	</div>
</div>
