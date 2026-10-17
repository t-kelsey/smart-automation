<!--
@component
Viewer for a single document (PDF or image) with a toolbar for zoom, page navigation and download.
Fills the height of its parent, so give the parent a height. State is local, so several viewers
can sit side by side (e.g. for comparing documents).

@param document - Document to show; needs `name`, `type` and `url` (the file link).
@param [class] - Extra classes for the root element.

@example
```html
<div class="h-[80vh]"><DocumentViewer document={doc} /></div>
```
-->

<script lang="ts">
	import {
		ChevronLeftIcon,
		ChevronRightIcon,
		DownloadIcon,
		FileQuestionMarkIcon,
		MaximizeIcon,
		ZoomInIcon,
		ZoomOutIcon
	} from '@lucide/svelte';
	import { Alert } from '#lib/components/alert/index.ts';
	import type { BoreholeDocument } from '#lib/domain/borehole.ts';
	import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from 'pdfjs-dist';

	interface Props {
		document: Pick<BoreholeDocument, 'name' | 'type' | 'url'>;
		class?: string;
	}

	let { document: doc, class: className = '' }: Props = $props();

	const MIN_ZOOM = 0.25;
	const MAX_ZOOM = 5;
	const ZOOM_STEP = 1.25;

	/** 1 = fit to the viewer width. */
	let zoom = $state(1);
	let page = $state(1);
	let pageCount = $state(1);
	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let errorMessage = $state('');

	let scroller = $state<HTMLDivElement>();
	let canvas = $state<HTMLCanvasElement>();
	let containerWidth = $state(0);

	let pdf = $state.raw<PDFDocumentProxy | null>(null);

	let supported = $derived(!!doc.url && (doc.type === 'pdf' || doc.type === 'image'));
	let isPdf = $derived(doc.type === 'pdf');

	function setZoom(value: number) {
		zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
	}

	function goToPage(value: number) {
		page = Math.min(pageCount, Math.max(1, value));
		scroller?.scrollTo({ top: 0 });
	}

	// Reset view state and (re)load whenever another document is shown.
	$effect(() => {
		const { url, type } = doc;
		zoom = 1;
		page = 1;
		pageCount = 1;
		pdf = null;
		errorMessage = '';
		status = 'loading';
		if (!url || type !== 'pdf') return;

		let cancelled = false;
		let task: PDFDocumentLoadingTask | undefined;
		(async () => {
			try {
				// Loaded on demand: pdf.js needs browser APIs and is large.
				const [pdfjs, { default: workerSrc }] = await Promise.all([
					import('pdfjs-dist'),
					import('pdfjs-dist/build/pdf.worker.min.mjs?url')
				]);
				pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;
				task = pdfjs.getDocument({ url });
				const result = await task.promise;
				if (cancelled) return;
				pageCount = result.numPages;
				pdf = result;
			} catch (e) {
				if (cancelled) return;
				errorMessage = e instanceof Error ? e.message : 'The PDF could not be loaded.';
				status = 'error';
			}
		})();

		return () => {
			cancelled = true;
			void task?.destroy();
		};
	});

	// Draw the current page; re-runs on page, zoom and width changes.
	$effect(() => {
		if (!pdf || !canvas || containerWidth <= 0) return;
		const target = canvas;
		const source = pdf;
		const width = containerWidth;
		const scale = zoom;
		const pageNumber = page;

		let renderTask: RenderTask | undefined;
		let cancelled = false;
		(async () => {
			try {
				const pdfPage = await source.getPage(pageNumber);
				if (cancelled) return;
				const base = pdfPage.getViewport({ scale: 1 });
				const cssScale = (width / base.width) * scale;
				const viewport = pdfPage.getViewport({ scale: cssScale * (window.devicePixelRatio || 1) });
				target.width = Math.floor(viewport.width);
				target.height = Math.floor(viewport.height);
				target.style.width = `${Math.floor(base.width * cssScale)}px`;
				target.style.height = `${Math.floor(base.height * cssScale)}px`;
				renderTask = pdfPage.render({ canvas: target, viewport });
				await renderTask.promise;
				if (!cancelled) status = 'ready';
			} catch (e) {
				// A superseded render is cancelled on purpose and is not an error.
				if (cancelled || (e instanceof Error && e.name === 'RenderingCancelledException')) return;
				errorMessage = e instanceof Error ? e.message : 'The page could not be rendered.';
				status = 'error';
			}
		})();

		return () => {
			cancelled = true;
			renderTask?.cancel();
		};
	});

	function onKeydown(event: KeyboardEvent) {
		if (event.target instanceof HTMLInputElement) return;
		if (event.key === '+' || event.key === '=') setZoom(zoom * ZOOM_STEP);
		else if (event.key === '-') setZoom(zoom / ZOOM_STEP);
		else if (event.key === '0') setZoom(1);
		else if (isPdf && event.key === 'ArrowRight') goToPage(page + 1);
		else if (isPdf && event.key === 'ArrowLeft') goToPage(page - 1);
		else return;
		event.preventDefault();
	}
