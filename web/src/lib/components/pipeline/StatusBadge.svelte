<script lang="ts">
	import type { PipelineStatus } from '#lib/domain/pipelines.ts';
	import StatusIcon from './StatusIcon.svelte';

	let { status }: { status: PipelineStatus } = $props();

	const labels: Record<PipelineStatus, string> = {
		pending: 'Pending',
		running: 'Running',
		success: 'Passed',
		failed: 'Failed',
		partial: 'Partially failed',
		skipped: 'Skipped'
	};
	const presets: Record<PipelineStatus, string> = {
		pending: 'preset-tonal-surface',
		running: 'preset-tonal-primary',
		success: 'preset-tonal-success',
		failed: 'preset-tonal-error',
		partial: 'preset-tonal-warning',
		skipped: 'preset-tonal-surface'
	};
</script>

<span class="badge rounded-full py-1 pr-3 pl-1.5 font-medium {presets[status]}">
	<StatusIcon {status} class="size-5" />
	{labels[status]}
</span>
