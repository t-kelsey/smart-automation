<!--
	Section (side view) along a line drawn on the map (ADR-0004): every borehole within the corridor
	at its distance along the line, all aligned at their start (depth 0), drawn as DIN 4023 columns.
	Between neighbours the predicted layers (correlation.ts) are drawn lighter with dashed outlines.
	Horizontal and vertical scales fill the available space independently; the resulting vertical
	exaggeration is shown. Columns that would overlap are pushed apart; a leader line keeps their
	true position on the distance axis.
-->
<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { ArrowLeftIcon, SparklesIcon } from '@lucide/svelte';
	import { columnHeight, columnSegments } from '#lib/borehole-columns/column-model.ts';
	import type { ColumnSegment } from '#lib/borehole-columns/column-model.ts';
	import { correlateSection } from '#lib/borehole-columns/correlation.ts';
	import type { Band } from '#lib/borehole-columns/correlation.ts';
	import {
		CORRIDOR_M,
		buildSection,
		sectionBBox,
		type Section,
		type SectionBorehole,
		type SectionLine
	} from '#lib/borehole-columns/section.ts';
	import { patternId } from '#lib/din4023/index.ts';
	import { createServices } from '#lib/services/index.ts';
	import { notify } from '#lib/components/toast/index.ts';
	import LayerFill from '#lib/components/borehole/LayerFill.svelte';
	import PatternDefs from '#lib/components/borehole/PatternDefs.svelte';

	interface Props {
		line: SectionLine;
		/** Back to the map. */
		onClose: () => void;
	}

	let { line, onClose }: Props = $props();

	/** Column width and the smallest gap between two columns, in pixels. */
	const COLUMN_WIDTH = 60;
	const MIN_GAP = 12;
	const margin = { top: 16, right: 24, bottom: 44, left: 64 };

	let section = $state<Section | undefined>();
	let loading = $state(true);
	let showPrediction = $state(true);
	let width = $state(0);
	let height = $state(0);

	// Load the boreholes around the line whenever it changes.
	$effect(() => {
		const current = line;
		let cancelled = false;
		loading = true;
		createServices({ fetch })
			.then(({ boreholes }) => boreholes.listColumns(sectionBBox(current)))
			.then((columns) => {
				if (!cancelled) section = buildSection(current, columns);
			})
			.catch((error) => notify.fromError(error, 'Could not load the section'))
			.finally(() => {
				if (!cancelled) loading = false;
			});
		return () => {
			cancelled = true;
		};
	});

	let correlations = $derived(section ? correlateSection(section.boreholes) : []);

	/** A round step for axis ticks: about `count` ticks over `range`. */
	function niceStep(range: number, count: number): number {
		const raw = range / Math.max(count, 1);
		const power = 10 ** Math.floor(Math.log10(raw || 1));
		return [1, 2, 5, 10].map((m) => m * power).find((step) => step >= raw) ?? 10 * power;
	}

	/** Pushes sorted centres apart to at least `gap`, within `[min, max]`. */
	function spread(xs: number[], gap: number, min: number, max: number): number[] {
		const available = max - min;
		const step = xs.length > 1 ? Math.min(gap, available / (xs.length - 1)) : gap;
		const out = [...xs];
		for (let i = 1; i < out.length; i++) out[i] = Math.max(out[i], out[i - 1] + step);
		const last = out.length - 1;
		if (last >= 0 && out[last] > max) {
			out[last] = max;
			for (let i = last - 1; i >= 0; i--) out[i] = Math.min(out[i], out[i + 1] - step);
		}
		return out.map((x) => Math.max(min, x));
	}

	let layout = $derived.by(() => {
		if (!section || width === 0 || height === 0) return undefined;
		const plotWidth = Math.max(width - margin.left - margin.right, COLUMN_WIDTH);
		const plotHeight = Math.max(height - margin.top - margin.bottom, 40);
		const maxDepth = Math.max(1, ...section.boreholes.map((b) => columnHeight(b.column)));
		const vertical = plotHeight / maxDepth; // px per metre of depth
		const usable = plotWidth - COLUMN_WIDTH;
		const horizontal = section.length > 0 ? usable / section.length : 0; // px per metre along
		const firstCentre = margin.left + COLUMN_WIDTH / 2;
		const trueX = section.boreholes.map((b) => firstCentre + b.along * horizontal);
		const centres = spread(trueX, COLUMN_WIDTH + MIN_GAP, firstCentre, firstCentre + usable);
		return {
			plotWidth,
			plotHeight,
			maxDepth,
			vertical,
			horizontal,
			exaggeration: horizontal > 0 ? vertical / horizontal : undefined,
			trueX,
			centres,
			y: (depth: number) => margin.top + depth * vertical,
			depthStep: niceStep(maxDepth, plotHeight / 60),
			distanceStep: niceStep(section.length || 1, plotWidth / 110)
		};
	});

	const range = (to: number, step: number) =>
		Array.from({ length: Math.floor(to / step + 1e-9) + 1 }, (_, i) => i * step);

	/** A band's outline in pixels: `t` runs from the left column's right edge to the right one's left edge. */
	function bandPoints(band: Band, leftCentre: number, rightCentre: number): string | undefined {
		if (!layout) return undefined;
		const x0 = leftCentre + COLUMN_WIDTH / 2;
		const x1 = rightCentre - COLUMN_WIDTH / 2;
		if (x1 <= x0) return undefined;
		const { y } = layout;
		return band.polygon.map(([t, depth]) => `${x0 + t * (x1 - x0)},${y(depth)}`).join(' ');
	}

	const formatExaggeration = (value: number) =>
		value >= 10 ? `${Math.round(value)}×` : `${Number(value.toFixed(1))}×`;
	const metres = (value: number) => `${Number(value.toFixed(2))} m`;

	// --- hover card
	type Hover =
		| { kind: 'layer'; borehole: SectionBorehole; segment: ColumnSegment }
		| { kind: 'band'; band: Band; left: SectionBorehole; right: SectionBorehole };
	let hover = $state<{ x: number; y: number; item: Hover } | undefined>();
	let container = $state<HTMLDivElement>();

	function track(event: PointerEvent, item: Hover) {
		const box = container?.getBoundingClientRect();
		if (!box) return;
		hover = { x: event.clientX - box.left, y: event.clientY - box.top, item };
	}

	const boreholeName = (b: SectionBorehole) => b.column.name;
	const openBorehole = (b: SectionBorehole) => goto(resolve('/borehole/[id]', { id: b.column.id }));
