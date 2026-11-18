<!--
@component
A value that is edited in place: saved on Enter or when the field loses focus, Escape restores it.
A rejected value stays in the field with the reason below it.

@param value - Stored value; `null` shows an empty field.
@param label - Accessible name.
@param onsave - Saves the typed text; resolves to an error message, or `null` when saved.
@param [type] - Input type.
@param [class] - Extra classes for the root element.
-->
<script lang="ts">
	interface Props {
		value: string | null;
		label: string;
		onsave: (text: string) => Promise<string | null>;
		type?: 'text' | 'number' | 'date';
		class?: string;
	}

	let { value, label, onsave, type = 'text', class: className = '' }: Props = $props();

	let error = $state<string | null>(null);
	let saving = $state(false);

	async function commit(input: HTMLInputElement) {
		if (input.value === (value ?? '')) {
			error = null;
			return;
		}
		saving = true;
		error = await onsave(input.value);
		saving = false;
	}

	function onkeydown(event: KeyboardEvent & { currentTarget: HTMLInputElement }) {
		if (event.key === 'Enter') event.currentTarget.blur();
		else if (event.key === 'Escape') {
			event.currentTarget.value = value ?? '';
			error = null;
			event.currentTarget.blur();
		}
	}
</script>

<div class="min-w-0 {className}">
	<input
		{type}
		value={value ?? ''}
		step={type === 'number' ? 'any' : undefined}
		aria-label={label}
		aria-invalid={!!error}
		placeholder="–"
		disabled={saving}
		class="input h-8 w-full min-w-16 border-transparent bg-transparent px-2 py-1 text-sm hover:border-surface-300-700 focus:border-primary-500 {error
			? 'border-error-500!'
			: ''}"
		onblur={(event) => commit(event.currentTarget)}
		{onkeydown}
	/>
	{#if error}
		<p class="px-2 text-xs text-error-600-400" role="alert">{error}</p>
	{/if}
</div>
