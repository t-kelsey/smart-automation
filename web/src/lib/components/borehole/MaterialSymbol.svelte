<script lang="ts">
	import { dinColors, materials, patternId } from '#lib/din4023/index.ts';
	import type { MaterialKey } from '#lib/din4023/index.ts';

	interface Props {
		material: MaterialKey;
		/** Tint the box with the DIN colour of the material. */
		colored?: boolean;
		class?: string;
	}

	let { material, colored = true, class: className = 'h-6 w-10' }: Props = $props();

	let color = $derived(materials[material].color);
</script>

<svg viewBox="0 0 40 24" class="shrink-0 {className}" aria-hidden="true">
	<rect width="40" height="24" fill="white" />
	{#if colored && color}
		<rect width="40" height="24" fill={dinColors[color].hex} fill-opacity="0.5" />
	{/if}
	<rect width="40" height="24" fill="url(#{patternId(material)})" />
	<rect width="40" height="24" fill="none" stroke="black" stroke-width="1.2" />
</svg>
