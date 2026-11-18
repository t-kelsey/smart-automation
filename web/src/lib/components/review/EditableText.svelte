<!--
@component
A value that is edited in place: saved when the field loses focus; Enter saves and moves to the
next field (like Tab), Escape restores the value. Numbers are typed as text and accept a decimal
comma; an invalid number is not saved but shown with a message. Empty clears the value. A small
check confirms a save; a rejected value stays in the field with the reason below it.

@param value - Stored value; `null` shows an empty field.
@param label - Accessible name.
@param onsave - Saves the typed text; resolves to an error message, or `null` when saved.
@param [type] - Kind of value.
@param [multiline] - Long text: a text area that grows with its content.
@param [class] - Extra classes for the root element.
-->
<script lang="ts">
	import { CheckIcon } from '@lucide/svelte';
	import { autosize, focusNext } from './review.ts';

	interface Props {
		value: string | null;
		label: string;
		onsave: (text: string) => Promise<string | null>;
		type?: 'text' | 'number' | 'date';
		multiline?: boolean;
		class?: string;
	}

	let {
		value,
		label,
		onsave,
		type = 'text',
		multiline = false,
		class: className = ''
	}: Props = $props();

	const NUMBER = /^[+-]?(\d+([.,]\d*)?|[.,]\d+)$/;

	let error = $state<string | null>(null);
	let saved = $state(false);
	let savedTimer: ReturnType<typeof setTimeout> | undefined;

	/** Whether the typed text means the stored value (numbers compare by value: "3,10" is 3.1). */
	function unchanged(text: string) {
		const stored = value ?? '';
		if (type !== 'number' || !text || !stored) return text === stored;
		return Number(text.replace(',', '.')) === Number(stored);
	}

	async function commit(input: HTMLInputElement | HTMLTextAreaElement) {
		const text = input.value.trim();
		if (unchanged(text)) {
			error = null;
			input.value = value ?? '';
			return;
		}
		if (type === 'number' && text && !NUMBER.test(text)) {
			error = 'Not a number. Use e.g. 9.5 or 9,5.';
			return;
		}
		error = await onsave(text);
		if (error) return;
		input.value = value ?? '';
		saved = true;
		clearTimeout(savedTimer);
		savedTimer = setTimeout(() => (saved = false), 1500);
	}

	function onkeydown(
		event: KeyboardEvent & { currentTarget: HTMLInputElement | HTMLTextAreaElement }
	) {
		// Ctrl+Enter is "looks right" for the field's flag (see ReviewField).
		if (event.key === 'Enter' && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
			event.preventDefault();
			focusNext(event.currentTarget);
		} else if (event.key === 'Escape') {
			event.currentTarget.value = value ?? '';
			error = null;
			event.currentTarget.blur();
		}
	}

	const inputClass =
		'input w-full min-w-16 border-transparent bg-transparent px-2 py-1 text-sm hover:border-surface-300-700 focus:border-primary-500';
</script>

<div class="relative min-w-0 {className}">
	{#if multiline}
		<textarea
			{@attach autosize(value)}
			rows="1"
			value={value ?? ''}
			aria-label={label}
			aria-invalid={!!error}
			placeholder="–"
			data-review-input
			class="{inputClass} block resize-none overflow-hidden pr-7 {error ? 'border-error-500!' : ''}"
			onblur={(event) => commit(event.currentTarget)}
			{onkeydown}></textarea>
	{:else}
		<input
			type={type === 'date' ? 'date' : 'text'}
			inputmode={type === 'number' ? 'decimal' : undefined}
			value={value ?? ''}
			aria-label={label}
			aria-invalid={!!error}
			placeholder="–"
			data-review-input
			class="{inputClass} h-8 pr-7 {error ? 'border-error-500!' : ''}"
			onblur={(event) => commit(event.currentTarget)}
			{onkeydown}
		/>
	{/if}
	{#if saved}
		<CheckIcon
			class="pointer-events-none absolute top-2 right-2 size-4 text-success-600-400"
			aria-label="Saved"
		/>
	{/if}
	{#if error}
		<p class="px-2 text-xs text-error-600-400" role="alert">{error}</p>
	{/if}
</div>
