<script lang="ts">
	import { RefreshCwIcon } from '@lucide/svelte';
	import { notify } from '#lib/components/toast/index.ts';
	import {
		countByStatus,
		formatDuration,
		stageStatus,
		type JobStatus,
		type Pipeline
	} from '#lib/domain/pipelines.ts';
	import StatusIcon from './StatusIcon.svelte';

	/** GitLab-style flow graph: one card per stage with its jobs inside, joined by connector lines. */
	let { pipeline }: { pipeline: Pipeline } = $props();

	const summaryOrder: [JobStatus, string][] = [
		['success', 'passed'],
		['running', 'running'],
		['failed', 'failed'],
		['pending', 'pending'],
		['skipped', 'skipped']
	];

	function summary(jobs: Pipeline['stages'][number]['jobs']): string {
		const counts = countByStatus(jobs);
		const parts = summaryOrder
			.filter(([status]) => counts[status] > 0)
			.map(([status, label]) => `${counts[status]} ${label}`);
		return `${jobs.length} ${jobs.length === 1 ? 'job' : 'jobs'}${parts.length ? ` · ${parts.join(' · ')}` : ''}`;
	}
</script>

<div class="overflow-x-auto rounded-2xl bg-surface-100-900 p-6">
	<ol class="flex min-w-max items-start">
		{#each pipeline.stages as stage, i (stage.key)}
			{#if i > 0}
				<!-- connector at the height of the stage title -->
				<li class="mt-7 h-0.5 w-10 shrink-0 bg-surface-300-700" aria-hidden="true"></li>
			{/if}
			<li class="w-80 shrink-0 rounded-2xl bg-surface-200-800 p-1.5">
				<header class="px-3 pt-2.5 pb-3">
					<h3 class="flex items-center gap-2 font-bold">
						{stage.label}
					</h3>
					<p class="text-xs opacity-70">
						<span class="sr-only">{stageStatus(stage)}:</span>
						{summary(stage.jobs)}
					</p>
				</header>

				<ul class="space-y-1 rounded-xl bg-surface-50-950 p-1.5">
					{#each stage.jobs as job (job.id)}
						<li
							class="flex items-center gap-3 rounded-lg px-2.5 py-2.5"
							title={job.error ?? job.name}
						>
							<StatusIcon status={job.status} class="size-8" />
							<div class="min-w-0 flex-1">
								<p class="truncate">{job.name}</p>
								{#if job.durationSeconds !== undefined}
									<p class="text-xs opacity-60">{formatDuration(job.durationSeconds)}</p>
								{/if}
							</div>
							<button
								type="button"
								class="btn-icon size-8 rounded-full border border-surface-400-600 hover:preset-tonal"
								aria-label="Retry {job.name}"
								title="Retry"
								onclick={() => notify.error('Retrying jobs is not available yet.')}
							>
								<RefreshCwIcon class="size-4" />
							</button>
						</li>
					{:else}
						<li class="px-2.5 py-2.5 text-sm opacity-60">No jobs</li>
					{/each}
				</ul>
			</li>
		{/each}
	</ol>
</div>
