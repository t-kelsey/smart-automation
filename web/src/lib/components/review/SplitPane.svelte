<!--
@component
Two panes side by side with a draggable splitter between them. The position is kept in local
storage; the splitter can also be moved with the arrow keys (Shift for bigger steps), Home and End.

@param left - Content of the left pane.
@param right - Content of the right pane.
@param storageKey - Local storage key of the position.
@param [initial] - Width of the left pane in percent.
@param [minLeft] - Minimum width of the left pane in pixels.
@param [minRight] - Minimum width of the right pane in pixels.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		left: Snippet;
		right: Snippet;
		storageKey: string;
		initial?: number;
		minLeft?: number;
		minRight?: number;
	}

	let { left, right, storageKey, initial = 40, minLeft = 380, minRight = 320 }: Props = $props();

	function read(): number | null {
		try {
			const value = Number(localStorage.getItem(storageKey));
			return value > 0 && value < 100 ? value : null;
		} catch {
			return null; // SSR, or storage blocked
		}
	}

	// Only the starting position, read once:
	// svelte-ignore state_referenced_locally
	let percent = $state(read() ?? initial);
	let width = $state(0);
	let container = $state<HTMLDivElement>();
	let dragging = $state(false);

	let min = $derived(width ? Math.min(50, (minLeft / width) * 100) : 0);
	let max = $derived(width ? Math.max(50, 100 - (minRight / width) * 100) : 100);
	let shown = $derived(Math.min(max, Math.max(min, percent)));

	function set(value: number) {
		percent = Math.min(max, Math.max(min, value));
		try {
			localStorage.setItem(storageKey, String(Math.round(percent * 10) / 10));
		} catch {
			// storage blocked: the position then only lives until the page is left
		}
	}

	function onpointermove(event: PointerEvent) {
		if (!dragging || !container) return;
		const rect = container.getBoundingClientRect();
		set(((event.clientX - rect.left) / rect.width) * 100);
	}

	function onkeydown(event: KeyboardEvent) {
		const step = event.shiftKey ? 10 : 2;
		if (event.key === 'ArrowLeft') set(shown - step);
		else if (event.key === 'ArrowRight') set(shown + step);
		else if (event.key === 'Home') set(min);
		else if (event.key === 'End') set(max);
		else return;
		event.preventDefault();
	}
</script>

<div
	bind:this={container}
	bind:clientWidth={width}
	class="flex min-h-0 flex-1 {dragging ? 'cursor-col-resize select-none' : ''}"
>
	<div class="flex min-h-0 min-w-0 shrink-0 flex-col" style:width="{shown}%">
		{@render left()}
	</div>
	<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
	<div
		class="group flex w-3 shrink-0 cursor-col-resize touch-none items-center justify-center outline-none"
		role="separator"
		aria-orientation="vertical"
		aria-label="Resize the panes"
		aria-valuenow={Math.round(shown)}
		aria-valuemin={Math.round(min)}
		aria-valuemax={Math.round(max)}
		tabindex="0"
		onpointerdown={(event) => {
			dragging = true;
			event.currentTarget.setPointerCapture(event.pointerId);
		}}
		{onpointermove}
		onpointerup={() => (dragging = false)}
		onpointercancel={() => (dragging = false)}
		ondblclick={() => set(initial)}
		{onkeydown}
	>
		<span
			class="h-12 w-1 rounded-full bg-surface-300-700 transition-colors group-hover:bg-primary-500 group-focus-visible:bg-primary-500 {dragging
				? 'bg-primary-500'
				: ''}"
		></span>
	</div>
	<div class="flex min-h-0 min-w-0 flex-1 flex-col">
		{@render right()}
	</div>
</div>
