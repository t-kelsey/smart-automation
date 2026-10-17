<script lang="ts">
	import { CheckIcon, ChevronsRightIcon, LoaderCircleIcon, XIcon } from '@lucide/svelte';
	import type { JobStatus } from '#lib/domain/pipelines.ts';

	/** GitLab-style status mark: a filled circle on a soft halo. */
	let { status, class: className = 'size-6' }: { status: JobStatus; class?: string } = $props();

	const labels: Record<JobStatus, string> = {
		pending: 'Pending',
		running: 'Running',
		success: 'Passed',
		failed: 'Failed',
		skipped: 'Skipped'
	};
	const halos: Record<JobStatus, string> = {
		pending: 'bg-surface-300-700/60 text-surface-600-400',
		running: 'bg-primary-500/20 text-primary-500',
		success: 'bg-success-500/25',
		failed: 'bg-error-500/25',
		skipped: 'bg-surface-300-700/60 text-surface-600-400'
	};
</script>

<span
	class="inline-flex shrink-0 items-center justify-center rounded-full p-[12%] {halos[
		status
	]} {className}"
	role="img"
	aria-label={labels[status]}
	title={labels[status]}
>
	{#if status === 'success'}
		<span class="flex size-full items-center justify-center rounded-full bg-success-600 text-white">
			<CheckIcon class="size-[70%]" strokeWidth={3.5} />
		</span>
	{:else if status === 'failed'}
		<span class="flex size-full items-center justify-center rounded-full bg-error-600 text-white">
			<XIcon class="size-[70%]" strokeWidth={3.5} />
		</span>
	{:else if status === 'running'}
		<LoaderCircleIcon class="size-full animate-spin" strokeWidth={3} />
	{:else if status === 'skipped'}
		<ChevronsRightIcon class="size-full" strokeWidth={3} />
	{:else}
		<span class="size-full rounded-full border-2 border-dashed border-current"></span>
	{/if}
</span>
