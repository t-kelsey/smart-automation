<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import {
		ArrowLeftIcon,
		FileIcon,
		LoaderCircleIcon,
		PlayIcon,
		SlidersHorizontalIcon
	} from '@lucide/svelte';
	import { notify } from '#lib/components/toast/index.ts';
	import { SegmentedControl } from '@skeletonlabs/skeleton-svelte';
	import {
		createDefaultPipelineConfig,
		PIPELINE_EFFORTS,
		PIPELINE_MODELS,
		PIPELINE_STEPS,
		type PipelineConfig,
		type PipelineEffort,
		type PipelineModel
	} from '#lib/domain/documents.ts';
	import { getQueuedFiles, markUploaded, unqueueFile } from '#lib/upload-queue.svelte.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const queued = $derived(getQueuedFiles());
	let uploading = $state(false);
	let config = $state<PipelineConfig>(createDefaultPipelineConfig());

	// The layout's <main> scrolls, not the window, so SvelteKit does not reset it on navigation.
	onMount(() => document.querySelector('main')?.scrollTo({ top: 0 }));

	/**
	 * Uploads every queued file (`POST /documents`) and submits it to the pipeline with the chosen
	 * config (`POST /pipeline_runs`). A file stays in the list if either step fails; one that is
	 * already uploaded is not uploaded again on a retry.
	 */
	async function start() {
		uploading = true;
		const runs: string[] = [];
		for (const queuedFile of [...queued]) {
			const { id, file } = queuedFile;
			try {
				let documentId = queuedFile.documentId;
				if (!documentId) {
					documentId = (await data.uploads.upload(file)).id;
					markUploaded(id, documentId);
				}
				const run = await data.pipelines.start(documentId, $state.snapshot(config));
				if (run.status === 'running') {
					runs.push(run.id);
					unqueueFile(id);
				} else if (run.status === 'failed') {
					notify.error(`The pipeline refused ${file.name}`, 'It is uploaded; try again later.');
				} else {
					notify.error(`${file.name} is uploaded but not started`, 'No pipeline is configured.');
				}
			} catch (e) {
				notify.fromError(e, `Could not process ${file.name}`);
			}
		}
		uploading = false;
		if (runs.length === 0) return;
		notify.success(
			runs.length === 1 ? 'Extraction started.' : `Extraction started for ${runs.length} files.`
		);
		await goto(
			runs.length === 1 && queued.length === 0
				? resolve('/pipeline/[id]', { id: runs[0] })
				: resolve('/pipeline')
		);
	}
</script>

<h1 class="mb-4 h1">Configure extraction</h1>
<p class="mb-6 max-w-prose opacity-70">
	Nothing is uploaded or processed until you start the extraction.
</p>

{#if queued.length === 0}
	<p class="mb-6">No files selected.</p>
	<a href={resolve('/upload')} class="btn preset-tonal"
		><ArrowLeftIcon class="size-4" /> Back to upload</a
	>
{:else}
	<section
		class="mb-10 card rounded-3xl border-2 border-primary-500 bg-primary-500/5 p-6 shadow-lg"
		aria-labelledby="config-heading"
	>
		<div class="mb-1 flex items-center gap-2">
			<SlidersHorizontalIcon class="size-5 text-primary-500" />
			<h2 id="config-heading" class="h3">Pipeline settings</h2>
		</div>
		<p class="mb-6 text-sm opacity-70">
			Choose the AI model and how much effort it spends on each step. Larger models and higher
			effort are more accurate but slower and more expensive.
		</p>

		<div class="mb-6 space-y-5">
			{#each PIPELINE_STEPS as step, i (step.key)}
				<div
					class="grid items-center gap-x-6 gap-y-2 border-surface-200-800 not-first:border-t not-first:pt-5 lg:grid-cols-[1fr_auto_auto]"
				>
					<div>
						<p class="font-bold">{i + 1}. {step.label}</p>
						<p class="text-xs opacity-60">{step.hint}</p>
					</div>

					<SegmentedControl
						value={config[step.key].model}
						onValueChange={(d) => d.value && (config[step.key].model = d.value as PipelineModel)}
						aria-label="{step.label} model"
					>
						<SegmentedControl.Label>Model</SegmentedControl.Label>
						<SegmentedControl.Control>
							<SegmentedControl.Indicator />
							{#each PIPELINE_MODELS as model (model)}
								<SegmentedControl.Item value={model}>
									<SegmentedControl.ItemText>{model}</SegmentedControl.ItemText>
									<SegmentedControl.ItemHiddenInput />
								</SegmentedControl.Item>
							{/each}
						</SegmentedControl.Control>
					</SegmentedControl>

					<SegmentedControl
						value={config[step.key].effort}
						onValueChange={(d) => d.value && (config[step.key].effort = d.value as PipelineEffort)}
						aria-label="{step.label} effort"
					>
						<SegmentedControl.Label>Effort</SegmentedControl.Label>
						<SegmentedControl.Control>
							<SegmentedControl.Indicator />
							{#each PIPELINE_EFFORTS as effort (effort)}
								<SegmentedControl.Item value={effort}>
									<SegmentedControl.ItemText>{effort}</SegmentedControl.ItemText>
									<SegmentedControl.ItemHiddenInput />
								</SegmentedControl.Item>
							{/each}
						</SegmentedControl.Control>
					</SegmentedControl>
				</div>
			{/each}
		</div>

		<div class="flex flex-wrap items-center justify-between gap-3">
			<button
				type="button"
				class="btn preset-tonal"
				onclick={() => (config = createDefaultPipelineConfig())}
			>
				Reset to defaults
			</button>
			<button
				type="button"
				class="btn preset-filled-primary-500 btn-lg"
				disabled={uploading}
				onclick={start}
			>
				{#if uploading}
					<LoaderCircleIcon class="size-5 animate-spin" />
				{:else}
					<PlayIcon class="size-5" />
				{/if}
				Start extraction
			</button>
		</div>
	</section>

	<h2 class="mb-2 h5 opacity-80">Files ({queued.length})</h2>
	<ul class="mb-6 space-y-2 text-sm">
		{#each queued as { id, file } (id)}
			<li class="flex items-center gap-3 rounded-xl preset-outlined-surface-200-800 px-3 py-2">
				<FileIcon class="size-4 shrink-0 opacity-60" />
				<span class="truncate">{file.name}</span>
			</li>
		{/each}
	</ul>

	<a href={resolve('/upload')} class="btn preset-tonal"><ArrowLeftIcon class="size-4" /> Back</a>
{/if}
