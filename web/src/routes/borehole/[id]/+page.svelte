<script lang="ts">
	import {
		ChevronDownIcon,
		EllipsisVerticalIcon,
		FileImageIcon,
		FileTextIcon,
		FileTypeIcon,
		PencilLine,
		PencilIcon,
		TrashIcon,
		UploadIcon,
		Download
	} from '@lucide/svelte';
	import BoreholePageHeader from '#lib/components/borehole/BoreholePageHeader.svelte';
	import CoreData from '#lib/components/borehole/CoreData.svelte';
	import CrossSection from '#lib/components/borehole/CrossSection.svelte';
	import LayersTable from '#lib/components/borehole/LayersTable.svelte';
	import HelpDrawer from '#lib/components/borehole/HelpDrawer.svelte';
	import PatternDefs from '#lib/components/borehole/PatternDefs.svelte';
	import type { BoreholeDocument } from '#lib/domain/borehole.ts';
	import { LayerSelection } from '#lib/layer-selection.svelte.ts';
	import type { PageProps } from './$types';
	import { Collapsible, Menu, Portal } from '@skeletonlabs/skeleton-svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';

	let { data }: PageProps = $props();
	let borehole = $derived(data.borehole);

	let coreDataOpen = $state(true);
	// Click selection is stored per borehole, so it carries over between details and review.
	let selection = $derived(new LayerSelection(borehole.id));
	$effect(() => selection.restore());

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

<PatternDefs />

<div class="-m-6 flex h-screen flex-col">
	<BoreholePageHeader {borehole} view="details">
		<HelpDrawer layers={borehole.layers} />
	</BoreholePageHeader>

	<div class="min-h-0 flex-1 overflow-y-auto p-6">
		<div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-[18rem_minmax(0,1fr)]">
			<!-- Cross section: as high as the screen below the header, and kept in view while scrolling -->
			<section
				class="flex h-[calc(100dvh-9rem)] flex-col self-start card border border-surface-200-800 bg-surface-50-950 p-4 lg:sticky lg:top-0"
			>
				<h2 class="mb-3 shrink-0 h5">Cross section</h2>
				<CrossSection {borehole} {selection} class="flex-1" />
			</section>

			<div class="min-w-0 space-y-6">
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
						<CoreData {borehole} class="mt-3" />
					</Collapsible.Content>
				</Collapsible>

				<!-- Layer table -->
				<section class="card border border-surface-200-800 bg-surface-50-950 p-4">
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
					<LayersTable layers={borehole.layers} {selection} />
				</section>

				<!-- Documents: the original log and additional information files -->
				<section class="card border border-surface-200-800 bg-surface-50-950 p-4">
					<div class="mb-3 flex items-center justify-between gap-2">
						<h2 class="h5">Documents</h2>
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
								{#if doc.role === 'original'}
									<span class="badge preset-tonal-primary">Original</span>
								{/if}
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
