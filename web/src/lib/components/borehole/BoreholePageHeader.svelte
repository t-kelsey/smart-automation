<!--
@component
Header shared by the views of one borehole: title and place at the left, a switch between the
views in the middle, and the share button plus page-specific actions at the right.

@param borehole - Borehole the page is about.
@param view - The view that is currently shown.
@param [children] - Actions shown after the share button.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Share2Icon } from '@lucide/svelte';
	import { SegmentedControl } from '@skeletonlabs/skeleton-svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import type { Borehole } from '#lib/domain/borehole.ts';

	type View = 'details' | 'review';

	interface Props {
		borehole: Pick<Borehole, 'id' | 'name' | 'location'>;
		view: View;
		/** Page-specific actions, shown after the share button. */
		children?: Snippet;
	}

	let { borehole, view, children }: Props = $props();

	const views: { id: View; label: string }[] = [
		{ id: 'details', label: 'Details' },
		{ id: 'review', label: 'Review' }
	];

	function onViewChange(next: View) {
		if (next === view) return;
		const id = borehole.id;
		void goto(
			next === 'review'
				? resolve('/borehole/[id]/review', { id })
				: resolve('/borehole/[id]', { id })
		);
	}
</script>

<header
	class="grid shrink-0 items-center gap-4 border-b border-surface-200-800 bg-surface-50-950 px-6 py-4 md:grid-cols-[1fr_auto_1fr]"
>
	<div>
		<h1 class="h2">Borehole {borehole.name}</h1>
		<p class="text-sm opacity-70">{borehole.location?.place ?? ''}</p>
	</div>

	<SegmentedControl
		value={view}
		onValueChange={(details) => details.value && onViewChange(details.value as View)}
		aria-label="Borehole view"
	>
		<SegmentedControl.Control>
			<SegmentedControl.Indicator />
			{#each views as item (item.id)}
				<SegmentedControl.Item value={item.id}>
					<SegmentedControl.ItemText>{item.label}</SegmentedControl.ItemText>
					<SegmentedControl.ItemHiddenInput />
				</SegmentedControl.Item>
			{/each}
		</SegmentedControl.Control>
	</SegmentedControl>

	<div class="flex flex-wrap items-center gap-2 md:justify-end">
		<!-- TODO: implement sharing (e.g. copy link to this borehole). -->
		<button type="button" class="btn preset-tonal">
			<Share2Icon class="size-4" />
			Share
		</button>
		{@render children?.()}
	</div>
</header>
