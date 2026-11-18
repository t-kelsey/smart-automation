<!--
@component
Viewer for a single document (PDF or image) with a toolbar for zoom, page navigation and download.
Fills the height of its parent, so give the parent a height. State is local, so several viewers
can sit side by side (e.g. for comparing documents).

A PDF page is drawn once at high resolution; zooming and panning are CSS transforms, so they are
smooth. A highlighted box is zoomed to (it fills about 60 % of the viewer width), the rest of the
page is dimmed; without a box the page is fitted to the width again. The wheel pans (Ctrl+wheel
zooms), the page can be dragged.

@param document - Document to show; needs `name`, `type` and `url` (the file link).
@param [highlight] - Page to show and a box to zoom to (normalised 0–1, origin top left).
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
	import { untrack } from 'svelte';
	import type { Attachment } from 'svelte/attachments';
	import type { SourceRef, StoredDocument } from '#lib/domain/borehole.ts';
	import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from 'pdfjs-dist';

	type Box = [number, number, number, number];

	interface Props {
		document: Pick<StoredDocument, 'name' | 'type' | 'url'>;
		highlight?: Pick<SourceRef, 'page' | 'box'> | null;
		class?: string;
	}

	let { document: doc, highlight = null, class: className = '' }: Props = $props();

	const MIN_ZOOM = 0.5;
	const MAX_ZOOM = 6;
	const ZOOM_STEP = 1.25;
	/** A highlighted box fills this share of the viewer (width, or height if that is tighter). */
	const BOX_FILL = 0.6;
	const MAX_BOX_ZOOM = 4;
	/** Zoom of a double click into the page. */
	const DOUBLE_CLICK_ZOOM = 2.5;
	/** The page is drawn at this many device pixels per fitted pixel, up to `MAX_PIXELS` in all. */
	const OVERSAMPLE = 2.5;
	const MAX_PIXELS = 12_000_000;
	/** Space left and right of the fitted page. */
	const PAD = 12;

	let page = $state(1);
	let pageCount = $state(1);
	/** Page shown in the canvas once it is drawn; a box is only drawn on its own page. */
	let drawnPage = $state(0);
	/** Height / width of the shown page. */
	let aspect = $state(Math.SQRT2);
	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let errorMessage = $state('');

	let canvas = $state<HTMLCanvasElement>();
	let viewW = $state(0);
	let viewH = $state(0);

	/** Zoom (1 = page fits the width) and the page point (0–1) in the middle of the viewer. */
	let view = $state({ zoom: 1, cx: 0.5, cy: 0 });
	/** Whether the next change of the view is animated (not while dragging or scrolling). */
	let animate = $state(false);
	let dragging = $state(false);

	let pdf = $state.raw<PDFDocumentProxy | null>(null);

	let supported = $derived(!!doc.url && (doc.type === 'pdf' || doc.type === 'image'));
	let isPdf = $derived(doc.type === 'pdf');

	let pageW = $derived(Math.max(1, viewW - 2 * PAD));
	let measured = $derived(viewW > 0);
	let pageH = $derived(pageW * aspect);

	const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

	/** Keeps the page in the viewer: centred where it is smaller, no empty margin where it is larger. */
	function clampView({ zoom, cx, cy }: typeof view): typeof view {
		zoom = clamp(zoom, MIN_ZOOM, MAX_ZOOM);
		const axis = (c: number, size: number, viewSize: number) => {
			const content = size * zoom;
			if (content <= viewSize) return 0.5;
			const margin = viewSize / 2 / content;
			return clamp(c, margin, 1 - margin);
		};
		return { zoom, cx: axis(cx, pageW, viewW), cy: axis(cy, pageH, viewH) };
	}

	// Clamped again on every resize, so that the view stays valid while the pane is resized.
	let shown = $derived(clampView(view));
	let tx = $derived(viewW / 2 - shown.cx * pageW * shown.zoom);
	let ty = $derived(viewH / 2 - shown.cy * pageH * shown.zoom);

	function setView(next: typeof view, smooth: boolean) {
		animate = smooth;
		view = clampView(next);
	}

	const fit = (smooth = true) => setView({ zoom: 1, cx: 0.5, cy: 0 }, smooth);

	function zoomToBox([x0, y0, x1, y1]: Box) {
		const zoom = Math.min(
			(BOX_FILL * viewW) / Math.max((x1 - x0) * pageW, 1),
			(BOX_FILL * viewH) / Math.max((y1 - y0) * pageH, 1)
		);
		setView({ zoom: clamp(zoom, 1, MAX_BOX_ZOOM), cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 }, true);
	}

	/** Zooms by `factor`, keeping the page point under `at` (viewer pixels) in place. */
	function zoomBy(factor: number, at?: { x: number; y: number }, smooth = false) {
		const zoom = clamp(shown.zoom * factor, MIN_ZOOM, MAX_ZOOM);
		if (!at) return setView({ ...shown, zoom }, true);
		const px = (at.x - tx) / (pageW * shown.zoom);
		const py = (at.y - ty) / (pageH * shown.zoom);
		setView(
			{
				zoom,
				cx: px - (at.x - viewW / 2) / (pageW * zoom),
				cy: py - (at.y - viewH / 2) / (pageH * zoom)
			},
			smooth
		);
	}

	/** Double click: zoom in on the clicked spot, or back out to the whole page if zoomed in. */
	function ondblclick(event: MouseEvent & { currentTarget: HTMLElement }) {
		if (shown.zoom > 1.2) return fit();
		const rect = event.currentTarget.getBoundingClientRect();
		zoomBy(
			DOUBLE_CLICK_ZOOM / shown.zoom,
			{ x: event.clientX - rect.left, y: event.clientY - rect.top },
			true
		);
	}

	function panBy(dx: number, dy: number) {
		setView(
			{
				...shown,
				cx: shown.cx + dx / (pageW * shown.zoom),
				cy: shown.cy + dy / (pageH * shown.zoom)
			},
			false
		);
	}

	function goToPage(value: number) {
		page = clamp(value, 1, pageCount);
		fit(false);
	}

	// Primitives, so that an equal document object (e.g. after a reload of the borehole) keeps the view.
	let url = $derived(doc.url);
	let type = $derived(doc.type);

	// Reset view state and (re)load whenever another document is shown.
	$effect(() => {
		page = untrack(() => highlight?.page ?? 1);
		pageCount = 1;
		drawnPage = 0;
		pdf = null;
		errorMessage = '';
		status = 'loading';
		untrack(() => fit(false));
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
				page = Math.min(page, pageCount);
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

	// Resolution step of the fitted width (every factor √2), so that the page is drawn again only
	// when the viewer grows or shrinks noticeably, not on every pixel of a resize.
	let sharpness = $derived(Math.ceil(Math.log2(pageW) * 2));

	// Draw the current page off screen at high resolution, then show it in one go: the previous page
	// stays visible (and its box hidden) until the new one is ready.
	$effect(() => {
		if (!pdf || !canvas || !measured) return;
		const target = canvas;
		const source = pdf;
		const pageNumber = page;
		const fittedPixels = 2 ** (sharpness / 2) * (window.devicePixelRatio || 1) * OVERSAMPLE;

		let renderTask: RenderTask | undefined;
		let cancelled = false;
		(async () => {
			try {
				const pdfPage = await source.getPage(pageNumber);
				if (cancelled) return;
				const base = pdfPage.getViewport({ scale: 1 });
				const width = Math.min(fittedPixels, Math.sqrt((MAX_PIXELS * base.width) / base.height));
				const viewport = pdfPage.getViewport({ scale: width / base.width });
				const offscreen = document.createElement('canvas');
				offscreen.width = Math.floor(viewport.width);
				offscreen.height = Math.floor(viewport.height);
				renderTask = pdfPage.render({ canvas: offscreen, viewport });
				await renderTask.promise;
				if (cancelled) return;
				target.width = offscreen.width;
				target.height = offscreen.height;
				target.getContext('2d')?.drawImage(offscreen, 0, 0);
				aspect = base.height / base.width;
				drawnPage = pageNumber;
				status = 'ready';
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

	// Turn to the highlighted page (clamped once the page count is known) …
	$effect(() => {
		if (highlight && isPdf) page = clamp(highlight.page, 1, pdf ? pageCount : Infinity);
	});

	// … and zoom to its box once that page is drawn; without a highlight show the whole width.
	let target = $derived(
		highlight && drawnPage && (!isPdf || highlight.page === drawnPage) ? highlight : null
	);
	let box = $derived(target?.box ?? null);
	let targetKey = $derived(
		highlight ? (target ? `${target.page}:${target.box}` : 'pending') : 'none'
	);
	$effect(() => {
		if (targetKey === 'pending' || !measured) return;
		untrack(() => (box ? zoomToBox(box) : fit()));
	});

	function onKeydown(event: KeyboardEvent) {
		if (event.target instanceof HTMLInputElement) return;
		if (event.key === '+' || event.key === '=') zoomBy(ZOOM_STEP);
		else if (event.key === '-') zoomBy(1 / ZOOM_STEP);
		else if (event.key === '0') fit();
		else if (event.key === 'ArrowUp') panBy(0, -80);
		else if (event.key === 'ArrowDown') panBy(0, 80);
		else if (isPdf && event.key === 'ArrowRight') goToPage(page + 1);
		else if (isPdf && event.key === 'ArrowLeft') goToPage(page - 1);
		else return;
		event.preventDefault();
	}

	// Not passive, so that the wheel moves the page instead of scrolling anything around it.
	const wheel: Attachment<HTMLElement> = (element) => {
		const onwheel = (event: WheelEvent) => {
			event.preventDefault();
			const unit = event.deltaMode === 1 ? 16 : 1;
			if (event.ctrlKey) {
				const rect = element.getBoundingClientRect();
				zoomBy(Math.exp(-event.deltaY * unit * 0.002), {
					x: event.clientX - rect.left,
					y: event.clientY - rect.top
				});
			} else if (event.shiftKey) panBy(event.deltaY * unit, 0);
			else panBy(event.deltaX * unit, event.deltaY * unit);
		};
		element.addEventListener('wheel', onwheel, { passive: false });
		return () => element.removeEventListener('wheel', onwheel);
	};

	let last = { x: 0, y: 0 };

	function onpointerdown(event: PointerEvent & { currentTarget: HTMLElement }) {
		if (event.button !== 0) return;
		dragging = true;
		last = { x: event.clientX, y: event.clientY };
		event.currentTarget.setPointerCapture(event.pointerId);
	}

	function onpointermove(event: PointerEvent) {
		if (!dragging) return;
		panBy(last.x - event.clientX, last.y - event.clientY);
		last = { x: event.clientX, y: event.clientY };
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
					disabled={shown.zoom <= MIN_ZOOM}
					onclick={() => zoomBy(1 / ZOOM_STEP)}
				>
					<ZoomOutIcon class="size-4" />
				</button>
				<span class="min-w-12 text-center tabular-nums">{Math.round(shown.zoom * 100)} %</span>
				<button
					type="button"
					class="btn-icon size-8 hover:preset-tonal"
					aria-label="Zoom in"
					disabled={shown.zoom >= MAX_ZOOM}
					onclick={() => zoomBy(ZOOM_STEP)}
				>
					<ZoomInIcon class="size-4" />
				</button>
				<button
					type="button"
					class="btn-icon size-8 hover:preset-tonal"
					aria-label="Fit to width"
					onclick={() => fit()}
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
		bind:clientWidth={viewW}
		bind:clientHeight={viewH}
		{@attach wheel}
		class="relative min-h-0 flex-1 touch-none overflow-hidden bg-surface-100-900 outline-none {supported
			? dragging
				? 'cursor-grabbing'
				: 'cursor-grab'
			: ''}"
		tabindex="0"
		role="region"
		aria-label="Document content"
		onkeydown={onKeydown}
		{onpointerdown}
		{onpointermove}
		onpointerup={() => (dragging = false)}
		{ondblclick}
		onpointercancel={() => (dragging = false)}
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

			<!-- The page, moved and scaled as a whole, and on top the box of the highlighted value. -->
			<div
				class="absolute top-0 left-0 origin-top-left will-change-transform {animate
					? 'transition-transform duration-300 ease-in-out motion-reduce:transition-none'
					: ''} {status === 'error' ? 'hidden' : ''}"
				style:width="{pageW}px"
				style:height="{pageH}px"
				style:transform="translate({tx}px, {ty}px) scale({shown.zoom})"
				ontransitionend={(event) => {
					if (event.target === event.currentTarget) animate = false;
				}}
			>
				{#if isPdf}
					<canvas
						bind:this={canvas}
						class="block size-full bg-white shadow"
						aria-label="Page {page} of {doc.name}"
					></canvas>
				{:else}
					<!-- eslint-disable svelte/no-navigation-without-resolve -- url comes from the API -->
					<img
						src={doc.url}
						alt={doc.name}
						draggable="false"
						class="block size-full max-w-none bg-white shadow"
						onload={(event) => {
							const image = event.currentTarget as HTMLImageElement;
							aspect = image.naturalHeight / image.naturalWidth;
							drawnPage = 1;
							status = 'ready';
						}}
						onerror={() => {
							errorMessage = 'The image could not be loaded.';
							status = 'error';
						}}
					/>
					<!-- eslint-enable svelte/no-navigation-without-resolve -->
				{/if}
				{#if box}
					<!-- Spotlight: the page around the box is dimmed by the box's huge shadow. -->
					<div
						class="pointer-events-none absolute rounded-sm border-primary-500 shadow-[0_0_0_200vmax_rgb(0_0_0/0.35)] transition-[left,top,width,height] duration-300 ease-in-out motion-reduce:transition-none"
						style:left="{box[0] * 100}%"
						style:top="{box[1] * 100}%"
						style:width="{(box[2] - box[0]) * 100}%"
						style:height="{(box[3] - box[1]) * 100}%"
						style:border-width="{2 / shown.zoom}px"
					></div>
				{/if}
			</div>
		{/if}
	</div>
</div>
