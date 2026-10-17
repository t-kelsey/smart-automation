<script lang="ts">
	import {
		ChevronDownIcon,
		EllipsisVerticalIcon,
		FileImageIcon,
		FileTextIcon,
		FileTypeIcon,
		PencilLine,
		PencilIcon,
		Share2Icon,
		TrashIcon,
		UploadIcon,
		Download
	} from '@lucide/svelte';
	import BoreholeColumn from '#lib/components/borehole/BoreholeColumn.svelte';
	import HelpDrawer from '#lib/components/borehole/HelpDrawer.svelte';
	import PatternDefs from '#lib/components/borehole/PatternDefs.svelte';
	import MapSnippet from '#lib/components/borehole/MapSnippet.svelte';
	import type { BoreholeDocument, BoreholeLayer } from '#lib/domain/borehole.ts';
	import { describe, shortForm } from '#lib/din4023/index.ts';
	import type { PageProps } from './$types';
	import { Collapsible, Menu, Portal } from '@skeletonlabs/skeleton-svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';

	let { data }: PageProps = $props();
	let borehole = $derived(data.borehole);

	let coreDataOpen = $state(true);
	let selectedLayerId = $state<string | null>(null);
	let colored = $state(true);

	let coreData = $derived([
		{ label: 'Name', value: borehole.name },
		{ label: 'Date', value: borehole.date ?? '–' },
		{ label: 'Boring cause', value: borehole.cause ?? '–' },
		{
			label: 'Height o. NN',
			value: borehole.elevation === null ? '–' : `${borehole.elevation.toFixed(2)} m`
		},
		{
			label: 'Total depth',
			value: borehole.totalDepth === null ? '–' : `${borehole.totalDepth.toFixed(1)} m`
		},
		{ label: 'Drilling method', value: borehole.drillingMethod ?? '–' },
		{ label: 'Client', value: borehole.client ?? '–' },
		{ label: 'Location', value: borehole.location?.place ?? '–' }
	]);

	const documentIcons: Record<BoreholeDocument['type'], typeof FileTextIcon> = {
		pdf: FileTextIcon,
		image: FileImageIcon,
		docx: FileTypeIcon
	};

	// TODO: wire up New Version, Rename and Delete once the API supports them.
	const documentActions = [
		{ label: 'Download', icon: Download },
		{ label: 'New Version', icon: UploadIcon },
		{ label: 'Rename', icon: PencilIcon },
		{ label: 'Delete', icon: TrashIcon, danger: true }
	];

	function onDocumentAction(doc: BoreholeDocument, action: string) {
		// The API sends the file as an attachment with ?download=1 (ADR-0026).
		if (action === 'Download' && doc.url) window.location.assign(`${doc.url}?download=1`);
	}
</script>