</script>

<PatternDefs />

<div class="flex h-full flex-col gap-3">
	<header class="flex flex-wrap items-center gap-3">
		<button type="button" class="btn preset-tonal btn-sm" onclick={onClose}>
			<ArrowLeftIcon class="size-4" /> Map
		</button>
		<h1 class="h5">Section</h1>
		{#if section}
			<span class="text-sm opacity-70">
				{Math.round(section.length)} m · {section.boreholes.length}
				{section.boreholes.length === 1 ? 'borehole' : 'boreholes'} within {CORRIDOR_M} m
				{#if layout?.exaggeration}· {formatExaggeration(layout.exaggeration)} vertical{/if}
			</span>
		{/if}
		<button
			type="button"
			class="ml-auto btn btn-sm {showPrediction
				? 'preset-filled-primary-500'
				: 'preset-filled-surface-50-950'}"
			aria-pressed={showPrediction}
			onclick={() => (showPrediction = !showPrediction)}
		>
			<SparklesIcon class="size-4" />
			Prediction: {showPrediction ? 'on' : 'off'}
		</button>
	</header>

	<div
		bind:this={container}
		bind:clientWidth={width}
		bind:clientHeight={height}
		class="relative min-h-0 flex-1 overflow-hidden card bg-surface-50-950"
	>
		{#if loading && !section}
			<p class="p-6 text-sm opacity-70">Loading boreholes along the line…</p>
		{:else if section && section.boreholes.length === 0}
			<p class="p-6 text-sm opacity-70">No boreholes within {CORRIDOR_M} m of the line.</p>
		{:else if section && layout}
			{@const { y, centres, trueX } = layout}
			<svg
				{width}
				{height}
				class="block"
				role="img"
				aria-label="Section along the drawn line"
				font-family="inherit"
			>
				<!-- depth axis: depth below each borehole's start -->
				<g class="text-surface-500" font-size="11" fill="currentColor">
					{#each range(layout.maxDepth, layout.depthStep) as depth (depth)}
						<line
							x1={margin.left - 6}
							x2={margin.left + layout.plotWidth}
							y1={y(depth)}
							y2={y(depth)}
							stroke="currentColor"
							stroke-opacity="0.18"
						/>
						<text x={margin.left - 10} y={y(depth)} text-anchor="end" dominant-baseline="middle">
							{depth} m
						</text>
					{/each}
				</g>

				<!-- predicted layers between neighbouring columns -->
				{#if showPrediction}
					{#each correlations as pair, k (pair.left.column.id + pair.right.column.id)}
						{#each pair.bands as band, b (b)}
							{@const points = bandPoints(band, centres[k], centres[k + 1])}
							{@const segment = band.left ?? band.right}
							{#if points && segment}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<g
									opacity="0.45"
									onpointermove={(event) =>
										track(event, { kind: 'band', band, left: pair.left, right: pair.right })}
									onpointerleave={() => (hover = undefined)}
								>
									<polygon {points} fill="white" />
									<polygon {points} fill={segment.color} fill-opacity="0.5" />
									{#if segment.material}
										<polygon {points} fill="url(#{patternId(segment.material, 'a')})" />
									{/if}
								</g>
								<polygon
									{points}
									fill="none"
									stroke="currentColor"
									stroke-opacity="0.55"
									stroke-width="0.8"
									stroke-dasharray="4 3"
									pointer-events="none"
								/>
							{/if}
						{/each}
					{/each}
				{/if}

				<!-- the boreholes -->
				{#each section.boreholes as borehole, i (borehole.column.id)}
					{@const x = centres[i] - COLUMN_WIDTH / 2}
					{@const segments = columnSegments(borehole.column)}
					{@const bottom = y(columnHeight(borehole.column))}
					<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
					<g class="cursor-pointer" onclick={() => openBorehole(borehole)}>
						{#each borehole.column.layers as layer (layer.id)}
							{@const segment = segments.find((s) => s.layerId === layer.id)}
							{#if segment}
								<g
									onpointermove={(event) => track(event, { kind: 'layer', borehole, segment })}
									onpointerleave={() => (hover = undefined)}
								>
									<LayerFill
										{x}
										y={y(layer.startDepth)}
										width={COLUMN_WIDTH}
										height={y(layer.endDepth) - y(layer.startDepth)}
										composition={layer.petrography.composition}
									/>
									{#if hover?.item.kind === 'layer' && hover.item.segment.layerId === layer.id}
										<rect
											{x}
											y={y(layer.startDepth)}
											width={COLUMN_WIDTH}
											height={y(layer.endDepth) - y(layer.startDepth)}
											class="fill-primary-500/20 stroke-primary-500"
											stroke-width="2"
										/>
									{/if}
								</g>
							{/if}
						{/each}
						<g stroke="currentColor" stroke-width="0.9" fill="none" pointer-events="none">
							<line x1={x} x2={x} y1={y(0)} y2={bottom} />
							<line x1={x + COLUMN_WIDTH} x2={x + COLUMN_WIDTH} y1={y(0)} y2={bottom} />
							{#each segments as segment (segment.layerId)}
								<line x1={x} x2={x + COLUMN_WIDTH} y1={y(segment.bottom)} y2={y(segment.bottom)} />
							{/each}
							<line x1={x - 4} x2={x + COLUMN_WIDTH + 4} y1={y(0)} y2={y(0)} stroke-width="1.6" />
							<line
								x1={x - 4}
								x2={x + COLUMN_WIDTH + 4}
								y1={bottom}
								y2={bottom}
								stroke-width="1.6"
							/>
						</g>
					</g>
					<!-- true position on the distance axis, with a leader if the column was pushed aside -->
					<g class="text-surface-500" stroke="currentColor" pointer-events="none">
						<line
							x1={trueX[i]}
							x2={trueX[i]}
							y1={margin.top + layout.plotHeight + 2}
							y2={margin.top + layout.plotHeight + 10}
							stroke-width="1.5"
						/>
						{#if Math.abs(trueX[i] - centres[i]) > 0.5}
							<line
								x1={centres[i]}
								x2={trueX[i]}
								y1={bottom + 2}
								y2={margin.top + layout.plotHeight + 2}
								stroke-dasharray="2 2"
							/>
						{/if}
					</g>
				{/each}

				<!-- distance along the line -->
				<g class="text-surface-500" font-size="11" fill="currentColor">
					<line
						x1={margin.left + COLUMN_WIDTH / 2}
						x2={margin.left + COLUMN_WIDTH / 2 + layout.horizontal * section.length}
						y1={margin.top + layout.plotHeight + 6}
						y2={margin.top + layout.plotHeight + 6}
						stroke="currentColor"
					/>
					{#each range(section.length, layout.distanceStep) as distance (distance)}
						<text
							x={margin.left + COLUMN_WIDTH / 2 + distance * layout.horizontal}
							y={margin.top + layout.plotHeight + 26}
							text-anchor="middle"
						>
							{distance} m
						</text>
					{/each}
				</g>
			</svg>

			{#if hover}
				{@const item = hover.item}
				<!-- Right of the pointer, so the rest of the column stays visible; flips left near the edge. -->
				<div
					role="tooltip"
					class="pointer-events-none absolute z-10 w-64 space-y-1 card bg-surface-50-950 p-3 text-sm shadow-xl"
					style:left="{hover.x > width - 280 ? hover.x - 272 : hover.x + 16}px"
					style:top="{Math.min(hover.y, height - 140)}px"
				>
					{#if item.kind === 'layer'}
						<p class="font-semibold">{boreholeName(item.borehole)}</p>
						<p class="text-xs opacity-60">
							{Math.round(item.borehole.along)} m along · {Math.round(item.borehole.offset)} m off the
							line · click to open
						</p>
						<p>
							<span class="font-medium">Layer {item.segment.position}</span>
							<span class="opacity-60"
								>· {metres(item.segment.top)}–{metres(item.segment.bottom)}</span
							>
						</p>
						<p>
							{item.segment.label}
							{#if item.segment.shortForm}<span class="opacity-60">({item.segment.shortForm})</span
								>{/if}
						</p>
						<p class="text-xs opacity-60">{item.segment.description}</p>
					{:else}
						{@const segment = item.band.left ?? item.band.right}
						<p class="font-semibold">Predicted: {segment?.label}</p>
						<p class="text-xs opacity-60">
							{#if item.band.kind === 'matched'}
								Connects {boreholeName(item.left)} and {boreholeName(item.right)}
							{:else}
								Only in {boreholeName(item.band.left ? item.left : item.right)}; pinches out halfway
							{/if}
						</p>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
</div>
