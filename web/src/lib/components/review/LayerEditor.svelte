<!--
@component
Layers of a borehole, edited in place, one card per layer: depths, stratigraphy and colour as
text, petrography picked from DIN 4023, with the review marks and open flags of every value.
Layers can be added and deleted; deleted layers are listed below and can be restored. Hovering a
layer highlights it in the profile and shows where it is written in the document.

@param review - Review of the borehole.
@param selection - Shared hover highlighting of the layers.
@param focus - Receives the source of the hovered or focused field.
-->
<script lang="ts">
	import { PlusIcon, TrashIcon, Undo2Icon } from '@lucide/svelte';
	import type { BoreholeLayer, LayerField } from '#lib/domain/borehole.ts';
	import type { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import { formatRelative } from '#lib/domain/pipelines.ts';
	import EditableText from './EditableText.svelte';
	import PetrographyPicker from './PetrographyPicker.svelte';
	import ReviewField from './ReviewField.svelte';
	import { formatValue, type Review } from './review.ts';
	import type { SourceFocus } from './source-focus.svelte.ts';

	interface Props {
		review: Review;
		selection: LayerSelection;
		focus: SourceFocus;
	}

	let { review, selection, focus }: Props = $props();

	let borehole = $derived(review.borehole);

	const columns: { field: Exclude<LayerField, 'petrography'>; label: string; type?: 'number' }[] = [
		{ field: 'depth_from_m', label: 'From (m)', type: 'number' },
		{ field: 'depth_to_m', label: 'To (m)', type: 'number' },
		{ field: 'stratigraphy', label: 'Stratigraphy' },
		{ field: 'color', label: 'Colour' }
	];
	const columnFields = new Set<string>([...columns.map((c) => c.field), 'petrography']);

	/** The whole layer (its creation) if it has flags or edits, and flagged fields without a column. */
	const otherFields = (layer: BoreholeLayer) =>
		[
			...new Set([
				'layer',
				...borehole.flags
					.filter((f) => !f.resolvedAt && f.layerId === layer.id && !columnFields.has(f.field))
					.map((f) => f.field)
			])
		].filter(
			(field) => review.openFlags(field, layer.id).length || review.edits(field, layer.id).length
		);

	/** The latest deletion of each layer that is still gone. */
	let deleted = $derived(
		borehole.edits.filter(
			(e, i, all) =>
				e.field === 'layer' &&
				e.newValue === null &&
				e.layerId &&
				!borehole.layers.some((l) => l.id === e.layerId) &&
				all.findIndex((other) => other.field === 'layer' && other.layerId === e.layerId) === i
		)
	);

	function addLayer() {
		const from = borehole.layers.at(-1)?.endDepth ?? 0;
		void review.run((s) => s.addLayer(borehole.id, { depth_from_m: from, depth_to_m: from + 1 }));
	}
</script>

<div class="space-y-3">
	{#each borehole.layers as layer (layer.id)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="@container rounded-container border p-2 transition-colors {selection.isHovered(
				layer.id
			) || selection.isSelected(layer.id)
				? 'border-primary-500 bg-primary-500/5'
				: 'border-surface-200-800'}"
			onmouseenter={() => selection.hover(layer.id)}
			onmouseleave={() => selection.hover(null)}
		>
			<div class="mb-1 flex items-center gap-2 text-sm">
				<span class="font-semibold">Layer {layer.position}</span>
				<span class="flex-1 text-xs opacity-60">
					{layer.startDepth} – {layer.endDepth} m
				</span>
				<button
					type="button"
					class="btn-icon size-7 hover:preset-tonal-error"
					title="Delete layer {layer.position}"
					aria-label="Delete layer {layer.position}"
					onclick={() => review.run((s) => s.deleteLayer(borehole.id, layer.id))}
				>
					<TrashIcon class="size-4" />
				</button>
			</div>
			<div class="grid grid-cols-2 gap-x-2 gap-y-1 @lg:grid-cols-4">
				{#each columns as column (column.field)}
					<ReviewField
						{review}
						{focus}
						field={column.field}
						layerId={layer.id}
						label={column.label}
						class={column.type ? '' : 'col-span-2 @lg:col-span-1'}
					>
						<EditableText
							value={layer.stored[column.field]}
							type={column.type}
							label="{column.label} of layer {layer.position}"
							onsave={(text) => review.setField(column.field, text, layer.id)}
						/>
					</ReviewField>
				{/each}
				<ReviewField
					{review}
					{focus}
					field="petrography"
					layerId={layer.id}
					label="Petrography (DIN 4023)"
					class="col-span-2 @lg:col-span-4"
				>
					<PetrographyPicker
						{layer}
						onsave={(text) => review.setField('petrography', text, layer.id)}
					/>
				</ReviewField>
				{#each otherFields(layer) as field (field)}
					<ReviewField
						{review}
						{focus}
						{field}
						layerId={layer.id}
						label={field === 'layer' ? 'Whole layer' : field}
						class="col-span-2 @lg:col-span-4"
					/>
				{/each}
			</div>
		</div>
	{:else}
		<p class="py-8 text-center opacity-60">No layers.</p>
	{/each}

	<button type="button" class="btn preset-tonal btn-sm" onclick={addLayer}>
		<PlusIcon class="size-4" />
		Add layer
	</button>

	{#if deleted.length}
		<section class="space-y-2">
			<h3 class="text-xs font-semibold uppercase opacity-60">Deleted layers</h3>
			<ul class="space-y-1 text-sm">
				{#each deleted as edit (edit.id)}
					<li class="flex items-center gap-2">
						<span class="flex-1">
							{formatValue(edit.oldValue)}
							<span class="text-xs opacity-60">· {formatRelative(new Date(edit.createdAt))}</span>
						</span>
						<button
							type="button"
							class="btn preset-tonal btn-sm"
							onclick={() => review.revert(edit.id)}
						>
							<Undo2Icon class="size-4" />
							Restore
						</button>
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</div>
