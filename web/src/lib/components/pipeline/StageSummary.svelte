<script lang="ts">
	import { stageStatus, type Pipeline } from '#lib/domain/pipelines.ts';
	import StatusIcon from './StatusIcon.svelte';

	/** GitLab-style row of status circles joined by short lines, one per stage. */
	let { pipeline }: { pipeline: Pipeline } = $props();
</script>

<ol class="flex items-center" aria-label="Stages">
	{#each pipeline.stages as stage, i (stage.key)}
		<li class="flex items-center" title="{stage.label}: {stage.jobs.length} jobs">
			{#if i > 0}<span class="h-0.5 w-2 bg-surface-300-700" aria-hidden="true"></span>{/if}
			<StatusIcon status={stageStatus(stage)} class="size-7" />
		</li>
	{/each}
</ol>
