<!--
@component
Cross section of a borehole (DIN 4023 column) with a colour toggle, scaled to fit the height of its
parent. Owns the colour state, so every
page that shows a cross section gets the same control.

@param borehole - Borehole whose layers are drawn.
@param [selectedId] - Id of the highlighted layer.
@param [onselect] - Called with a layer id on hover and with `null` when the pointer leaves.
@param [class] - Extra classes for the root element. The component fills the height of its parent, so
  the parent needs a height.
-->
<script lang="ts">
	import type { Borehole } from '#lib/domain/borehole.ts';
	import BoreholeColumn from './BoreholeColumn.svelte';

	interface Props {
		borehole: Pick<Borehole, 'layers' | 'totalDepth'>;
		selectedId?: string | null;
		onselect?: (id: string | null) => void;
		class?: string;
	}

	let { borehole, selectedId = null, onselect, class: className = '' }: Props = $props();

	let colored = $state(true);
	let columnHeight = $state(0);
</script>

<div class="flex h-full min-h-0 flex-col {className}">
	<label class="mb-3 flex shrink-0 cursor-pointer items-center justify-end gap-2 text-sm">
		<input type="checkbox" class="checkbox" bind:checked={colored} />
		Colour
	</label>
	<!-- The column is scaled to the height left for it, so it never needs scrolling. -->
	<div class="min-h-0 flex-1" bind:clientHeight={columnHeight}>
		<BoreholeColumn
			layers={borehole.layers}
			totalDepth={borehole.totalDepth ?? 0}
			{colored}
			{selectedId}
			{onselect}
			availableHeight={columnHeight}
		/>
	</div>
</div>
