<!--
	Borehole column after DIN 4023:2023-02: two vertical lines with cross lines at the layer boundaries,
	hatch pattern (and optional DIN colour) per layer, depths on the left, short form on the right.
-->
<script lang="ts">
	import type { BoreholeLayer } from '#lib/domain/borehole.ts';
	import {
		columnFill,
		describe,
		dinColors,
		materials,
		patternId,
		shortForm
	} from '#lib/din4023/index.ts';
	import type { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import type { MaterialKey } from '#lib/din4023/index.ts';

	interface Props {
		layers: BoreholeLayer[];
		totalDepth: number;
		/** Tint the layers with the DIN colours; otherwise only the hatch patterns are drawn. */
		colored?: boolean;
		selection?: LayerSelection;
		/**
		 * Height in pixels the drawing may use; the scale is chosen so that the whole column fits.
		 * Without it the column is drawn at a fixed scale.
		 */
		availableHeight?: number;
		/** Worst open review flag of a layer, drawn as a yellow (warning) or red (error) dot. */
		flagOf?: (layerId: string) => 'warning' | 'error' | null;
	}

	let { layers, totalDepth, colored = true, selection, availableHeight, flagOf }: Props = $props();

	const defaultScale = 14; // units (pixels) per metre
	const minScale = 1;
	const top = 8;
	const bottomMargin = 14;
	const colX = 60;
	const colW = 90;
	const half = colW / 2;
	const width = colX + colW + 90;

	/** Drawn depth: layers below the stated total depth are drawn too, not cut off. */
	let depth = $derived(Math.max(totalDepth, ...layers.map((l) => l.endDepth)));
	/** Units per metre; one unit is one pixel, so text keeps its size whatever the depth. */
	let scale = $derived(
		availableHeight && depth > 0
			? Math.max(minScale, (availableHeight - top - bottomMargin) / depth)
			: defaultScale
	);
	const y = (metres: number) => top + metres * scale;
	let bottom = $derived(y(depth));
	let height = $derived(bottom + bottomMargin);

	/** Pushes sorted positions apart so that labels do not overlap. */
	function spread(positions: number[], gap: number, limit: number): number[] {
		const out = [...positions];
		for (let i = 1; i < out.length; i++) out[i] = Math.max(out[i], out[i - 1] + gap);
		const last = out.length - 1;
		if (last >= 0 && out[last] > limit) {
			out[last] = limit;
			for (let i = last - 1; i >= 0; i--) out[i] = Math.min(out[i], out[i + 1] - gap);
		}
		return out;
	}

	const hex = (key: MaterialKey | undefined) => {
		const color = key && materials[key].color;
		return color ? dinColors[color].hex : undefined;
	};

	let rows = $derived.by(() => {
		const sorted = [...layers].sort((a, b) => a.startDepth - b.startDepth);
		const labelYs = spread(
			sorted.map((l) => y((l.startDepth + l.endDepth) / 2)),
			14,
			bottom
		);
		const depthYs = spread(
			sorted.map((l) => y(l.endDepth) - 2),
			13,
			bottom + 10
		);
		return sorted.map((layer, i) => {
			const composition = layer.petrography.composition;
			const fill = composition && columnFill(composition);
			return {
				layer,
				y0: y(layer.startDepth),
				y1: y(layer.endDepth),
				labelY: labelYs[i],
				depthY: depthYs[i],
				fill,
				leftColor: fill && hex(fill.main),
				rightColor: fill && (hex(fill.second) ?? hex(fill.main)),
				label: composition ? shortForm(composition) : '?',
				title: composition ? describe(composition) : layer.petrography.description
			};
		});
	});
</script>

<!-- Drawn at pixel size; `max-w-full` shrinks it (keeping the aspect ratio) on narrow containers. -->
<svg
	viewBox="0 0 {width} {height}"
	{width}
	{height}
	class="mx-auto block max-w-full"
	role="img"
	aria-label="Borehole cross section after DIN 4023"
	font-family="inherit"
>
	{#each rows as row (row.layer.id)}
		{@const h = row.y1 - row.y0}
		{@const selected = selection?.isSelected(row.layer.id) ?? false}
		{@const hovered = selection?.isHovered(row.layer.id) ?? false}
		<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
		<g
			class="cursor-pointer"
			onmouseenter={() => selection?.hover(row.layer.id)}
			onmouseleave={() => selection?.hover(null)}
			onclick={() => selection?.toggle(row.layer.id)}
		>
			<title>{row.title}</title>
			<rect x={colX} y={row.y0} width={colW} height={h} fill={row.fill ? 'white' : '#e5e7eb'} />
			{#if row.fill}
				{#if colored}
					{#if row.leftColor}
						<rect
							x={colX}
							y={row.y0}
							width={half}
							height={h}
							fill={row.leftColor}
							fill-opacity="0.5"
						/>
					{/if}
					{#if row.rightColor}
						<rect
							x={colX + half}
							y={row.y0}
							width={half}
							height={h}
							fill={row.rightColor}
							fill-opacity="0.5"
						/>
					{/if}
				{/if}
				<rect
					x={colX}
					y={row.y0}
					width={colW}
					height={h}
					fill="url(#{patternId(row.fill.main, 'a')})"
				/>
				{#if row.fill.second}
					<!-- 4.2.5: the first minor component only fills the right half; equal components fill both -->
					<rect
						x={row.fill.mode === 'both' ? colX : colX + half}
						y={row.y0}
						width={row.fill.mode === 'both' ? colW : half}
						height={h}
						fill="url(#{patternId(row.fill.second, 'b')})"
					/>
				{/if}
			{/if}
			{#if flagOf?.(row.layer.id)}
				<circle
					cx={8}
					cy={(row.y0 + row.y1) / 2}
					r={5}
					class={flagOf(row.layer.id) === 'error' ? 'fill-error-500' : 'fill-warning-500'}
				/>
			{/if}
			{#if hovered || selected}
				<rect
					x={colX}
					y={row.y0}
					width={colW}
					height={h}
					class="stroke-primary-500 {selected ? 'fill-primary-500/30' : 'fill-primary-500/15'}"
					stroke-width={selected ? 2.5 : 1.5}
					stroke-dasharray={selected || !hovered ? undefined : '4 2'}
				/>
			{/if}
		</g>
		<text
			x={colX + colW + 8}
			y={row.labelY}
			dominant-baseline="middle"
			font-size="12"
			fill="currentColor"
			font-weight={selected || hovered ? 700 : 600}
		>
			{row.label}
		</text>
	{/each}

	<g stroke="currentColor" fill="none" stroke-width="0.9">
		<line x1={colX} x2={colX} y1={top} y2={bottom} />
		<line x1={colX + colW} x2={colX + colW} y1={top} y2={bottom} />
		{#each rows as row (row.layer.id)}
			<line x1={colX - 36} x2={colX + colW} y1={row.y1} y2={row.y1} />
		{/each}
		<line x1={colX - 36} x2={colX + colW + 6} y1={top} y2={top} stroke-width="1.6" />
		<line x1={colX - 36} x2={colX + colW + 6} y1={bottom} y2={bottom} stroke-width="1.6" />
	</g>

	<!-- depths below the borehole start -->
	<g fill="currentColor" font-size="11" text-anchor="end">
		{#each rows as row (row.layer.id)}
			<text x={colX - 4} y={row.depthY}>{row.layer.endDepth.toFixed(1)}</text>
		{/each}
	</g>
</svg>
