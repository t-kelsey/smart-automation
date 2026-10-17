<!--
@component
Core data (Stammdaten) of a borehole as a list, with a map snippet of its location. Side by side on
wide containers, stacked on narrow ones.

@param borehole - Borehole to show.
@param [class] - Extra classes for the root element.
-->
<script lang="ts">
	import type { Borehole } from '#lib/domain/borehole.ts';
	import MapSnippet from './MapSnippet.svelte';

	interface Props {
		borehole: Borehole;
		class?: string;
	}

	let { borehole, class: className = '' }: Props = $props();

	let items = $derived([
		{ label: 'Name', value: borehole.name },
		{ label: 'Date', value: borehole.date ?? '–' },
		{ label: 'Boring cause', value: borehole.cause ?? '–' },
		{
			label: 'Height o. NN',
			value: borehole.elevation === null ? '–' : `${borehole.elevation.toFixed(2)} m`
		},
		{
			label: 'Total depth',
			value: borehole.totalDepth === null ? '–' : `${borehole.totalDepth.toFixed(1)} m`
		},
		{ label: 'Drilling method', value: borehole.drillingMethod ?? '–' },
		{ label: 'Client', value: borehole.client ?? '–' },
		{ label: 'Location', value: borehole.location?.place ?? '–' }
	]);
</script>

<div class="@container {className}">
	<div class="grid gap-4 @2xl:grid-cols-[1fr_20rem]">
		<dl class="grid grid-cols-[auto_1fr] content-start gap-x-6 gap-y-2 text-sm">
			{#each items as item (item.label)}
				<dt class="opacity-60">{item.label}</dt>
				<dd class="font-medium">{item.value}</dd>
			{/each}
		</dl>
		{#if borehole.location}
			<MapSnippet lat={borehole.location.lat} lon={borehole.location.lon} />
		{/if}
	</div>
</div>
