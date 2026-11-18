<!--
	One layer of a DIN 4023 column as a rectangle: white background (grey if unclassified), the DIN
	colour of the main and first minor component as a tint on the left and right half, the main
	hatch over the whole width and the minor component's hatch on the right half (4.2.5).
	Shared by the profile column and the section view; needs `PatternDefs` on the page.
-->
<script lang="ts">
	import { columnFill, materialHex, patternId } from '#lib/din4023/index.ts';
	import type { Composition, MaterialKey } from '#lib/din4023/index.ts';

	interface Props {
		x: number;
		y: number;
		width: number;
		height: number;
		composition?: Composition;
		/** Tint with the DIN colours; otherwise only the hatch patterns are drawn. */
		colored?: boolean;
	}

	let { x, y, width, height, composition, colored = true }: Props = $props();

	const hex = (key: MaterialKey | undefined) => (key ? materialHex(key) : undefined);
	let fill = $derived(composition && columnFill(composition));
	let leftColor = $derived(fill && hex(fill.main));
	let rightColor = $derived(fill && (hex(fill.second) ?? hex(fill.main)));
	let half = $derived(width / 2);
</script>

<rect {x} {y} {width} {height} fill={fill ? 'white' : '#e5e7eb'} />
{#if fill}
	{#if colored}
		{#if leftColor}
			<rect {x} {y} width={half} {height} fill={leftColor} fill-opacity="0.5" />
		{/if}
		{#if rightColor}
			<rect x={x + half} {y} width={half} {height} fill={rightColor} fill-opacity="0.5" />
		{/if}
	{/if}
	<rect {x} {y} {width} {height} fill="url(#{patternId(fill.main, 'a')})" />
	{#if fill.second}
		<!-- 4.2.5: the first minor component only fills the right half; equal components fill both -->
		<rect
			x={fill.mode === 'both' ? x : x + half}
			{y}
			width={fill.mode === 'both' ? width : half}
			{height}
			fill="url(#{patternId(fill.second, 'b')})"
		/>
	{/if}
{/if}
