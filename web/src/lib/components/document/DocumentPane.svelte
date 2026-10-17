<!--
@component
A document viewer for one borehole's documents: shows the original document and lets the user
switch to its additional information files.

@param documents - The documents of a borehole.
@param [class] - Extra classes for the root element.
-->
<script lang="ts">
	import { FileQuestionMarkIcon } from '@lucide/svelte';
	import type { BoreholeDocument } from '#lib/domain/borehole.ts';
	import { splitDocuments } from '#lib/domain/documents.ts';
	import DocumentViewer from './DocumentViewer.svelte';

	interface Props {
		documents: BoreholeDocument[];
		class?: string;
	}

	let { documents, class: className = '' }: Props = $props();

	let { original, additional } = $derived(splitDocuments(documents));
	/** Shown in the viewer; `null` selects the original. */
	let selectedId = $state<string | null>(null);

	let shown = $derived(
		documents.find((doc) => doc.id === selectedId) ?? original ?? additional[0] ?? null
	);
</script>

<div class="flex h-full min-h-0 flex-col gap-2 {className}">
	{#if additional.length}
		<label class="flex items-center gap-2 text-sm">
			<span class="opacity-60">Document</span>
			<select
				class="select min-w-0 flex-1"
				value={shown?.id}
				onchange={(event) => (selectedId = event.currentTarget.value)}
			>
				{#each [...(original ? [original] : []), ...additional] as doc (doc.id)}
					<option value={doc.id}>
						{doc.role === 'original' ? 'Original: ' : ''}{doc.name}
					</option>
				{/each}
			</select>
		</label>
	{/if}

	{#if shown}
		<DocumentViewer document={shown} class="flex-1" />
	{:else}
		<div
			class="flex flex-1 flex-col items-center justify-center gap-2 card border border-surface-200-800 bg-surface-50-950 p-6 opacity-60"
		>
			<FileQuestionMarkIcon class="size-10" />
			<p>No documents are linked to this borehole.</p>
		</div>
	{/if}
</div>
