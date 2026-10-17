<script lang="ts">
	import { resolve } from '$app/paths';
	import { CheckIcon, ExternalLinkIcon, Share2Icon } from '@lucide/svelte';
	import type { BoreholeSummary, MapPoint } from '#lib/domain/borehole.ts';

	interface Props {
		/** Undefined while the card is hidden. */
		point?: MapPoint;
		/** Undefined while the summary is still loading. */
		summary?: BoreholeSummary;
		onEnter?: () => void;
		onLeave?: () => void;
	}

	let { point, summary, onEnter, onLeave }: Props = $props();

	let copied = $state(false);

	async function share() {
		if (!point) return;
		const url = new URL(resolve('/borehole/[id]', { id: point.id }), location.origin).href;
		if (navigator.share) {
			try {
				await navigator.share({ title: point.name, url });
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

<!-- One card is shared by all dots; the map moves it to the hovered dot. -->
{#if point}
	<div
		role="tooltip"
		class="w-64 space-y-3 card bg-surface-50-950 p-3 shadow-xl"
		onpointerenter={onEnter}
		onpointerleave={onLeave}
	>
		<div>
			<p class="font-semibold">{point.name}</p>
			<p class="text-xs opacity-60">
				{#if !summary}<span class="inline-block h-3 w-20 animate-pulse rounded bg-surface-300-700"
					></span>{:else}{summary.date ?? 'Date unknown'}{/if}
			</p>
		</div>
		<dl class="grid grid-cols-2 gap-x-2 gap-y-1 text-sm">
			<dt class="opacity-60">Height</dt>
			<dd class="text-right">
				{#if !summary}<span class="inline-block h-3 w-16 animate-pulse rounded bg-surface-300-700"
					></span>{:else}{summary.elevation === null ? '–' : `${summary.elevation} m ü. NN`}{/if}
			</dd>
			<dt class="opacity-60">Depth</dt>
			<dd class="text-right">
				{#if !summary}<span class="inline-block h-3 w-12 animate-pulse rounded bg-surface-300-700"
					></span>{:else}{summary.totalDepth === null ? '–' : `${summary.totalDepth} m`}{/if}
			</dd>
		</dl>
		<div class="flex gap-2">
			<button type="button" class="btn flex-1 preset-tonal btn-sm" onclick={share}>
				{#if copied}<CheckIcon class="size-4" /> Copied{:else}<Share2Icon class="size-4" /> Share{/if}
			</button>
			<a
				class="btn flex-1 preset-filled-primary-500 btn-sm"
				href={resolve('/borehole/[id]', { id: point.id })}
			>
				<ExternalLinkIcon class="size-4" /> Details
			</a>
		</div>
	</div>
{/if}
