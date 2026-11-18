<!--
@component
Layers of a borehole, edited in place: depths, stratigraphy and colour as text, petrography picked
from DIN 4023, with the review marks of every value. Layers can be added and deleted; deleted
layers are listed below the table and can be restored. Hovering a row highlights the layer in the
profile and shows where it is written in the document.

@param review - Review of the borehole.
@param selection - Shared hover highlighting of the layers.
-->
<script lang="ts">
	import { PlusIcon, TrashIcon, Undo2Icon } from '@lucide/svelte';
	import type { BoreholeLayer, LayerField } from '#lib/domain/borehole.ts';
	import type { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import { formatRelative } from '#lib/domain/pipelines.ts';
	import EditableText from './EditableText.svelte';
	import FieldMarks from './FieldMarks.svelte';
	import PetrographyPicker from './PetrographyPicker.svelte';
	import { formatValue, type Review } from './review.ts';

	interface Props {
		review: Review;
		selection: LayerSelection;
	}

	let { review, selection }: Props = $props();

	let borehole = $derived(review.borehole);

	const columns: { field: LayerField; label: string; type?: 'number' }[] = [
		{ field: 'depth_from_m', label: 'From (m)', type: 'number' },
		{ field: 'depth_to_m', label: 'To (m)', type: 'number' },
		{ field: 'stratigraphy', label: 'Stratigraphy' },
		{ field: 'petrography', label: 'Petrography' },
		{ field: 'color', label: 'Colour' }
	];
	const columnFields = new Set<string>(columns.map((c) => c.field));

	/** The whole layer (its creation), and flagged fields of the layer that have no column. */
	const otherFields = (layer: BoreholeLayer) => [
		...new Set([
			'layer',
			...borehole.flags
				.filter((f) => !f.resolvedAt && f.layerId === layer.id && !columnFields.has(f.field))
				.map((f) => f.field)
		])
	];

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

<div class="space-y-4">
	<div class="table-wrap">
		<table class="table">
			<thead>
				<tr>
					<th class="w-px">#</th>
					{#each columns as column (column.field)}
						<th class="whitespace-nowrap">{column.label}</th>
					{/each}
					<th class="w-px"><span class="sr-only">Actions</span></th>
				</tr>
			</thead>
			<tbody>
				{#each borehole.layers as layer (layer.id)}
					<tr
						class={selection.isHovered(layer.id) ? 'bg-primary-500/10' : ''}
						onmouseenter={() => selection.hover(layer.id)}
						onmouseleave={() => selection.hover(null)}
					>
						<td class="font-medium">{layer.position}</td>
						{#each columns as column (column.field)}
							<td class="p-1 align-top">
								<div
									class="flex items-start gap-0.5 rounded-base {review.tint(
										column.field,
										layer.id
									)}"
									data-review-target="{layer.id}:{column.field}"
								>
									{#if column.field === 'petrography'}
										<div class="min-w-48 flex-1">
											<PetrographyPicker
												{layer}
												onsave={(text) => review.setField('petrography', text, layer.id)}
											/>
										</div>
									{:else}
										<EditableText
											class="flex-1 {column.type ? 'w-20' : 'min-w-28'}"
											value={layer.stored[column.field]}
											type={column.type}
											label="{column.label} of layer {layer.position}"
											onsave={(text) => review.setField(column.field, text, layer.id)}
										/>
									{/if}
									<FieldMarks {review} field={column.field} layerId={layer.id} />
								</div>
							</td>
						{/each}
						<td class="p-1 align-top">
							<div class="flex items-center gap-0.5" data-review-target="{layer.id}:*">
								{#each otherFields(layer) as field (field)}
									<FieldMarks {review} {field} layerId={layer.id} />
								{/each}
								<button
									type="button"
									class="btn-icon size-8 hover:preset-tonal-error"
									title="Delete layer {layer.position}"
									aria-label="Delete layer {layer.position}"
									onclick={() => review.run((s) => s.deleteLayer(borehole.id, layer.id))}
								>
									<TrashIcon class="size-4" />
								</button>
							</div>
						</td>
					</tr>
				{:else}
					<tr><td colspan="7" class="py-8 text-center opacity-60">No layers.</td></tr>
				{/each}
			</tbody>
		</table>
	</div>

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
