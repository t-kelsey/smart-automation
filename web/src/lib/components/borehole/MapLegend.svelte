<script lang="ts">
	import { patternIconSvg } from './dot-icons.ts';
	import { dinColors, materials } from '#lib/din4023/index.ts';
	import type { MaterialKey } from '#lib/din4023/index.ts';

	interface Props {
		/** Matches the dots: rock types with a white rim, or the plain verified/unverified colour. */
		showFill?: boolean;
	}

	let { showFill = false }: Props = $props();

	// Example boreholes, one per rock type: the fill is the material's DIN hatch on its DIN colour.
	const rockTypes: MaterialKey[] = [
		'sand',
		'gravel',
		'silt',
		'clay',
		'peat',
		'sandstone',
		'conglomerate',
		'anhydrite',
		'gypsum',
		'rockSalt'
	];
	const rockEntries = rockTypes.map((key) => {
		const color = materials[key].color;
		return {
			key,
			label: materials[key].name.en,
			color: color ? dinColors[color].hex : '#ffffff'
		};
	});

	const iconUrl = (svg: string) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
</script>

<!-- Passes pointer events through, so the map underneath stays fully usable. -->
{#if showFill}
	<ul
		class="pointer-events-none space-y-1 rounded-md bg-surface-50-950/70 px-2.5 py-1.5 text-[0.8625rem] shadow-sm backdrop-blur-sm"
		aria-label="Map legend"
	>
		{#each rockEntries as { key, label, color } (key)}
			<li class="flex items-center gap-2">
				<img
					src={iconUrl(patternIconSvg({ material: key, color }, '#ffffff'))}
					alt=""
					class="size-[1.725rem] shrink-0"
				/>
				<span class="opacity-80">{label}</span>
			</li>
		{/each}
	</ul>
{/if}
