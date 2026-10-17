<script lang="ts">
	import { ArrowLeftIcon } from '@lucide/svelte';
	import { resolve } from '$app/paths';
	import { DocumentViewer } from '#lib/components/document/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let document = $derived(data.document);
</script>

<svelte:head>
	<title>{document.name}</title>
</svelte:head>

<div class="flex h-screen flex-col gap-3 p-4">
	<nav class="flex flex-wrap gap-x-4 gap-y-1 text-sm">
		{#each document.boreholes as borehole (borehole.id)}
			<a
				href={resolve('/borehole/[id]', { id: borehole.id })}
				class="inline-flex items-center gap-1 anchor"
			>
				<ArrowLeftIcon class="size-4" />
				{borehole.name}
			</a>
		{/each}
	</nav>
	<DocumentViewer {document} class="flex-1" />
</div>
