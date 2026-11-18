<!--
@component
Deletes a borehole after a confirmation (layers, flags and history go with it; documents stay).

@param borehole - The borehole to delete.
@param [small] - Icon-only button for table rows.
@param [ondeleted] - Called after the deletion; defaults to going to the borehole list.
-->
<script lang="ts">
	import { Trash2Icon } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { notify } from '#lib/components/toast/index.ts';
	import { createServices } from '#lib/services/index.ts';

	interface Props {
		borehole: { id: string; name: string };
		small?: boolean;
		ondeleted?: () => unknown;
	}

	let { borehole, small = false, ondeleted }: Props = $props();

	async function remove() {
		if (
			!confirm(
				`Delete borehole ${borehole.name} with its layers, flags and history? This cannot be undone.`
			)
		)
			return;
		try {
			const { boreholes } = await createServices({ fetch });
			await boreholes.deleteBorehole(borehole.id);
			notify.success(`Borehole ${borehole.name} deleted`);
			await (ondeleted ? ondeleted() : goto(resolve('/borehole')));
		} catch (e) {
			notify.fromError(e, 'Could not delete');
		}
	}
</script>

<button
	type="button"
	class={small ? 'btn-icon btn-icon-sm hover:preset-tonal-error' : 'btn preset-tonal-error'}
	title="Delete borehole"
	aria-label="Delete borehole {borehole.name}"
	onclick={remove}
>
	<Trash2Icon class="size-4" />
	{#if !small}Delete{/if}
</button>