{#snippet petrography(layer: BoreholeLayer)}
	{@const composition = layer.petrography.composition}
	{#if composition}
		<span class="font-medium">{shortForm(composition)}</span>
		{describe(composition)}
	{:else}
		<span class="opacity-60">Unclassified</span>
	{/if}
	<span class="block text-xs opacity-60">{layer.petrography.description}</span>
{/snippet}

<PatternDefs />

<div class="-m-6 flex h-screen flex-col">
	<header
		class="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-surface-200-800 bg-surface-50-950 px-6 py-4"
	>
		<div>
			<h1 class="h2">Borehole {borehole.name}</h1>
			<p class="text-sm opacity-70">{borehole.location?.place ?? ''}</p>
		</div>
		<div class="flex items-center gap-2">
			<!-- TODO: implement sharing (e.g. copy link to this borehole). -->
			<button type="button" class="btn preset-tonal">
				<Share2Icon class="size-4" />
				Share
			</button>
			<HelpDrawer layers={borehole.layers} />
		</div>
	</header>

	<div class="min-h-0 flex-1 overflow-y-auto p-6">
		<div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
			<!-- Cross section -->
			<section class="card border border-surface-200-800 bg-surface-50-950 p-4 lg:col-span-1">
				<div class="mb-3 flex items-center justify-between gap-2">
					<h2 class="h5">Cross section</h2>
					<label class="flex cursor-pointer items-center gap-2 text-sm">
						<input type="checkbox" class="checkbox" bind:checked={colored} />
						Colour
					</label>
				</div>
				<BoreholeColumn
					layers={borehole.layers}
					totalDepth={borehole.totalDepth ?? 0}
					{colored}
					selectedId={selectedLayerId}
					onselect={(id) => (selectedLayerId = id)}
				/>
			</section>

			<div class="min-w-0 space-y-6 lg:col-span-3">
				<!-- Core data and map -->
				<Collapsible
					open={coreDataOpen}
					onOpenChange={(details) => (coreDataOpen = details.open)}
					class="items-stretch! card border border-surface-200-800 bg-surface-50-950 p-4"
				>
					<div class="flex items-center justify-between gap-2">
						<Collapsible.Trigger class="flex items-center gap-2 text-left">
							<h2 class="h5">Core data</h2>
							<ChevronDownIcon
								class="size-4 shrink-0 transition-transform {coreDataOpen ? '' : '-rotate-90'}"
							/>
						</Collapsible.Trigger>
						<button
							type="button"
							class="btn preset-tonal btn-sm"
							onclick={() => goto(resolve('/borehole/[id]/edit', { id: borehole.id }))}
						>
							<PencilLine class="size-4" />
							Edit
						</button>
					</div>
					<Collapsible.Content>
						<div class="mt-3 grid gap-4 xl:grid-cols-[1fr_20rem]">
							<dl class="grid grid-cols-[auto_1fr] content-start gap-x-6 gap-y-2 text-sm">
								{#each coreData as item (item.label)}
									<dt class="opacity-60">{item.label}</dt>
									<dd class="font-medium">{item.value}</dd>
								{/each}
							</dl>
							{#if borehole.location}
								<MapSnippet lat={borehole.location.lat} lon={borehole.location.lon} />
							{/if}
						</div>
					</Collapsible.Content>
				</Collapsible>

				<!-- Layer table -->
				<section class="@container card border border-surface-200-800 bg-surface-50-950 p-4">
					<div class="mb-3 flex items-center justify-between gap-2">
						<h2 class="h5">Layers</h2>
						<button
							type="button"
							class="btn preset-tonal btn-sm"
							onclick={() => goto(resolve('/borehole/[id]/edit', { id: borehole.id }))}
						>
							<PencilLine class="size-4" />
							Edit layers
						</button>
					</div>
					<!-- Narrow card: one card per layer instead of a horizontally scrolling table. -->
					<ul class="space-y-3 @2xl:hidden">
						{#each borehole.layers as layer (layer.id)}
							<li
								class="rounded-lg border border-surface-200-800 p-3 text-sm {selectedLayerId ===
								layer.id
									? 'bg-primary-500/15'
									: ''}"
								onmouseenter={() => (selectedLayerId = layer.id)}
								onmouseleave={() => (selectedLayerId = null)}
							>
								<div class="mb-2 flex items-center justify-between gap-2">
									<span class="font-medium">{layer.position}</span>
									<span class="text-xs opacity-60">
										{layer.startDepth.toFixed(1)} m – {layer.endDepth.toFixed(1)} m
									</span>
								</div>
								<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
									<dt class="opacity-60">Stratigraphie</dt>
									<dd>
										<span class="font-medium">{layer.stratigraphy.code}</span>
										<span class="text-xs opacity-60">{layer.stratigraphy.name}</span>
									</dd>
									<dt class="opacity-60">Petrographie</dt>
									<dd>
										{@render petrography(layer)}
									</dd>
									<dt class="opacity-60">Color</dt>
									<dd class="flex items-center gap-2">
										<span
											class="size-4 rounded-sm border border-black/40"
											style:background-color={layer.color.hex}
										></span>
										{layer.color.name}
									</dd>
								</dl>
							</li>
						{/each}
					</ul>

					<div class="hidden table-wrap @2xl:block">
						<table class="table">
							<thead>
								<tr>
									<th class="w-px">Id</th>
									<th class="w-px whitespace-nowrap">From (m)</th>
									<th class="w-px whitespace-nowrap">To (m)</th>
									<th>Stratigraphie</th>
									<th>Petrographie</th>
									<th>Color</th>
								</tr>
							</thead>
							<tbody>
								{#each borehole.layers as layer (layer.id)}
									<tr
										class={selectedLayerId === layer.id ? 'bg-primary-500/15' : ''}
										onmouseenter={() => (selectedLayerId = layer.id)}
										onmouseleave={() => (selectedLayerId = null)}
									>
										<td class="font-medium">{layer.position}</td>
										<td class="whitespace-nowrap">{layer.startDepth.toFixed(1)}</td>
										<td class="whitespace-nowrap">{layer.endDepth.toFixed(1)}</td>
										<td>
											<span class="font-medium">{layer.stratigraphy.code}</span>
											<span class="block text-xs opacity-60">{layer.stratigraphy.name}</span>
										</td>
										<td>
											{@render petrography(layer)}
										</td>
										<td>
											<span class="flex items-center gap-2 whitespace-nowrap">
												<span
													class="size-4 rounded-sm border border-black/40"
													style:background-color={layer.color.hex}
												></span>
												{layer.color.name}
											</span>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</section>

				<!-- Original documents -->
				<section class="card border border-surface-200-800 bg-surface-50-950 p-4">
					<div class="mb-3 flex items-center justify-between gap-2">
						<h2 class="h5">Original documents</h2>
						<!-- TODO: implement document upload. -->
						<button type="button" class="btn preset-tonal btn-sm">
							<UploadIcon class="size-4" />
							Upload
						</button>
					</div>
					<ul class="divide-y divide-surface-200-800">
						{#each borehole.documents as doc (doc.id)}
							{@const Icon = documentIcons[doc.type]}
							<li class="group flex items-center gap-3 py-2 text-sm">
								<Icon class="size-5 shrink-0 opacity-70" />
								<a
									href={resolve('/document/[id]', { id: doc.id })}
									class="min-w-0 flex-1 truncate anchor">{doc.name}</a
								>
								<span class="shrink-0 text-xs opacity-60">
									{[
										doc.type.toUpperCase(),
										doc.pages ? `${doc.pages} p.` : null,
										doc.language,
										doc.sizeKb ? `${(doc.sizeKb / 1024).toFixed(1)} MB` : null
									]
										.filter(Boolean)
										.join(' · ')}
								</span>
								<!-- Fixed-size slot so the row does not shift when the trigger appears. -->
								<div class="size-8 shrink-0">
									<Menu
										positioning={{ placement: 'bottom-end' }}
										onSelect={(details) => onDocumentAction(doc, details.value)}
									>
										<Menu.Trigger
											class="btn-icon size-8 opacity-0 group-hover:opacity-100 hover:preset-tonal focus-visible:opacity-100 data-[state=open]:opacity-100"
											aria-label="Actions for {doc.name}"
										>
											<EllipsisVerticalIcon class="size-4" />
										</Menu.Trigger>
										<Portal>
											<Menu.Positioner>
												<Menu.Content
													class="w-52 card rounded-2xl bg-surface-100-900 p-2 shadow-xl"
												>
													{#each documentActions as action (action.label)}
														<Menu.Item
															value={action.label}
															disabled={action.label === 'Download' && !doc.url}
															class="flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 text-sm hover:preset-tonal {action.danger
																? 'text-error-500'
																: ''}"
														>
															<action.icon class="size-4" />
															<Menu.ItemText>{action.label}</Menu.ItemText>
														</Menu.Item>
													{/each}
												</Menu.Content>
											</Menu.Positioner>
										</Portal>
									</Menu>
								</div>
							</li>
						{:else}
							<li class="py-2 text-sm opacity-60">No documents linked.</li>
						{/each}
					</ul>
				</section>
			</div>
		</div>
	</div>
</div>
