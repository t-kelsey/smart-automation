<script lang="ts">
	import { patternIconSvg } from './dot-icons.ts';
	import { materialHex, materials } from '#lib/din4023/index.ts';
	import { UNKNOWN_COLOR } from '#lib/borehole-columns/column-model.ts';
	import { patternTile } from './column-patterns.ts';
	import type { MaterialKey } from '#lib/din4023/index.ts';

	interface Props {
		/** Matches the dots: rock types with a white rim, or the plain verified/unverified colour. */
		showFill?: boolean;
		/** Matches the detail view's columns: the plain DIN colour per material. */
		showColumns?: boolean;
	}

	let { showFill = false, showColumns = false }: Props = $props();

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
	const rockEntries = rockTypes.map((key) => ({
		key,
		label: materials[key].name.en,
		color: materialHex(key) ?? '#ffffff'
	}));

	const iconUrl = (svg: string) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
</script>

<!-- Passes pointer events through, so the map underneath stays fully usable. -->
{#if showColumns}
	<ul
		class="pointer-events-none space-y-1 rounded-md bg-surface-50-950/70 px-2.5 py-1.5 text-[0.8625rem] shadow-sm backdrop-blur-sm"
		aria-label="Map legend"
	>
		{#each [...rockEntries, { key: undefined, label: 'Unknown', color: UNKNOWN_COLOR }] as { key, label, color } (label)}
			<li class="flex items-center gap-2">
				<!-- The same tile as on the column walls; only shown in the browser, where canvas exists. -->
				<img
					src={patternTile(key, color).toDataURL()}
					alt=""
					class="size-[1.725rem] shrink-0 rounded-sm border border-surface-950/30 object-cover object-left-top"
				/>
				<span class="opacity-80">{label}</span>
			</li>
		{/each}
	</ul>
{:else if showFill}
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
