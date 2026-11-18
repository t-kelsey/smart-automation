<!--
@component
One reviewed value: label, editor, history marks and the open flags right below it with "Looks
right" (resolves the flag, also Ctrl+Enter in the field) and "Apply …" for a validator
suggestion. Hovering the field previews its source in the document, focusing it pins the source.

@param review - Review of the borehole.
@param focus - Receives the field's source.
@param field - API field name.
@param label - Shown above the editor.
@param [layerId] - Layer of a layer field.
@param [children] - The editor; without one only the flags are shown.
@param [class] - Extra classes for the root element.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { CheckIcon, OctagonAlertIcon, TriangleAlertIcon, WandSparklesIcon } from '@lucide/svelte';
	import FieldMarks from './FieldMarks.svelte';
	import { formatValue, type Review } from './review.ts';
	import type { SourceFocus } from './source-focus.svelte.ts';

	interface Props {
		review: Review;
		focus: SourceFocus;
		field: string;
		label: string;
		layerId?: string | null;
		children?: Snippet;
		class?: string;
	}

	let {
		review,
		focus,
		field,
		label,
		layerId = null,
		children,
		class: className = ''
	}: Props = $props();

	let flags = $derived(review.openFlags(field, layerId));
	let source = $derived(review.source(field, layerId));
	let root = $state<HTMLDivElement>();

	/** Resolves the flag and keeps the focus in the field (the button goes away with the flag). */
	async function resolve(flagId: string) {
		const input = root?.querySelector<HTMLElement>('[data-review-input]');
		await review.resolve(flagId);
		input?.focus({ preventScroll: true });
	}

	function onkeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && flags[0]) {
			event.preventDefault();
			void resolve(flags[0].id);
		}
	}
</script>

<!-- Hover preview and Ctrl+Enter for the field inside: -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
	bind:this={root}
	class="min-w-0 {className}"
	role="group"
	aria-label={label}
	data-review-target="{layerId ?? 'borehole'}:{field}"
	data-flagged={flags.length ? '' : undefined}
	onmouseenter={() => focus.hover(source)}
	onmouseleave={() => focus.unhover(source)}
	onfocusin={() => focus.pin(source)}
	onfocusout={(event) => {
		if (!event.currentTarget.contains(event.relatedTarget as Node | null)) focus.pin(null);
	}}
	{onkeydown}
>
	<div class="flex h-6 items-center gap-1">
		<span class="min-w-0 flex-1 truncate text-xs opacity-60">{label}</span>
		<FieldMarks {review} {field} {layerId} />
	</div>
	{#if children}
		<div class="rounded-base {review.tint(field, layerId)}">
			{@render children()}
		</div>
	{/if}
	{#each flags as flag (flag.id)}
		<div class="mt-1 flex flex-wrap items-start gap-x-2 gap-y-1 text-xs">
			<p class="flex min-w-0 flex-1 basis-48 gap-1.5">
				{#if flag.severity === 'error'}
					<OctagonAlertIcon class="mt-px size-3.5 shrink-0 text-error-500" />
				{:else}
					<TriangleAlertIcon class="mt-px size-3.5 shrink-0 text-warning-500" />
				{/if}
				<span>{flag.message}</span>
			</p>
			<span class="flex flex-wrap gap-1">
				<button
					type="button"
					class="btn h-6 preset-tonal-success px-2 text-xs btn-sm"
					title="The value is right (Ctrl+Enter)"
					data-flag-action
					onclick={() => resolve(flag.id)}
				>
					<CheckIcon class="size-3.5" />
					Looks right
				</button>
				{#if flag.suggestion !== null && flag.suggestion !== undefined}
					<button
						type="button"
						class="btn h-6 max-w-64 preset-tonal-primary px-2 text-xs btn-sm"
						title="Save the suggested value"
						data-flag-action
						onclick={() => review.apply(flag)}
					>
						<WandSparklesIcon class="size-3.5 shrink-0" />
						<span class="truncate">Apply {formatValue(flag.suggestion)}</span>
					</button>
				{/if}
			</span>
		</div>
	{/each}
</div>
