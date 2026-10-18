<script lang="ts">
	import { resolve } from '$app/paths';
	import { ArrowLeftIcon, MapPinIcon } from '@lucide/svelte';
	import { RefreshCwIcon } from '@lucide/svelte';
	import { retryJob } from '#lib/components/pipeline/retry.ts';
	import { PIPELINE_STAGES, canRetryJob } from '#lib/domain/pipelines.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let job = $derived(data.job);
	let pipeline = $derived(data.pipeline);
	let borehole = $derived(data.borehole);

	const formatter = new Intl.DateTimeFormat(undefined, {
		dateStyle: 'medium',
		timeStyle: 'medium'
	});
	let stageLabel = $derived(PIPELINE_STAGES.find((s) => s.key === job.type)?.label ?? job.type);
	/** The run's current job at this position; only the newest attempt of a job can be retried. */
	let runJob = $derived.by(() => {
		for (const stage of pipeline?.stages ?? []) {
			const found = stage.jobs.find((j) => j.execStageId === job.id);
			if (found) return { stage, job: found };
		}
		return null;
	});
	let title = $derived(job.position === undefined ? stageLabel : `${stageLabel} #${job.position}`);

	/** Top level attributes of the result, or the whole value if it is not an object. */
	let attributes = $derived.by(() => {
		const value = job.data;
		if (value === null || value === undefined) return [];
		if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
			return Object.entries(value as Record<string, unknown>);
		}
		return [['data', value]] as [string, unknown][];
	});

	function describe(value: unknown): string {
		if (Array.isArray(value)) return `array · ${value.length}`;
		if (value === null) return 'null';
		if (typeof value === 'object') return `object · ${Object.keys(value).length}`;
		return typeof value;
	}

	const isScalar = (value: unknown) => value === null || typeof value !== 'object';
	const pretty = (value: unknown) => JSON.stringify(value, null, 2);
</script>

<svelte:head>
	<title>Job {title}</title>
</svelte:head>

<a
	href={pipeline ? resolve('/pipeline/[id]', { id: pipeline.id }) : resolve('/pipeline')}
	class="mb-4 btn preset-tonal btn-sm"
>
	<ArrowLeftIcon class="size-4" />
	{pipeline ? pipeline.filename : 'All pipelines'}
</a>

<header class="mb-6 flex flex-wrap items-center gap-x-4 gap-y-2">
	<div>
		<h1 class="h2">{title}</h1>
		<p class="text-sm opacity-70">#{job.id.slice(-6)} · {formatter.format(job.createdAt)}</p>
	</div>
	{#if pipeline && runJob && canRetryJob(pipeline, runJob.stage, runJob.job)}
		<button
			type="button"
			class="ml-auto btn preset-tonal"
			onclick={() => retryJob(data.service, runJob.job)}
		>
			<RefreshCwIcon class="size-4" /> Retry
		</button>
	{/if}
	{#if borehole}
		<a href={resolve('/borehole/[id]', { id: borehole.id })} class="ml-auto btn preset-filled">
			<MapPinIcon class="size-4" /> Borehole {borehole.name}
		</a>
	{/if}
</header>

<section class="mb-8">
	<h2 class="mb-2 h4">Core data</h2>
	<div class="table-wrap">
		<table class="table">
			<tbody>
				<tr><th class="w-48">Job ID</th><td class="font-mono text-sm">{job.id}</td></tr>
				<tr><th>Stage</th><td>{stageLabel} <span class="opacity-60">({job.type})</span></td></tr>
				<tr><th>Borehole position</th><td>{job.position ?? '–'}</td></tr>
				<tr><th>Status</th><td>{job.status}</td></tr>
				{#if job.error}
					<tr><th>Error</th><td class="font-mono text-sm whitespace-pre-wrap">{job.error}</td></tr>
				{/if}
				<tr>
					<th>Model</th>
					<td>{job.model ?? '–'}{job.effort ? ` · ${job.effort}` : ''}</td>
				</tr>
				<tr>
					<th>Pipeline run</th>
					<td class="font-mono text-sm">
						{#if pipeline}
							<a href={resolve('/pipeline/[id]', { id: pipeline.id })} class="anchor">{job.runId}</a
							>
						{:else}
							{job.runId}
						{/if}
					</td>
				</tr>
				<tr>
					<th>Documents</th>
					<td class="font-mono text-sm">
						{#each job.documentIds as id (id)}
							<a href={resolve('/document/[id]', { id })} class="block anchor">{id}</a>
						{:else}
							–
						{/each}
					</td>
				</tr>
				<tr>
					<th>Started</th>
					<td>{job.startedAt ? formatter.format(job.startedAt) : '–'}</td>
				</tr>
				<tr>
					<th>Finished</th>
					<td>
						{job.finishedAt ? formatter.format(job.finishedAt) : '–'}
						{#if job.durationSeconds !== undefined}
							<span class="opacity-60">({job.durationSeconds.toFixed(1)} s)</span>
						{/if}
					</td>
				</tr>
				{#if job.usage}
					<tr>
						<th>Usage</th>
						<td class="text-sm">
							{job.usage.calls ?? '–'} calls · {job.usage.total_tokens ?? '–'} tokens · ${Number(
								job.usage.cost_usd ?? 0
							).toFixed(4)}
						</td>
					</tr>
				{/if}
			</tbody>
		</table>
	</div>
</section>

<section>
	<h2 class="mb-2 h4">Data</h2>
	{#each attributes as [key, value] (key)}
		<details class="mb-2 card preset-outlined-surface-300-700" open={isScalar(value)}>
			<summary class="flex cursor-pointer items-center gap-3 p-3">
				<span class="font-mono font-semibold">{key}</span>
				<span class="badge preset-tonal-surface px-2 py-0.5 text-xs">{describe(value)}</span>
			</summary>
			<pre class="max-h-[32rem] overflow-auto border-t border-surface-300-700 p-3 text-xs">{pretty(
					value
				)}</pre>
		</details>
	{:else}
		<p class="opacity-70">This job has no data.</p>
	{/each}
</section>
