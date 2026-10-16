<script lang="ts">
	import { lithologies } from './lithology';
	import type { BoreholeLayer } from './types';

	interface Props {
		layers: BoreholeLayer[];
		/** Height of the borehole start in m ü. NN. */
		elevation: number;
		totalDepth: number;
		selectedId?: string | null;
		onselect?: (id: string | null) => void;
	}

	let { layers, elevation, totalDepth, selectedId = null, onselect }: Props = $props();

	const scale = 14; // px per metre
	const axisWidth = 44;
	const columnWidth = 70;
	const labelWidth = 130;
	const top = 12;

	let height = $derived(totalDepth * scale);
	let width = axisWidth + columnWidth + labelWidth;
	let ticks = $derived(Array.from({ length: Math.floor(totalDepth / 2) + 1 }, (_, i) => i * 2));
</script>

<svg
	viewBox="0 0 {width} {height + top * 2}"
	class="w-full"
	role="img"
	aria-label="Borehole cross section"
>
	<g transform="translate(0 {top})">
		<!-- depth / height axis -->
		{#each ticks as depth (depth)}
			<line
				x1={axisWidth - 5}
				x2={axisWidth}
				y1={depth * scale}
				y2={depth * scale}
				class="stroke-surface-500"
			/>
			<text
				x={axisWidth - 8}
				y={depth * scale}
				text-anchor="end"
				dominant-baseline="middle"
				class="fill-current text-[8px]"
			>
				{(elevation - depth).toFixed(0)}
			</text>
		{/each}
		<text x="0" y="-3" class="fill-current text-[7px] opacity-60">m ü. NN</text>

		<!-- layers -->
		{#each layers as layer (layer.id)}
			{@const y = layer.startDepth * scale}
			{@const h = (layer.endDepth - layer.startDepth) * scale}
			{@const selected = selectedId === layer.id}
			<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
			<g
				class="cursor-pointer"
				onmouseenter={() => onselect?.(layer.id)}
				onmouseleave={() => onselect?.(null)}
				onclick={() => onselect?.(selected ? null : layer.id)}
			>
				<title>{layer.id}: {lithologies[layer.petrography.lithology].label}</title>
				<rect x={axisWidth} {y} width={columnWidth} height={h} fill={layer.color.hex} />
				<rect
					x={axisWidth}
					{y}
					width={columnWidth}
					height={h}
					fill="url(#{lithologies[layer.petrography.lithology].patternId})"
				/>
				<rect
					x={axisWidth}
					{y}
					width={columnWidth}
					height={h}
					fill="none"
					class={selected ? 'stroke-primary-500' : 'stroke-black/70'}
					stroke-width={selected ? 2 : 0.8}
				/>
				{#if h >= 10}
					<text
						x={axisWidth + columnWidth + 6}
						y={y + h / 2}
						dominant-baseline="middle"
						class="fill-current text-[8px] {selected ? 'font-bold' : ''}"
					>
						{layer.stratigraphy.code} · {lithologies[layer.petrography.lithology].label}
					</text>
				{/if}
			</g>
		{/each}

		<!-- end of borehole marker -->
		<line
			x1={axisWidth}
			x2={axisWidth + columnWidth}
			y1={height}
			y2={height}
			stroke-width="2"
			class="stroke-black"
		/>
		<text
			x={axisWidth + columnWidth / 2}
			y={height + 9}
			text-anchor="middle"
			class="fill-current text-[7px] opacity-60"
		>
			EOH {totalDepth.toFixed(1)} m
		</text>
	</g>
</svg>
