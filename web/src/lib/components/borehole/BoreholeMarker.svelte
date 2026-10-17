<script lang="ts">
	import { resolve } from '$app/paths';
	import { Portal, Tooltip } from '@skeletonlabs/skeleton-svelte';
	import { CheckIcon, ExternalLinkIcon, Share2Icon } from '@lucide/svelte';
	import type { BoreholeSummary } from '#lib/domain/borehole.ts';

	interface Props {
		borehole: BoreholeSummary;
	}

	let { borehole }: Props = $props();

	let copied = $state(false);

	async function share() {
		const url = new URL(resolve('/borehole/[id]', { id: borehole.id }), location.origin).href;
		if (navigator.share) {
			try {
				await navigator.share({ title: borehole.name, url });
			} catch {
				// Share sheet dismissed.
			}
			return;
		}
		await navigator.clipboard.writeText(url);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}
</script>

<Tooltip
	positioning={{ placement: 'top', offset: { mainAxis: 8 } }}
	interactive
	openDelay={100}
	closeDelay={200}
>
	<Tooltip.Trigger
		class="block size-3.5 cursor-pointer rounded-full border-2 border-white shadow-md {borehole.verified
			? 'bg-success-500'
			: 'bg-primary-500'}"
		aria-label={borehole.name}
	/>
	<Portal>
		<Tooltip.Positioner>
			<Tooltip.Content class="w-64 space-y-3 card bg-surface-50-950 p-3 shadow-xl">
				<div>
					<p class="font-semibold">{borehole.name}</p>
					<p class="text-xs opacity-60">{borehole.date ?? 'Date unknown'}</p>
				</div>
				<dl class="grid grid-cols-2 gap-x-2 text-sm">
					<dt class="opacity-60">Height</dt>
					<dd class="text-right">
						{borehole.elevation === null ? '–' : `${borehole.elevation} m ü. NN`}
					</dd>
					<dt class="opacity-60">Depth</dt>
					<dd class="text-right">{borehole.totalDepth} m</dd>
				</dl>
				<div class="flex gap-2">
					<button type="button" class="btn flex-1 preset-tonal btn-sm" onclick={share}>
						{#if copied}<CheckIcon class="size-4" /> Copied{:else}<Share2Icon class="size-4" /> Share{/if}
					</button>
					<a
						class="btn flex-1 preset-filled-primary-500 btn-sm"
						href={resolve('/borehole/[id]', { id: borehole.id })}
					>
						<ExternalLinkIcon class="size-4" /> Details
					</a>
				</div>
			</Tooltip.Content>
		</Tooltip.Positioner>
	</Portal>
</Tooltip>
