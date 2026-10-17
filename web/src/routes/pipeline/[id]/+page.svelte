<script lang="ts">
	import { goto, invalidate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import {
		ArrowLeftIcon,
		ChevronRightIcon,
		ListIcon,
		MapPinIcon,
		RefreshCwIcon,
		Trash2Icon,
		WorkflowIcon
	} from '@lucide/svelte';
	import { PipelineGraph, StatusBadge, StatusIcon } from '#lib/components/pipeline/index.ts';
	import { notify } from '#lib/components/toast/index.ts';
	import { retryPipeline } from '#lib/components/pipeline/retry.ts';
	import {
		formatDuration,
		isActive,
		pipelineDuration,
		pipelineStatus,
		stageStatus
	} from '#lib/domain/pipelines.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let pipeline = $derived(data.pipeline);
	let tab = $state('pipeline');

	// Keep polling while the pipeline is still going.
	$effect(() => {
		if (!isActive(pipeline)) return;
		const timer = setInterval(() => invalidate('app:pipelines'), 3000);
		return () => clearInterval(timer);
	});

	async function deletePipeline() {
		const warning = isActive(pipeline) ? ' It is still running and will be cancelled.' : '';
		if (!confirm(`Delete this pipeline run and its jobs?${warning}`)) return;
		try {
			await data.service.delete(pipeline.id);
			notify.success('Pipeline deleted.');
			await goto(resolve('/pipeline'), { invalidateAll: true });
		} catch (e) {
			notify.fromError(e, 'Could not delete the pipeline');
		}
	}

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
	<button
		type="button"
		class="ml-auto btn preset-tonal"
		disabled={isActive(pipeline)}
		onclick={() => retryPipeline(data.service, pipeline)}
	>
		<RefreshCwIcon class="size-4" /> Retry
	</button>
	<button type="button" class="btn preset-tonal-error" onclick={deletePipeline}>
		<Trash2Icon class="size-4" /> Delete
	</button>
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
								<span class="flex flex-wrap items-center gap-x-3 gap-y-1">
									{#if job.execStageId}
										<a
											href={resolve('/jobs/[id]', { id: job.execStageId })}
											class="inline-flex items-center gap-1 font-medium text-primary-600-400 hover:underline"
										>
											{job.name}<ChevronRightIcon class="size-4" aria-hidden="true" />
										</a>
									{:else}
										{job.name}
									{/if}
									{#if job.boreholeId}
										<a
											href={resolve('/borehole/[id]', { id: job.boreholeId })}
											class="chip preset-tonal-primary text-xs"
										>
											<MapPinIcon class="size-3" /> Borehole
										</a>
									{/if}
								</span>
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
