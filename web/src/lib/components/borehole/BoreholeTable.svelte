<script lang="ts">
	import { resolve } from '$app/paths';
	import { CircleCheck, Circle } from '@lucide/svelte';
	import { invalidateAll } from '$app/navigation';
	import type { BoreholeSummary } from '#lib/domain/borehole.ts';
	import DeleteBoreholeButton from './DeleteBoreholeButton.svelte';

	interface Props {
		items: BoreholeSummary[];
		/** Render names as links. Turn off when the table sits inside another link. */
		links?: boolean;
		/** Show a delete button per row; the list reloads afterwards. */
		deletable?: boolean;
	}

	let { items, links = true, deletable = false }: Props = $props();
</script>

<div class="table-wrap">
	<table class="table caption-bottom">
		<thead>
			<tr>
				<th>Name</th>
				<th>Place</th>
				<th>Date</th>
				<th class="text-right!">Elevation (m)</th>
				<th class="text-right!">Depth (m)</th>
				<th>Verified</th>
				<th>Flags</th>
				{#if deletable}<th><span class="sr-only">Actions</span></th>{/if}
			</tr>
		</thead>
		<tbody class="[&>tr]:hover:preset-tonal">
			{#each items as borehole (borehole.id)}
				<tr>
					<td>
						{#if links}
							<a class="anchor" href={resolve('/borehole/[id]', { id: borehole.id })}
								>{borehole.name}</a
							>
						{:else}
							{borehole.name}
						{/if}
					</td>
					<td>{borehole.location?.place ?? '–'}</td>
					<td>{borehole.date ?? '–'}</td>
					<td class="text-right">{borehole.elevation ?? '–'}</td>
					<td class="text-right">{borehole.totalDepth ?? '–'}</td>
					<td>
						{#if borehole.verified}
							<CircleCheck class="size-4 text-success-500" aria-label="Verified" />
						{:else}
							<Circle class="size-4 opacity-40" aria-label="Not verified" />
						{/if}
					</td>
					<td>
						{#if borehole.openFlagCount}
							<span
								class="badge preset-filled-warning-500"
								title="{borehole.openFlagCount} open flags to review"
							>
								{borehole.openFlagCount}
							</span>
						{/if}
					</td>
					{#if deletable}
						<td class="text-right">
							<DeleteBoreholeButton {borehole} small ondeleted={invalidateAll} />
						</td>
					{/if}
				</tr>
			{:else}
				<tr
					><td colspan={deletable ? 8 : 7} class="py-8 text-center opacity-60"
						>No boreholes found.</td
					></tr
				>
			{/each}
		</tbody>
	</table>
</div>
