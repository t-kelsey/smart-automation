<script lang="ts">
	import { CheckIcon, FileUpIcon, LoaderCircleIcon, TriangleAlertIcon } from '@lucide/svelte';
	import { notify } from '#lib/components/toast/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	interface Entry {
		name: string;
		state: 'uploading' | 'done' | 'error';
		message?: string;
	}

	let entries = $state<Entry[]>([]);
	let dragging = $state(false);

	async function upload(files: FileList | File[]) {
		for (const file of files) {
			const entry: Entry = $state({ name: file.name, state: 'uploading' });
			entries.unshift(entry);
			try {
				const document = await data.uploads.upload(file);
				entry.state = 'done';
				entry.message =
					document.status === 'processing'
						? 'Sent to the extraction pipeline.'
						: 'Stored. No pipeline is configured, so it is not processed.';
			} catch (e) {
				entry.state = 'error';
				entry.message = e instanceof Error ? e.message : 'Upload failed.';
				notify.fromError(e, `Could not upload ${file.name}`);
			}
		}
	}

	function onDrop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		if (event.dataTransfer?.files.length) upload(event.dataTransfer.files);
	}

	function onSelect(event: Event & { currentTarget: HTMLInputElement }) {
		const input = event.currentTarget;
		if (input.files?.length) upload(input.files);
		input.value = '';
	}
</script>

<h1 class="mb-4 h1">Upload</h1>
<p class="mb-6 max-w-prose opacity-70">
	Upload borehole logs (PDF, scanned images or Word). Each document is stored and run through the
	extraction pipeline; the boreholes found in it appear in the list and on the map once it is done.
</p>

<label
	class="flex cursor-pointer flex-col items-center gap-3 rounded-3xl border-2 border-dashed px-6 py-16 text-center transition-colors {dragging
		? 'border-primary-500 bg-primary-500/10'
		: 'border-surface-300-700'}"
	ondragover={(e) => {
		e.preventDefault();
		dragging = true;
	}}
	ondragleave={() => (dragging = false)}
	ondrop={onDrop}
>
	<FileUpIcon class="size-10 opacity-60" />
	<span class="font-bold">Drop documents here or click to choose</span>
	<span class="text-xs opacity-60">{data.uploads.accept}</span>
	<input type="file" multiple accept={data.uploads.accept} class="sr-only" onchange={onSelect} />
</label>

{#if entries.length}
	<ul class="mt-6 space-y-2" aria-live="polite">
		{#each entries as entry, i (i)}
			<li
				class="flex items-center gap-3 card rounded-2xl preset-outlined-surface-200-800 px-4 py-3"
			>
				{#if entry.state === 'uploading'}
					<LoaderCircleIcon class="size-5 shrink-0 animate-spin" />
				{:else if entry.state === 'done'}
					<CheckIcon class="size-5 shrink-0 text-success-500" />
				{:else}
					<TriangleAlertIcon class="size-5 shrink-0 text-error-500" />
				{/if}
				<div class="min-w-0 flex-1">
					<p class="truncate font-bold">{entry.name}</p>
					{#if entry.message}<p class="text-xs opacity-60">{entry.message}</p>{/if}
				</div>
			</li>
		{/each}
	</ul>
{/if}
