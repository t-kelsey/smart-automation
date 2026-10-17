<script lang="ts">
	import { resolve } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import { CalendarIcon, ClockIcon, RefreshCwIcon, SearchIcon } from '@lucide/svelte';
	import { notify } from '#lib/components/toast/index.ts';
	import { StageSummary, StatusBadge } from '#lib/components/pipeline/index.ts';
	import { retryPipeline } from '#lib/components/pipeline/retry.ts';
	import {
		formatClock,
		formatRelative,
		isActive,
		pipelineDuration,
		pipelineStatus
	} from '#lib/domain/pipelines.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	$effect(() => {
		if (data.loadError) notify.fromError(data.loadError, 'Could not load pipelines');
	});

	// Keep polling while a pipeline is still going.
	$effect(() => {
		if (!data.pipelines.some(isActive)) return;
		const timer = setInterval(() => invalidate('app:pipelines'), 3000);
		return () => clearInterval(timer);
	});

	let tab = $state('all');
	let filter = $state('');

	const tabs = $derived([
		{ id: 'all', label: 'All', pipelines: data.pipelines },
		{
			id: 'running',
			label: 'Running',
			pipelines: data.pipelines.filter((p) => ['pending', 'running'].includes(pipelineStatus(p)))
		},
		{
			id: 'finished',
			label: 'Finished',
			pipelines: data.pipelines.filter((p) =>
				['success', 'failed', 'skipped'].includes(pipelineStatus(p))
			)
		}
	]);
	const visible = $derived(
		(tabs.find((t) => t.id === tab)?.pipelines ?? []).filter((p) =>
			p.filename.toLowerCase().includes(filter.trim().toLowerCase())
		)
	);

	function extension(filename: string): string {
		return filename.split('.').pop()?.toUpperCase() ?? '';
	}
</script>

<svelte:head>
	<title>Pipelines</title>
</svelte:head>

<h1 class="mb-4 h1">Pipelines</h1>

<Tabs value={tab} onValueChange={(details) => (tab = details.value)}>
	<Tabs.List>
		{#each tabs as t (t.id)}
			<Tabs.Trigger value={t.id} class="flex items-center gap-2">
				{t.label}
				<span class="badge preset-tonal-surface px-2 py-0.5 text-xs">{t.pipelines.length}</span>
			</Tabs.Trigger>
		{/each}
		<Tabs.Indicator />
	</Tabs.List>
</Tabs>

<form class="my-4 flex" role="search" onsubmit={(e) => e.preventDefault()}>
	<input
		type="search"
		class="input min-w-0 flex-1 rounded-r-none"
		placeholder="Filter pipelines"
		aria-label="Filter pipelines"
		bind:value={filter}
	/>
	<button
		type="submit"
		class="btn rounded-l-none preset-outlined-surface-300-700"
		aria-label="Search"
	>
		<SearchIcon class="size-4" />
	</button>
</form>

{#if visible.length === 0}
	<p class="opacity-70">
		{data.pipelines.length === 0
			? 'No pipelines yet. Upload a document to start one.'
			: 'No pipelines match.'}
	</p>
{:else}
	<div class="table-wrap">
		<table class="table">
			<thead>
				<tr>
					<th>Status</th>
					<th>Pipeline</th>
					<th>Stages</th>
					<th><span class="sr-only">Actions</span></th>
				</tr>
			</thead>
			<tbody class="align-top">
				{#each visible as pipeline (pipeline.id)}
					<tr>
						<td class="space-y-1.5">
							<StatusBadge status={pipelineStatus(pipeline)} />
							<p class="flex items-center gap-1.5 text-sm opacity-70">
								<ClockIcon class="size-3.5" />
								{formatClock(pipelineDuration(pipeline))}
							</p>
							<p class="flex items-center gap-1.5 text-sm opacity-70">
								<CalendarIcon class="size-3.5" />
								{formatRelative(pipeline.createdAt)}
							</p>
						</td>
						<td class="space-y-1.5">
							<a
								href={resolve('/pipeline/[id]', { id: pipeline.id })}
								class="font-medium text-primary-600-400 hover:underline"
							>
								{pipeline.filename}
							</a>
							<p class="flex flex-wrap items-center gap-2 text-sm">
								<span class="opacity-70">#{pipeline.id.slice(-6)}</span>
								<span class="chip preset-tonal-surface font-mono text-xs">
									{extension(pipeline.filename)}
								</span>
								<span class="chip preset-tonal-surface font-mono text-xs">
									{pipeline.stages.flatMap((s) => s.jobs).length} jobs
								</span>
							</p>
						</td>
						<td><StageSummary {pipeline} /></td>
						<td class="text-right">
							<button
								type="button"
								class="btn-icon preset-outlined-surface-300-700"
								aria-label="Retry {pipeline.filename}"
								title="Retry"
								disabled={isActive(pipeline)}
								onclick={() => retryPipeline(data.service, pipeline)}
							>
								<RefreshCwIcon class="size-4" />
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
