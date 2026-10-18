<script lang="ts">
	import { resolve } from '$app/paths';
	import {
		ArrowRightIcon,
		FileIcon,
		CombineIcon,
		FileUpIcon,
		FolderUpIcon,
		XIcon
	} from '@lucide/svelte';
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

	/** Images of one folder are the pages of one log: merge each folder into one PDF document. */
	async function addFolder(files: File[]) {
		const groups: Record<string, File[]> = {};
		const rest: File[] = [];
		for (const file of files) {
			if (!data.uploads.isMergeableImage(file)) {
				rest.push(file);
				continue;
			}
			const parts = (file.webkitRelativePath || file.name).split('/');
			const folder = parts.length > 1 ? parts[parts.length - 2] : 'document';
			(groups[folder] ??= []).push(file);
		}
		const merged: File[] = [];
		for (const [folder, images] of Object.entries(groups)) {
			try {
				merged.push(await data.uploads.combineImages(images, folder));
			} catch (e) {
				notify.error(
					`${folder}: images could not be combined`,
					e instanceof Error ? e.message : ''
				);
			}
		}
		add([...merged, ...rest]);
	}

	function onSelectFolder(event: Event & { currentTarget: HTMLInputElement }) {
		const input = event.currentTarget;
		if (input.files?.length) void addFolder([...input.files]);
		input.value = '';
	}

	/** Combines all queued PNG/JPEG images into one document, e.g. when they were picked as single files. */
	async function mergeQueuedImages() {
		const images = queued.filter((q) => data.uploads.isMergeableImage(q.file));
		try {
			const name = images[0].file.name.replace(/\.[^.]+$/, '');
			const merged = await data.uploads.combineImages(
				images.map((q) => q.file),
				`${name}_combined`
			);
			images.forEach((q) => unqueueFile(q.id));
			queueFiles([merged]);
		} catch (e) {
			notify.error('Images could not be combined', e instanceof Error ? e.message : '');
		}
	}

	const mergeableCount = $derived(
		queued.filter((q) => data.uploads.isMergeableImage(q.file)).length
	);
	const needsMerge = $derived(mergeableCount > 1);

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
	Upload borehole logs (PDF, scanned images or Word). Pages that come as separate image files can be
	merged into one document. Nothing is uploaded yet. Remove the files you do not want, then continue
	to choose the AI models and start the extraction.
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

<div class="mt-3 flex flex-wrap items-center gap-3 text-sm">
	<label class="btn preset-tonal">
		<FolderUpIcon class="size-4" />
		Choose a folder of page images
		<!-- @ts-expect-error webkitdirectory is not in the typings -->
		<input type="file" webkitdirectory class="sr-only" onchange={onSelectFolder} />
	</label>
	<span class="opacity-60"
		>The PNG/JPEG images of a folder are merged into one document, ordered by file name.</span
	>
</div>

{#if needsMerge}
	<div
		class="mt-4 flex flex-wrap items-center gap-4 card rounded-2xl preset-filled-warning-500 p-4"
		role="alert"
	>
		<p class="min-w-0 flex-1 font-bold">
			{mergeableCount} separate images are queued. Merge them into one document first, otherwise the extraction
			fails.
		</p>
		<button type="button" class="btn preset-filled-primary-500 btn-lg" onclick={mergeQueuedImages}>
			<CombineIcon class="size-5" />
			Merge {mergeableCount} images into one document
		</button>
	</div>
{/if}

<div class="mt-6 flex justify-end">
	{#if queued.length && !needsMerge}
		<a href={resolve('/upload/config')} class="btn preset-filled-primary-500 btn-lg">
			Continue with {queued.length}
			{queued.length === 1 ? 'file' : 'files'}
			<ArrowRightIcon class="size-5" />
		</a>
	{:else}
		<button
			type="button"
			class="btn preset-filled-primary-500 btn-lg"
			disabled
			title={needsMerge ? 'Merge the images into one document first' : undefined}
		>
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
