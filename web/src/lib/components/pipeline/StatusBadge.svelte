<script lang="ts">
	import type { JobStatus } from '#lib/domain/pipelines.ts';
	import StatusIcon from './StatusIcon.svelte';

	let { status }: { status: JobStatus } = $props();

	const labels: Record<JobStatus, string> = {
		pending: 'Pending',
		running: 'Running',
		success: 'Passed',
		failed: 'Failed',
		skipped: 'Skipped'
	};
	const presets: Record<JobStatus, string> = {
		pending: 'preset-tonal-surface',
		running: 'preset-tonal-primary',
		success: 'preset-tonal-success',
		failed: 'preset-tonal-error',
		skipped: 'preset-tonal-surface'
	};
</script>

<span class="badge rounded-full py-1 pr-3 pl-1.5 font-medium {presets[status]}">
	<StatusIcon {status} class="size-5" />
	{labels[status]}
</span>
