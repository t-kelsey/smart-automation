<!--
@component
Petrography of a layer, picked from the DIN 4023 terms: one main component and any number of
minor components ("Sand, schluffig, kiesig"), stored with the German names of the standard.

@param layer - The layer.
@param onsave - Saves the new term; resolves to an error message, or `null` when saved.
-->
<script lang="ts">
	import { Popover, Portal } from '@skeletonlabs/skeleton-svelte';
	import {
		describe,
		materialGroups,
		materialList,
		materials,
		materialsByGroup,
		shortForm
	} from '#lib/din4023/index.ts';
	import type { MaterialKey } from '#lib/din4023/index.ts';
	import type { BoreholeLayer } from '#lib/domain/borehole.ts';

	interface Props {
		layer: BoreholeLayer;
		onsave: (text: string) => Promise<string | null>;
	}

	let { layer, onsave }: Props = $props();

	const minors = materialList.filter((m) => m.secondaryName?.de);
	// Longest first, so that "Grobsand" is not taken for "Sand".
	const mains = [...materialList].sort((a, b) => b.name.de.length - a.name.de.length);

	let open = $state(false);
	let main = $state<MaterialKey | ''>('');
	let secondary = $state<MaterialKey[]>([]);
	let error = $state<string | null>(null);

	/** Reads the stored term back into main and minor components. */
	function load() {
		const text = (layer.stored.petrography ?? '').toLowerCase();
		const found = mains.find((m) => text.startsWith(m.name.de.toLowerCase()));
		const rest = text
			.slice(found?.name.de.length ?? 0)
			.split(/\s*,\s*/)
			.filter(Boolean);
		main = found?.key ?? '';
		secondary = minors
			.filter((m) => m.secondaryName!.de.split(', ').every((word) => rest.includes(word)))
			.map((m) => m.key);
		error = null;
	}

	let term = $derived(
		main
			? [
					materials[main].name.de,
					...secondary.filter((key) => key !== main).map((key) => materials[key].secondaryName!.de)
				].join(', ')
			: ''
	);

	async function save() {
		error = term === (layer.stored.petrography ?? '') ? null : await onsave(term);
		if (!error) open = false;
	}

	const toggle = (key: MaterialKey) =>
		(secondary = secondary.includes(key)
			? secondary.filter((k) => k !== key)
			: [...secondary, key]);
</script>

<Popover
	{open}
	onOpenChange={(details) => {
		open = details.open;
		if (open) load();
	}}
	positioning={{ placement: 'bottom-start' }}
>
	<Popover.Trigger
		class="block w-full rounded-base px-2 py-1 text-left text-sm hover:preset-tonal"
		title="Pick from DIN 4023"
		data-review-input
	>
		{#if layer.petrography.composition}
			<span class="font-medium">{shortForm(layer.petrography.composition)}</span>
			{describe(layer.petrography.composition)}
		{:else}
			<span class="opacity-60">Unclassified</span>
		{/if}
		<span class="block text-xs opacity-60">
			{layer.stored.petrography ??
				(layer.petrography.original ? `Original: ${layer.petrography.original}` : '')}
		</span>
	</Popover.Trigger>
	<Portal>
		<Popover.Positioner class="z-50">
			<Popover.Content
				class="w-96 space-y-3 card border border-surface-200-800 bg-surface-50-950 p-3 text-sm shadow-xl"
			>
				<label class="block space-y-1">
					<span class="text-xs font-semibold uppercase opacity-60">Main component</span>
					<select class="select" bind:value={main}>
						<option value="">– none –</option>
						{#each materialGroups as group (group.group)}
							<optgroup label={group.title.en}>
								{#each materialsByGroup(group.group) as material (material.key)}
									<option value={material.key}>
										{material.name.de} ({material.short}) · {material.name.en}
									</option>
								{/each}
							</optgroup>
						{/each}
					</select>
				</label>

				{#if main}
					<fieldset class="space-y-1">
						<legend class="text-xs font-semibold uppercase opacity-60">Minor components</legend>
						<div class="flex flex-wrap gap-1">
							{#each minors.filter((m) => m.key !== main) as material (material.key)}
								<button
									type="button"
									class="chip {secondary.includes(material.key)
										? 'preset-filled-primary-500'
										: 'preset-tonal'}"
									aria-pressed={secondary.includes(material.key)}
									title={material.secondaryName!.en}
									onclick={() => toggle(material.key)}
								>
									{material.secondaryName!.de}
								</button>
							{/each}
						</div>
					</fieldset>
				{/if}

				<p class="text-xs opacity-60">Saved as: <strong>{term || '–'}</strong></p>
				{#if error}
					<p class="text-xs text-error-600-400" role="alert">{error}</p>
				{/if}
				<div class="flex justify-end gap-2">
					<button type="button" class="btn preset-tonal btn-sm" onclick={() => (open = false)}>
						Cancel
					</button>
					<button type="button" class="btn preset-filled-primary-500 btn-sm" onclick={save}>
						Save
					</button>
				</div>
			</Popover.Content>
		</Popover.Positioner>
	</Portal>
</Popover>
