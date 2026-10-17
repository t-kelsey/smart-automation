<script lang="ts">
	import { resolve } from '$app/paths';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import { ArrowLeftIcon, ListIcon, WorkflowIcon } from '@lucide/svelte';
	import { PipelineGraph, StatusBadge, StatusIcon } from '#lib/components/pipeline/index.ts';
	import {
		formatDuration,
		pipelineDuration,
		pipelineStatus,
		stageStatus
	} from '#lib/domain/pipelines.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let pipeline = $derived(data.pipeline);
	let tab = $state('pipeline');

	const formatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });
	const jobs = $derived(
		pipeline.stages.flatMap((stage) => stage.jobs.map((job) => ({ ...job, stage })))
	);
</script>

<svelte:head>
	<title>Pipeline {pipeline.filename}</title>
</svelte:head>

<a href={resolve('/pipeline')} class="mb-4 btn preset-tonal btn-sm">
	<ArrowLeftIcon class="size-4" /> All pipelines
</a>

<header class="mb-6 flex flex-wrap items-center gap-x-4 gap-y-2">
	<StatusBadge status={pipelineStatus(pipeline)} />
	<h1 class="min-w-0 truncate h2">{pipeline.filename}</h1>
	<p class="text-sm opacity-70">
		#{pipeline.id.slice(-6)} · started {formatter.format(pipeline.createdAt)} · {formatDuration(
			pipelineDuration(pipeline)
		)}
	</p>
</header>

<Tabs value={tab} onValueChange={(details) => (tab = details.value)}>
	<Tabs.List>
		<Tabs.Trigger value="pipeline" class="flex items-center gap-2">
			<WorkflowIcon class="size-4" />
			Pipeline
		</Tabs.Trigger>
		<Tabs.Trigger value="jobs" class="flex items-center gap-2">
			<ListIcon class="size-4" />
			Jobs
			<span class="badge preset-tonal-surface px-2 py-0.5 text-xs">{jobs.length}</span>
		</Tabs.Trigger>
		<Tabs.Indicator />
	</Tabs.List>

	<Tabs.Content value="pipeline" class="pt-6">
		<PipelineGraph {pipeline} />
	</Tabs.Content>

	<Tabs.Content value="jobs" class="pt-6">
		<div class="table-wrap">
			<table class="table">
				<thead>
					<tr>
						<th>Status</th>
						<th>Job</th>
						<th>Stage</th>
						<th>Model</th>
						<th class="text-right">Duration</th>
					</tr>
				</thead>
				<tbody>
					{#each jobs as job (job.stage.key + job.id)}
						<tr>
							<td><StatusIcon status={job.status} class="size-7" /></td>
							<td>
								{job.name}
								{#if job.error}<p class="text-xs text-error-500">{job.error}</p>{/if}
							</td>
							<td>
								<span class="flex items-center gap-2">
									<StatusIcon status={stageStatus(job.stage)} class="size-6" />
									{job.stage.label}
								</span>
							</td>
							<td>{job.model ?? '–'}</td>
							<td class="text-right">
								{job.durationSeconds === undefined ? '–' : formatDuration(job.durationSeconds)}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</Tabs.Content>
</Tabs>
