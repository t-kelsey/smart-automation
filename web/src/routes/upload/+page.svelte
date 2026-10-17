<script lang="ts">
	import { resolve } from '$app/paths';
	import { ArrowRightIcon, FileIcon, FileUpIcon, XIcon } from '@lucide/svelte';
	import { notify } from '#lib/components/toast/index.ts';
	import { getQueuedFiles, queueFiles, unqueueFile } from '#lib/upload-queue.svelte.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const queued = $derived(getQueuedFiles());
	let dragging = $state(false);

	function add(files: FileList | File[]) {
		const accepted: File[] = [];
		for (const file of files) {
			if (data.uploads.isSupported(file)) accepted.push(file);
			else notify.error(`${file.name}: unsupported file type`, `Expected ${data.uploads.accept}`);
		}
		if (accepted.length) queueFiles(accepted);
	}

	function onDrop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		if (event.dataTransfer?.files.length) add(event.dataTransfer.files);
	}

	function onSelect(event: Event & { currentTarget: HTMLInputElement }) {
		const input = event.currentTarget;
		if (input.files?.length) add(input.files);
		input.value = '';
	}

	function formatSize(bytes: number): string {
		return bytes < 1024 * 1024
			? `${Math.max(1, Math.round(bytes / 1024))} KB`
			: `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}
</script>

<h1 class="mb-4 h1">Upload</h1>
<p class="mb-6 max-w-prose opacity-70">
	Upload borehole logs (PDF, scanned images or Word). Nothing is uploaded yet. Remove the files you
	do not want, then continue to choose the AI models and start the extraction.
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

<div class="mt-6 flex justify-end">
	{#if queued.length}
		<a href={resolve('/upload/config')} class="btn preset-filled-primary-500 btn-lg">
			Continue with {queued.length}
			{queued.length === 1 ? 'file' : 'files'}
			<ArrowRightIcon class="size-5" />
		</a>
	{:else}
		<button type="button" class="btn preset-filled-primary-500 btn-lg" disabled>
			Continue
			<ArrowRightIcon class="size-5" />
		</button>
	{/if}
</div>

{#if queued.length}
	<ul class="mt-4 space-y-2" aria-live="polite">
		{#each queued as { id, file } (id)}
			<li
				class="flex items-center gap-3 card rounded-2xl preset-outlined-surface-200-800 px-4 py-3"
			>
				<FileIcon class="size-5 shrink-0 opacity-60" />
				<div class="min-w-0 flex-1">
					<p class="truncate font-bold">{file.name}</p>
					<p class="text-xs opacity-60">{formatSize(file.size)}</p>
				</div>
				<button
					type="button"
					class="btn-icon size-8 hover:preset-tonal"
					aria-label="Remove {file.name}"
					onclick={() => unqueueFile(id)}
				>
					<XIcon class="size-4" />
				</button>
			</li>
		{/each}
	</ul>
{/if}
