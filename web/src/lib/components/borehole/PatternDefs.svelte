<!--
	SVG hatch patterns of DIN 4023, shared by the cross section, swatches and legend.
	Render once per page; patterns are referenced by id (see `patternId`) from any SVG in the document.
-->
<script lang="ts">
	import { materialList, patternId, patterns } from '#lib/din4023/index.ts';
	import type { PatternDef, Shape } from '#lib/din4023/index.ts';
</script>

{#snippet shapes(list: Shape[])}
	{#each list as shape, i (i)}
		{#if shape.type === 'circle'}
			<circle
				cx={shape.cx}
				cy={shape.cy}
				r={shape.r}
				fill={shape.filled ? 'currentColor' : 'none'}
			/>
		{:else if shape.type === 'rect'}
			<rect
				x={shape.x}
				y={shape.y}
				width={shape.width}
				height={shape.height}
				fill={shape.filled ? 'currentColor' : 'none'}
			/>
		{:else if shape.type === 'path'}
			<path
				d={shape.d}
				fill={shape.filled ? 'currentColor' : 'none'}
				stroke-width={shape.strokeWidth}
			/>
		{:else}
			<text x={shape.x} y={shape.y} font-size={shape.size} fill="currentColor" stroke="none">
				{shape.text}
			</text>
		{/if}
	{/each}
{/snippet}

{#snippet tile(id: string, def: PatternDef, shift: boolean)}
	<pattern
		{id}
		width={def.width}
		height={def.height}
		patternUnits="userSpaceOnUse"
		patternTransform={shift ? `translate(${def.width / 2} ${def.height / 2})` : undefined}
	>
		{@render shapes(def.shapes)}
	</pattern>
{/snippet}

<!-- Symbols are always black on white, independent of the page theme. -->
<svg width="0" height="0" class="absolute text-black" aria-hidden="true" focusable="false">
	<defs>
		<g stroke="currentColor" stroke-width="0.7" fill="none" stroke-linecap="butt">
			{#each materialList as material (material.key)}
				{@render tile(patternId(material.key, 'a'), patterns[material.key], false)}
				{@render tile(patternId(material.key, 'b'), patterns[material.key], true)}
			{/each}
		</g>
	</defs>
</svg>
