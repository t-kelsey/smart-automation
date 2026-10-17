<script lang="ts">
	import { resolve } from '$app/paths';
	import { CircleCheck, Circle } from '@lucide/svelte';
	import type { BoreholeSummary } from '#lib/domain/borehole.ts';

	interface Props {
		items: BoreholeSummary[];
		/** Render names as links. Turn off when the table sits inside another link. */
		links?: boolean;
	}

	let { items, links = true }: Props = $props();
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
				</tr>
			{:else}
				<tr><td colspan="6" class="py-8 text-center opacity-60">No boreholes found.</td></tr>
			{/each}
		</tbody>
	</table>
</div>
