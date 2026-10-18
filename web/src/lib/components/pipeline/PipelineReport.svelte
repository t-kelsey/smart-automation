<script lang="ts">
	import { Collapsible } from '@skeletonlabs/skeleton-svelte';
	import { ChevronDownIcon } from '@lucide/svelte';
	import { formatDuration, type PipelineReportStep } from '#lib/domain/pipelines.ts';

	/** The run's report: time, model calls, tokens and cost per step, with totals. */
	let { steps }: { steps: PipelineReportStep[] } = $props();

	// The totals are always shown; the per-step table only on request.
	let detailsOpen = $state(false);

	const integer = new Intl.NumberFormat('en');
	const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
	const usd = new Intl.NumberFormat('en', {
		style: 'currency',
		currency: 'USD',
		minimumFractionDigits: 2,
		maximumFractionDigits: 4
	});

	/** Sum of a field over all steps; unset if no step reports it. */
	function total(field: keyof PipelineReportStep): number | undefined {
		const values = steps.map((s) => s[field]).filter((v): v is number => typeof v === 'number');
		return values.length > 0 ? values.reduce((a, b) => a + b, 0) : undefined;
	}

	const num = (v: number | undefined) => (v === undefined ? '–' : integer.format(v));
	const cost = (v: number | undefined) => (v === undefined ? '–' : usd.format(v));
	const time = (v: number | undefined) => (v === undefined ? '–' : formatDuration(v));

	let totals = $derived({
		wallSeconds: total('wallSeconds'),
		calls: total('calls'),
		inputTokens: total('inputTokens'),
		outputTokens: total('outputTokens'),
		cacheReadTokens: total('cacheReadTokens'),
		cacheCreateTokens: total('cacheCreateTokens'),
		totalTokens: total('totalTokens'),
		costUsd: total('costUsd')
	});

	let tiles = $derived([
		{ label: 'Cost', value: cost(totals.costUsd) },
		{
			label: 'Tokens',
			value: totals.totalTokens === undefined ? '–' : compact.format(totals.totalTokens)
		},
		{ label: 'Total time', value: time(totals.wallSeconds) },
		{ label: 'Model calls', value: num(totals.calls) }
	]);
</script>

<section class="space-y-4" aria-labelledby="report-heading">
	<header>
		<h2 id="report-heading" class="h4">Report</h2>
		<p class="text-xs opacity-70">
			Usage of the model calls, as reported by the pipeline. The total time is the sum of the step
			times.
		</p>
	</header>

	<dl class="grid grid-cols-2 gap-3 sm:grid-cols-4">
		{#each tiles as tile (tile.label)}
			<div class="rounded-2xl bg-surface-100-900 px-4 py-3">
				<dt class="text-xs opacity-70">{tile.label}</dt>
				<dd class="text-xl font-bold tabular-nums">{tile.value}</dd>
			</div>
		{/each}
	</dl>

	<Collapsible
		open={detailsOpen}
		onOpenChange={(details) => (detailsOpen = details.open)}
		class="items-stretch! card border border-surface-200-800 bg-surface-50-950 p-4"
	>
		<Collapsible.Trigger class="flex items-center gap-2 text-left">
			<h3 class="h5">Steps</h3>
			<ChevronDownIcon
				class="size-4 shrink-0 transition-transform {detailsOpen ? '' : '-rotate-90'}"
			/>
		</Collapsible.Trigger>
		<Collapsible.Content>
			<div class="mt-3 table-wrap">
				<table class="table">
					<thead>
						<tr>
							<th>Step</th>
							<th>Model</th>
							<th class="text-right">Time</th>
							<th class="text-right">Calls</th>
							<th class="text-right">Input</th>
							<th class="text-right">Output</th>
							<th class="text-right">Cache read</th>
							<th class="text-right">Cache write</th>
							<th class="text-right">Total tokens</th>
							<th class="text-right">Cost</th>
						</tr>
					</thead>
					<tbody class="tabular-nums">
						{#each steps as step, i (step.label + i)}
							<tr>
								<td class="font-medium">{step.label}</td>
								<td>
									{step.model ?? '–'}{#if step.effort}<span class="opacity-60">
											· {step.effort}</span
										>{/if}
								</td>
								<td class="text-right">{time(step.wallSeconds)}</td>
								<td class="text-right">{num(step.calls)}</td>
								<td class="text-right">{num(step.inputTokens)}</td>
								<td class="text-right">{num(step.outputTokens)}</td>
								<td class="text-right">{num(step.cacheReadTokens)}</td>
								<td class="text-right">{num(step.cacheCreateTokens)}</td>
								<td class="text-right">{num(step.totalTokens)}</td>
								<td class="text-right">{cost(step.costUsd)}</td>
							</tr>
						{/each}
					</tbody>
					<tfoot class="tabular-nums">
						<tr class="font-bold">
							<td>Total</td>
							<td></td>
							<td class="text-right">{time(totals.wallSeconds)}</td>
							<td class="text-right">{num(totals.calls)}</td>
							<td class="text-right">{num(totals.inputTokens)}</td>
							<td class="text-right">{num(totals.outputTokens)}</td>
							<td class="text-right">{num(totals.cacheReadTokens)}</td>
							<td class="text-right">{num(totals.cacheCreateTokens)}</td>
							<td class="text-right">{num(totals.totalTokens)}</td>
							<td class="text-right">{cost(totals.costUsd)}</td>
						</tr>
					</tfoot>
				</table>
			</div>
		</Collapsible.Content>
	</Collapsible>
</section>
