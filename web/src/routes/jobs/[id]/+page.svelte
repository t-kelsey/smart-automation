<script lang="ts">
	import { resolve } from '$app/paths';
	import { ArrowLeftIcon } from '@lucide/svelte';
	import { PIPELINE_STAGES } from '#lib/domain/pipelines.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let job = $derived(data.job);
	let pipeline = $derived(data.pipeline);

	const formatter = new Intl.DateTimeFormat(undefined, {
		dateStyle: 'medium',
		timeStyle: 'medium'
	});
	let stageLabel = $derived(PIPELINE_STAGES.find((s) => s.key === job.type)?.label ?? job.type);
	let title = $derived(job.position === undefined ? stageLabel : `${stageLabel} #${job.position}`);

	/** Top level attributes of the result, or the whole value if it is not an object. */
	let attributes = $derived.by(() => {
		const value = job.data;
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

<header class="mb-6">
	<h1 class="h2">{title}</h1>
	<p class="text-sm opacity-70">#{job.id.slice(-6)} · {formatter.format(job.createdAt)}</p>
</header>

<section class="mb-8">
	<h2 class="mb-2 h4">Core data</h2>
	<div class="table-wrap">
		<table class="table">
			<tbody>
				<tr><th class="w-48">Job ID</th><td class="font-mono text-sm">{job.id}</td></tr>
				<tr><th>Stage</th><td>{stageLabel} <span class="opacity-60">({job.type})</span></td></tr>
				<tr><th>Borehole position</th><td>{job.position ?? '–'}</td></tr>
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
				<tr><th>Executed</th><td>{formatter.format(job.createdAt)}</td></tr>
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
