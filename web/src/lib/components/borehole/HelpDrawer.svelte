<script lang="ts">
	import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';
	import { CircleHelpIcon, XIcon } from '@lucide/svelte';
	import type { BoreholeLayer } from '#lib/domain/borehole.ts';
	import {
		dinColors,
		materialGroups,
		materialList,
		materials,
		materialsByGroup,
		standard,
		usedMaterials
	} from '#lib/din4023/index.ts';
	import type { Material } from '#lib/din4023/index.ts';
	import MaterialSymbol from './MaterialSymbol.svelte';

	interface Props {
		/** Layers of the current borehole; the legend lists the materials they use first. */
		layers?: BoreholeLayer[];
	}

	let { layers = [] }: Props = $props();

	let used = $derived.by(() => {
		const keys = new Set(
			layers.flatMap((layer) =>
				layer.petrography.composition ? usedMaterials(layer.petrography.composition) : []
			)
		);
		return materialList.filter((material) => keys.has(material.key));
	});
</script>

{#snippet materialRow(material: Material)}
	<li class="flex items-center gap-3 text-sm">
		<MaterialSymbol material={material.key} />
		<span class="w-10 shrink-0 font-semibold">{material.short}</span>
		<span class="min-w-0 flex-1">
			{material.name.en}
			<span class="block text-xs opacity-60">
				{material.name.de}{material.color ? ` · ${dinColors[material.color].name.en}` : ''}
			</span>
		</span>
	</li>
{/snippet}

<Dialog>
	<Dialog.Trigger class="btn preset-tonal">
		<CircleHelpIcon class="size-4" />
		Help
	</Dialog.Trigger>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-40 bg-surface-950/50" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex justify-end">
			<Dialog.Content
				class="flex h-full w-full max-w-md flex-col gap-6 overflow-y-auto bg-surface-50-950 p-6 shadow-xl"
			>
				<header class="flex items-start justify-between gap-4">
					<div>
						<Dialog.Title class="h4">Help</Dialog.Title>
						<Dialog.Description class="text-sm opacity-70">
							How to read the borehole cross section, drawn after DIN 4023:2023-02.
						</Dialog.Description>
					</div>
					<Dialog.CloseTrigger class="btn-icon preset-tonal" aria-label="Close help">
						<XIcon class="size-4" />
					</Dialog.CloseTrigger>
				</header>

				<section class="space-y-2">
					<h5 class="h6">Reading the column</h5>
					<ul class="list-disc space-y-1 pl-5 text-sm">
						<li>Depths on the left are metres below the start of the borehole.</li>
						<li>Right of the column: short form of the layer.</li>
						<li>
							The main component fills the whole width. The first minor component is drawn in the
							right half only (<em>G, s</em>: gravel, sandy).
						</li>
						<li>
							Two components with about equal shares are written with a slash (<em>G/S</em>) and
							drawn over the whole width; colours are split into left and right half.
						</li>
						<li>
							<em>u'</em> is a weak, <em>u*</em> a strong minor component. In brackets: the soil a
							rock decomposed to, or the soil of made ground (<em>Pl (S, g)</em>,
							<em>A (S, g)</em>).
						</li>
						<li>
							The tint behind the pattern is the DIN colour (Annex A) and can be switched off.
						</li>
						<li>Hover or click a layer to highlight it in the layer table.</li>
					</ul>
				</section>

				{#if used.length}
					<section class="space-y-2">
						<h5 class="h6">Used in this borehole</h5>
						<ul class="space-y-2">
							{#each used as material (material.key)}
								{@render materialRow(material)}
							{/each}
						</ul>
					</section>
				{/if}

				<section class="space-y-2">
					<h5 class="h6">All DIN 4023 symbols</h5>
					{#each materialGroups as { group, title, table } (group)}
						<details class="rounded-lg border border-surface-200-800 p-3">
							<summary class="cursor-pointer text-sm font-medium">
								{title.en} <span class="opacity-60">· Table {table}</span>
							</summary>
							<ul class="mt-3 space-y-2">
								{#each materialsByGroup(group) as material (material.key)}
									{@render materialRow(material)}
								{/each}
							</ul>
						</details>
					{/each}
					<p class="text-xs opacity-60">
						Soil short forms in lower case (e.g. <em>{materials.sand.secondaryShort}</em>) name a
						minor component.
					</p>
					<p class="text-xs opacity-60">
						Source: <code>standards/din-4023/din-4023.json</code> (soil table
						{standard.norm.ausgabe_tabelle_1}, hatches {standard.norm.ausgabe_schraffuren}).
					</p>
				</section>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog>
