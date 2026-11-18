<!--
@component
Coordinates of a borehole as x, y and EPSG code (WGS84 by default: x = longitude, y = latitude).
Saved together on Enter or when the focus leaves the three fields; Escape restores them.

@param review - Review of the borehole.
-->
<script lang="ts">
	import type { Review } from './review.ts';

	let { review }: { review: Review } = $props();

	let location = $derived(review.borehole.location);
	let error = $state<string | null>(null);
	let saving = $state(false);
	let group = $state<HTMLDivElement>();

	const inputs = () => [...(group?.querySelectorAll('input') ?? [])];
	const initial = () => [location?.lon ?? '', location?.lat ?? '', 4326].map(String);

	async function commit() {
		const [x, y, epsg] = inputs().map((input) => input.value.trim().replace(',', '.'));
		if ([x, y, epsg].join() === initial().join() || (!x && !y)) return;
		if (!x || !y || !epsg) {
			error = 'Give x, y and EPSG code.';
			return;
		}
		saving = true;
		error = await review.run(
			(s) => s.setLocation(review.borehole.id, { x: Number(x), y: Number(y), epsg: Number(epsg) }),
			'location'
		);
		saving = false;
	}

	function onkeydown(event: KeyboardEvent & { currentTarget: HTMLInputElement }) {
		if (event.key === 'Enter') event.currentTarget.blur();
		else if (event.key === 'Escape') {
			inputs().forEach((input, i) => (input.value = initial()[i]));
			error = null;
			event.currentTarget.blur();
		}
	}

	// Saves once the focus has left all three fields, not when moving between them.
	function onfocusout(event: FocusEvent) {
		if (!group?.contains(event.relatedTarget as Node | null)) void commit();
	}

	const fields = [
		{ label: 'x', title: 'x (longitude in WGS84)', value: () => location?.lon },
		{ label: 'y', title: 'y (latitude in WGS84)', value: () => location?.lat },
		{ label: 'EPSG', title: 'EPSG code of x and y', value: () => 4326 }
	];
</script>

<div class="min-w-0 flex-1">
	<div bind:this={group} class="flex gap-1" {onfocusout}>
		{#each fields as f (f.label)}
			<label class="flex min-w-0 flex-1 items-center gap-1 text-xs" title={f.title}>
				<span class="opacity-60">{f.label}</span>
				<input
					type="text"
					inputmode="decimal"
					value={f.value() ?? ''}
					placeholder="–"
					disabled={saving}
					class="input h-8 w-full border-transparent bg-transparent px-2 py-1 text-sm hover:border-surface-300-700 focus:border-primary-500"
					{onkeydown}
				/>
			</label>
		{/each}
	</div>
	{#if error}
		<p class="px-2 text-xs text-error-600-400" role="alert">{error}</p>
	{/if}
</div>
