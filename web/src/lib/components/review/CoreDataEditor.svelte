<!--
@component
Core data of a borehole, edited in place, with the review marks of every field. Hovering a field
shows where it is written in the document. Flags on fields without a row of their own (e.g. "no
layers") are listed at the end.

@param review - Review of the borehole.
@param selection - Receives the source of the hovered field.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { BOREHOLE_FIELDS } from '#lib/domain/borehole.ts';
	import type { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import MapSnippet from '#lib/components/borehole/MapSnippet.svelte';
	import EditableText from './EditableText.svelte';
	import FieldMarks from './FieldMarks.svelte';
	import LocationEditor from './LocationEditor.svelte';
	import type { Review } from './review.ts';

	interface Props {
		review: Review;
		selection: LayerSelection;
	}

	let { review, selection }: Props = $props();

	let borehole = $derived(review.borehole);
	const shown = new Set<string>([...BOREHOLE_FIELDS.map((f) => f.field), 'location']);
	let otherFields = $derived([
		...new Set(
			borehole.flags
				.filter((f) => !f.resolvedAt && !f.layerId && !shown.has(f.field))
				.map((f) => f.field)
		)
	]);
</script>

{#snippet row(field: string, label: string, editor: Snippet)}
	<dt class="py-1.5 text-sm opacity-60">{label}</dt>
	<dd
		class="flex items-start gap-1 rounded-base {review.tint(field)}"
		data-review-target="borehole:{field}"
		onmouseenter={() => selection.showSource(review.source(field))}
		onmouseleave={() => selection.showSource(null)}
	>
		{@render editor()}
		<FieldMarks {review} {field} />
	</dd>
{/snippet}

<div class="@container">
	<div class="grid gap-4 @2xl:grid-cols-[1fr_20rem]">
		<dl class="grid grid-cols-[auto_1fr] content-start gap-x-4 gap-y-1">
			{#each BOREHOLE_FIELDS as f (f.field)}
				{#snippet editor()}
					<EditableText
						class="flex-1"
						value={borehole.stored[f.field]}
						type={f.type}
						label={f.label}
						onsave={(text) => review.setField(f.field, text)}
					/>
				{/snippet}
				{@render row(f.field, f.label, editor)}
			{/each}

			{#snippet location()}
				<LocationEditor {review} />
			{/snippet}
			{@render row('location', 'Coordinates', location)}

			{#each otherFields as field (field)}
				{#snippet messages()}
					<p class="flex-1 px-2 py-1.5 text-sm">
						{review
							.openFlags(field)
							.map((f) => f.message)
							.join(' · ')}
					</p>
				{/snippet}
				{@render row(field, field === 'layer' ? 'Layers' : field, messages)}
			{/each}
		</dl>
		{#if borehole.location}
			<MapSnippet lat={borehole.location.lat} lon={borehole.location.lon} />
		{/if}
	</div>
</div>
