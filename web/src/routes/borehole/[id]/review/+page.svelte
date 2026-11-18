<script lang="ts">
	import { goto, invalidate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import {
		ArrowRightIcon,
		BadgeCheckIcon,
		PartyPopperIcon,
		SkipForwardIcon,
		TriangleAlertIcon,
		Undo2Icon
	} from '@lucide/svelte';
	import BoreholePageHeader from '#lib/components/borehole/BoreholePageHeader.svelte';
	import CrossSection from '#lib/components/borehole/CrossSection.svelte';
	import HelpDrawer from '#lib/components/borehole/HelpDrawer.svelte';
	import PatternDefs from '#lib/components/borehole/PatternDefs.svelte';
	import { DocumentPane } from '#lib/components/document/index.ts';
	import CoreDataEditor from '#lib/components/review/CoreDataEditor.svelte';
	import LayerEditor from '#lib/components/review/LayerEditor.svelte';
	import SplitPane from '#lib/components/review/SplitPane.svelte';
	import { Review } from '#lib/components/review/review.ts';
	import { SourceFocus } from '#lib/components/review/source-focus.svelte.ts';
	import type { Borehole } from '#lib/domain/borehole.ts';
	import { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// The loaded borehole, replaced by the answer of every write (no reload, the focus stays put).
	let borehole = $derived(data.borehole);
	let review = $derived(new Review(borehole, data.service, update));

	let boreholeId = $derived(borehole.id);
	// Click selection is stored per borehole, so it carries over between details and review.
	let selection = $derived(new LayerSelection(boreholeId));
	$effect(() => selection.restore());
	let focus = $derived.by(() => {
		void boreholeId;
		return new SourceFocus();
	});
	$effect(() => focus.destroy);

	// Hovering a layer in the profile shows the whole layer (the cards show single fields themselves).
	let overProfile = $state(false);
	$effect(() => {
		const id = selection.hoveredId;
		if (id && overProfile) focus.hover(borehole.layers.find((l) => l.id === id)?.source ?? null);
	});

	// Moving from the data over to the document keeps the zoom there, so it can be read; leaving both
	// zooms back out.
	let documentArea = $state<HTMLElement>();
	const into = (area: HTMLElement | undefined, event: MouseEvent) =>
		!!area && area.contains(event.relatedTarget as Node | null);

	let openFlags = $derived(borehole.flags.filter((f) => !f.resolvedAt));
	let progress = $derived(review.progress);
	let layerFlags = $derived(openFlags.filter((f) => f.layerId).length);
	/** Set when the last open flag of this borehole was resolved here: offer the release. */
	let promptFor = $state<string | null>(null);
	let allChecked = $derived(!openFlags.length && !borehole.verified);

	function update(next: Borehole) {
		const before = openFlags.length;
		borehole = next;
		if (before && !next.flags.some((f) => !f.resolvedAt) && !next.verified) promptFor = next.id;
	}

	let scroller = $state<HTMLDivElement>();
	const motion = () =>
		window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';

	function jumpTo(id: string) {
		scroller?.querySelector(`#${id}`)?.scrollIntoView({ block: 'start', behavior: motion() });
	}

	/** Focuses the next flagged field after the focused one (wrapping around) and shows its source. */
	function nextFlag() {
		const fields = [...(scroller?.querySelectorAll<HTMLElement>('[data-flagged]') ?? [])];
		const active = document.activeElement;
		const after =
			active && scroller?.contains(active)
				? fields.find(
						(f) =>
							!f.contains(active) &&
							active.compareDocumentPosition(f) & Node.DOCUMENT_POSITION_FOLLOWING
					)
				: undefined;
		const target = after ?? fields[0];
		if (!target) return;
		target.scrollIntoView({ block: 'center', behavior: motion() });
		target
			.querySelector<HTMLElement>('[data-review-input], [data-flag-action]')
			?.focus({ preventScroll: true });
	}

	function onkeydown(event: KeyboardEvent) {
		if (event.key.toLowerCase() !== 'n' || event.ctrlKey || event.metaKey || event.altKey) return;
		const target = event.target as HTMLElement | null;
		if (target?.closest('input, textarea, select, [contenteditable="true"]')) return;
		event.preventDefault();
		nextFlag();
	}

	async function setVerified(verified: boolean) {
		const n = openFlags.length;
		if (
			verified &&
			n &&
			!confirm(`${n} open ${n === 1 ? 'flag is' : 'flags are'} left. Release the borehole anyway?`)
		)
			return;
		const error = await review.run((s) => s.setVerified(borehole.id, verified));
		if (!error) void invalidate('app:review-count');
	}
</script>

<svelte:head>
	<title>Review {borehole.name}</title>
</svelte:head>

<svelte:window {onkeydown} />

<PatternDefs />

<div class="-m-6 flex h-screen flex-col">
	<BoreholePageHeader {borehole} view="review">
		{#if progress.total}
			<div class="flex w-36 flex-col gap-1" title="Flags resolved by you or by the checks">
				<span class="text-xs tabular-nums opacity-70">
					{progress.done} of {progress.total} flags done
				</span>
				<div class="h-1 overflow-hidden rounded-full bg-surface-200-800">
					<div
						class="h-full rounded-full bg-success-500 transition-[width] duration-500 motion-reduce:transition-none"
						style:width="{(progress.done / progress.total) * 100}%"
					></div>
				</div>
			</div>
		{/if}
		<button
			type="button"
			class="btn preset-tonal-warning"
			disabled={!openFlags.length}
			title="Go to the next open flag (N)"
			onclick={nextFlag}
		>
			<SkipForwardIcon class="size-4" />
			Next flag
		</button>
		{#if borehole.verified}
			<button type="button" class="btn preset-tonal" onclick={() => setVerified(false)}>
				<Undo2Icon class="size-4" />
				Withdraw release
			</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				onclick={() => goto(resolve('/review'))}
			>
				Next borehole
				<ArrowRightIcon class="size-4" />
			</button>
		{:else}
			<button
				type="button"
				class="btn preset-filled-success-500 {allChecked
					? 'ring-4 ring-success-500/40 motion-safe:animate-pulse'
					: ''}"
				onclick={() => setVerified(true)}
			>
				<BadgeCheckIcon class="size-4" />
				Verify & release
			</button>
		{/if}
		<HelpDrawer layers={borehole.layers} />
	</BoreholePageHeader>

	{#if promptFor === borehole.id && allChecked}
		<div
			class="flex items-center gap-3 border-b border-success-500/40 bg-success-500/10 px-6 py-2 text-sm"
			role="status"
		>
			<PartyPopperIcon class="size-5 text-success-600-400" />
			<span class="flex-1 font-medium">All checked – release?</span>
			<button
				type="button"
				class="btn preset-filled-success-500 btn-sm"
				onclick={() => setVerified(true)}
			>
				<BadgeCheckIcon class="size-4" />
				Verify & release
			</button>
			<button type="button" class="btn preset-tonal btn-sm" onclick={() => (promptFor = null)}>
				Not yet
			</button>
		</div>
	{/if}

	<div class="flex min-h-0 flex-1 p-4">
		<SplitPane storageKey="review:split">
			{#snippet left()}
				<!-- Extracted data, edited in place; leaving it zooms the document back out. -->
				<div
					bind:this={scroller}
					class="relative min-h-0 flex-1 overflow-y-auto card border border-surface-200-800 bg-surface-50-950"
					role="region"
					aria-label="Extracted data"
					onmouseleave={(event) => (into(documentArea, event) ? focus.hold() : focus.leave())}
				>
					<nav
						class="sticky top-0 z-10 flex items-center gap-1 border-b border-surface-200-800 bg-surface-50-950 px-2 py-1.5 text-sm"
						aria-label="Sections"
					>
						<button
							type="button"
							class="btn btn-sm hover:preset-tonal"
							onclick={() => jumpTo('core-data')}
						>
							Core data
						</button>
						<span class="opacity-40">·</span>
						<button
							type="button"
							class="btn btn-sm hover:preset-tonal"
							onclick={() => jumpTo('layers')}
						>
							Layers ({borehole.layers.length})
							{#if layerFlags}
								<span class="flex items-center gap-0.5 text-warning-600-400">
									<TriangleAlertIcon class="size-3.5" />
									{layerFlags}
								</span>
							{/if}
						</button>
					</nav>

					<section id="core-data" class="scroll-mt-12 p-4">
						<h2 class="mb-2 h5">Core data</h2>
						<CoreDataEditor {review} {focus} />
					</section>

					<section id="layers" class="scroll-mt-12 border-t border-surface-200-800 p-4">
						<h2 class="mb-2 h5">Layers</h2>
						<div class="flex items-start gap-3">
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="sticky top-12 h-[min(70vh,44rem)] w-36 shrink-0"
								onmouseenter={() => (overProfile = true)}
								onmouseleave={() => (overProfile = false)}
							>
								<CrossSection {borehole} {selection} flagOf={review.layerSeverity} />
							</div>
							<div class="min-w-0 flex-1">
								<LayerEditor {review} {selection} {focus} />
							</div>
						</div>
					</section>

					<p
						class="sticky bottom-0 truncate border-t border-surface-200-800 bg-surface-50-950 px-4 py-1.5 text-xs [&_kbd]:font-semibold"
					>
						<span class="opacity-70">
							<kbd>N</kbd> next flag · <kbd>Enter</kbd>/<kbd>Tab</kbd> save & next ·
							<kbd>Ctrl+Enter</kbd> looks right · <kbd>Esc</kbd> undo typing
						</span>
					</p>
				</div>
			{/snippet}
			{#snippet right()}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					bind:this={documentArea}
					class="flex min-h-0 flex-1 flex-col"
					onmouseleave={(event) => {
						if (!into(scroller, event)) focus.leave();
					}}
				>
					<DocumentPane
						documents={borehole.documents}
						preferredId={review.mainDocumentId}
						source={focus.current}
						class="min-h-0 flex-1"
					/>
				</div>
			{/snippet}
		</SplitPane>
	</div>
</div>
