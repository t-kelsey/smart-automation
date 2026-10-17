<!--
@component
Layers of a borehole: a table on wide containers, one card per layer on narrow ones. Hovering a
layer, or clicking it, is reported to `selection`, so it is highlighted in the cross section too.

@param layers - Layers to list, in display order.
@param [selection] - Shared hover and click highlighting of the layers.
-->
<script lang="ts">
	import type { BoreholeLayer } from '#lib/domain/borehole.ts';
	import type { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import { describe, shortForm } from '#lib/din4023/index.ts';

	interface Props {
		layers: BoreholeLayer[];
		selection?: LayerSelection;
	}

	let { layers, selection }: Props = $props();

	function onkey(event: KeyboardEvent, id: string) {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		selection?.toggle(id);
	}

	/** Selected layers are tinted stronger and outlined; hovering tints lightly. Both can apply. */
	const highlight = (id: string) =>
		[
			selection?.isSelected(id)
				? 'bg-primary-500/25 outline-2 -outline-offset-2 outline-primary-500'
				: '',
			selection?.isHovered(id) && !selection.isSelected(id) ? 'bg-primary-500/15' : ''
		].join(' ');
</script>

{#snippet petrography(layer: BoreholeLayer)}
	{@const composition = layer.petrography.composition}
	{#if composition}
		<span class="font-medium">{shortForm(composition)}</span>
		{describe(composition)}
	{:else}
		<span class="opacity-60">Unclassified</span>
	{/if}
	<span class="block text-xs opacity-60">{layer.petrography.description}</span>
{/snippet}

{#snippet colorSwatch(layer: BoreholeLayer)}
	<span
		class="size-4 shrink-0 rounded-sm border border-black/40"
		style:background-color={layer.color.hex}
	></span>
{/snippet}

<div class="@container">
	<!-- Narrow container: one card per layer instead of a horizontally scrolling table. -->
	<ul class="space-y-3 @2xl:hidden">
		{#each layers as layer (layer.id)}
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_no_noninteractive_tabindex -->
			<li
				class="cursor-pointer rounded-lg border border-surface-200-800 p-3 text-sm {highlight(
					layer.id
				)}"
				onmouseenter={() => selection?.hover(layer.id)}
				onmouseleave={() => selection?.hover(null)}
				onclick={() => selection?.toggle(layer.id)}
				onkeydown={(event) => onkey(event, layer.id)}
				tabindex="0"
			>
				<div class="mb-2 flex items-center justify-between gap-2">
					<span class="font-medium">{layer.position}</span>
					<span class="text-xs opacity-60">
						{layer.startDepth.toFixed(1)} m – {layer.endDepth.toFixed(1)} m
					</span>
				</div>
				<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
					<dt class="opacity-60">Stratigraphie</dt>
					<dd>
						<span class="font-medium">{layer.stratigraphy.code}</span>
						<span class="text-xs opacity-60">{layer.stratigraphy.name}</span>
					</dd>
					<dt class="opacity-60">Petrographie</dt>
					<dd>{@render petrography(layer)}</dd>
					<dt class="opacity-60">Color</dt>
					<dd class="flex items-center gap-2">
						{@render colorSwatch(layer)}
						{layer.color.name}
					</dd>
				</dl>
			</li>
		{/each}
	</ul>

	<div class="hidden table-wrap @2xl:block">
		<table class="table">
			<thead>
				<tr>
					<th class="w-px">Id</th>
					<th class="w-px whitespace-nowrap">From (m)</th>
					<th class="w-px whitespace-nowrap">To (m)</th>
					<th>Stratigraphie</th>
					<th>Petrographie</th>
					<th>Color</th>
				</tr>
			</thead>
			<tbody>
				{#each layers as layer (layer.id)}
					<tr
						class="cursor-pointer {highlight(layer.id)}"
						onmouseenter={() => selection?.hover(layer.id)}
						onmouseleave={() => selection?.hover(null)}
						onclick={() => selection?.toggle(layer.id)}
						onkeydown={(event) => onkey(event, layer.id)}
						tabindex="0"
					>
						<td class="font-medium">{layer.position}</td>
						<td class="whitespace-nowrap">{layer.startDepth.toFixed(1)}</td>
						<td class="whitespace-nowrap">{layer.endDepth.toFixed(1)}</td>
						<td>
							<span class="font-medium">{layer.stratigraphy.code}</span>
							<span class="block text-xs opacity-60">{layer.stratigraphy.name}</span>
						</td>
						<td>{@render petrography(layer)}</td>
						<td>
							<span class="flex items-center gap-2 whitespace-nowrap">
								{@render colorSwatch(layer)}
								{layer.color.name}
							</span>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
