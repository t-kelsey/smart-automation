<!--
@component
Core data of a borehole, edited in place in small groups (identification, project, depths and
height, location), with the review marks and open flags of every field. The location group has a
mini map. Flags on fields without a row of their own (e.g. "no layers") are listed at the end.

@param review - Review of the borehole.
@param focus - Receives the source of the hovered or focused field.
-->
<script lang="ts">
	import { Popover, Portal } from '@skeletonlabs/skeleton-svelte';
	import { MapIcon } from '@lucide/svelte';
	import { BOREHOLE_FIELDS, type BoreholeField } from '#lib/domain/borehole.ts';
	import MapSnippet from '#lib/components/borehole/MapSnippet.svelte';
	import EditableText from './EditableText.svelte';
	import LocationEditor from './LocationEditor.svelte';
	import ReviewField from './ReviewField.svelte';
	import type { Review } from './review.ts';
	import type { SourceFocus } from './source-focus.svelte.ts';

	interface Props {
		review: Review;
		focus: SourceFocus;
	}

	let { review, focus }: Props = $props();

	let borehole = $derived(review.borehole);

	const groups: { title: string; fields: BoreholeField[] }[] = [
		{ title: 'Identification', fields: ['name', 'external_id', 'drilled_at', 'end_date'] },
		{ title: 'Project', fields: ['client', 'purpose', 'drilling_method'] },
		{ title: 'Depths & height', fields: ['elevation_m', 'total_depth_m', 'groundwater_level_m'] },
		{ title: 'Location', fields: ['place'] }
	];
	/** Long text: full width, growing with the content. */
	const wide = new Set<string>(['client', 'purpose', 'drilling_method', 'place']);
	const definition = Object.fromEntries(BOREHOLE_FIELDS.map((f) => [f.field, f]));

	const shown = new Set<string>([...BOREHOLE_FIELDS.map((f) => f.field), 'location']);
	let otherFields = $derived([
		...new Set(
			borehole.flags
				.filter((f) => !f.resolvedAt && !f.layerId && !shown.has(f.field))
				.map((f) => f.field)
		)
	]);

	let mapOpen = $state(false);
</script>

<div class="space-y-5">
	{#each groups as group (group.title)}
		<section>
			<h3
				class="mb-1 flex h-7 items-center gap-2 text-xs font-semibold tracking-wide uppercase opacity-70"
			>
				{group.title}
				{#if group.title === 'Location' && borehole.location}
					{@const { lat, lon } = borehole.location}
					<Popover
						open={mapOpen}
						onOpenChange={(details) => (mapOpen = details.open)}
						positioning={{ placement: 'bottom-start' }}
					>
						<Popover.Trigger
							class="btn-icon size-7 normal-case hover:preset-tonal"
							title="Show on a map"
							aria-label="Show on a map"
						>
							<MapIcon class="size-4" />
						</Popover.Trigger>
						<Portal>
							<Popover.Positioner class="z-50">
								<Popover.Content
									class="w-96 card border border-surface-200-800 bg-surface-50-950 p-2 shadow-xl"
								>
									{#if mapOpen}
										<MapSnippet {lat} {lon} />
									{/if}
								</Popover.Content>
							</Popover.Positioner>
						</Portal>
					</Popover>
				{/if}
			</h3>
			<div class="grid grid-cols-2 gap-x-3 gap-y-2">
				{#each group.fields as field (field)}
					{@const f = definition[field]}
					<ReviewField
						{review}
						{focus}
						{field}
						label={f.label}
						class={wide.has(field) ? 'col-span-2' : ''}
					>
						<EditableText
							value={borehole.stored[field]}
							type={f.type}
							multiline={wide.has(field)}
							label={f.label}
							onsave={(text) => review.setField(field, text)}
						/>
					</ReviewField>
				{/each}
				{#if group.title === 'Location'}
					<ReviewField
						{review}
						{focus}
						field="location"
						label="Coordinates (x · y · EPSG)"
						class="col-span-2"
					>
						<LocationEditor {review} />
					</ReviewField>
				{/if}
			</div>
		</section>
	{/each}

	{#if otherFields.length}
		<section>
			<h3 class="mb-1 text-xs font-semibold tracking-wide uppercase opacity-70">Other</h3>
			<div class="space-y-2">
				{#each otherFields as field (field)}
					<ReviewField {review} {focus} {field} label={field === 'layer' ? 'Layers' : field} />
				{/each}
			</div>
		</section>
	{/if}
</div>