</script>

<div
	class="flex h-full min-h-0 flex-col overflow-hidden card border border-surface-200-800 bg-surface-50-950 {className}"
>
	<div
		class="flex flex-wrap items-center gap-2 border-b border-surface-200-800 px-3 py-2 text-sm"
		role="toolbar"
		aria-label="Document controls"
	>
		<span class="min-w-0 flex-1 truncate font-medium" title={doc.name}>{doc.name}</span>

		{#if supported}
			{#if isPdf && pageCount > 1}
				<div class="flex items-center gap-1">
					<button
						type="button"
						class="btn-icon size-8 hover:preset-tonal"
						aria-label="Previous page"
						disabled={page <= 1}
						onclick={() => goToPage(page - 1)}
					>
						<ChevronLeftIcon class="size-4" />
					</button>
					<span class="min-w-14 text-center tabular-nums" aria-live="polite">
						{page} / {pageCount}
					</span>
					<button
						type="button"
						class="btn-icon size-8 hover:preset-tonal"
						aria-label="Next page"
						disabled={page >= pageCount}
						onclick={() => goToPage(page + 1)}
					>
						<ChevronRightIcon class="size-4" />
					</button>
				</div>
			{/if}

			<div class="flex items-center gap-1">
				<button
					type="button"
					class="btn-icon size-8 hover:preset-tonal"
					aria-label="Zoom out"
					disabled={zoom <= MIN_ZOOM}
					onclick={() => setZoom(zoom / ZOOM_STEP)}
				>
					<ZoomOutIcon class="size-4" />
				</button>
				<span class="min-w-12 text-center tabular-nums">{Math.round(zoom * 100)} %</span>
				<button
					type="button"
					class="btn-icon size-8 hover:preset-tonal"
					aria-label="Zoom in"
					disabled={zoom >= MAX_ZOOM}
					onclick={() => setZoom(zoom * ZOOM_STEP)}
				>
					<ZoomInIcon class="size-4" />
				</button>
				<button
					type="button"
					class="btn-icon size-8 hover:preset-tonal"
					aria-label="Fit to width"
					onclick={() => setZoom(1)}
				>
					<MaximizeIcon class="size-4" />
				</button>
			</div>

			<!-- eslint-disable svelte/no-navigation-without-resolve -- url comes from the API -->
			<a
				href="{doc.url}?download=1"
				class="btn-icon size-8 hover:preset-tonal"
				aria-label="Download"
				title="Download"
			>
				<DownloadIcon class="size-4" />
			</a>
			<!-- eslint-enable svelte/no-navigation-without-resolve -->
		{/if}
	</div>

	<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
	<div
		bind:this={scroller}
		bind:clientWidth={containerWidth}
		class="relative min-h-0 flex-1 overflow-auto bg-surface-100-900 outline-none"
		tabindex="0"
		role="region"
		aria-label="Document content"
		onkeydown={onKeydown}
	>
		{#if !doc.url}
			<div class="flex h-full flex-col items-center justify-center gap-2 p-6 opacity-60">
				<FileQuestionMarkIcon class="size-10" />
				<p>No file is stored for this document.</p>
			</div>
		{:else if !supported}
			<div class="flex h-full flex-col items-center justify-center gap-2 p-6 opacity-60">
				<FileQuestionMarkIcon class="size-10" />
				<p>This file type cannot be previewed.</p>
				<!-- eslint-disable svelte/no-navigation-without-resolve -- url comes from the API -->
				<a href="{doc.url}?download=1" class="btn preset-tonal btn-sm">Download</a>
				<!-- eslint-enable svelte/no-navigation-without-resolve -->
			</div>
		{:else}
			{#if status === 'error'}
				<div class="p-4">
					<Alert type="error" title="Could not show document" message={errorMessage} />
				</div>
			{:else if status === 'loading'}
				<p class="absolute inset-0 grid place-items-center text-sm opacity-60">Loading…</p>
			{/if}

			{#if isPdf}
				<canvas
					bind:this={canvas}
					class="mx-auto block bg-white shadow {status === 'error' ? 'hidden' : ''}"
					aria-label="Page {page} of {doc.name}"
				></canvas>
			{:else}
				<!-- eslint-disable svelte/no-navigation-without-resolve -- url comes from the API -->
				<img
					src={doc.url}
					alt={doc.name}
					class="mx-auto block max-w-none bg-white shadow {status === 'error' ? 'hidden' : ''}"
					style:width="{zoom * 100}%"
					onload={() => (status = 'ready')}
					onerror={() => {
						errorMessage = 'The image could not be loaded.';
						status = 'error';
					}}
				/>
				<!-- eslint-enable svelte/no-navigation-without-resolve -->
			{/if}
		{/if}
	</div>
</div>
