<script lang="ts">
	import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';
	import { CircleHelpIcon, XIcon } from '@lucide/svelte';
	import { mapColors } from './map-colors.ts';
</script>

{#snippet dot(color: string, halo = false, hollow = false)}
	<span
		class="size-4 shrink-0 rounded-full border-2 border-white shadow-md"
		style:background={hollow ? 'white' : color}
		style:outline={hollow ? `3px solid ${color}` : undefined}
		style:outline-offset="-5px"
		style:box-shadow={halo ? `0 0 0 6px ${color}40` : undefined}
	></span>
{/snippet}

<Dialog>
	<Dialog.Trigger class="btn preset-filled-surface-50-950 shadow-md btn-sm">
		<CircleHelpIcon class="size-4" />
		Help
	</Dialog.Trigger>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-40 bg-surface-950/50" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex justify-end">
			<Dialog.Content
				class="flex h-full w-full max-w-md flex-col gap-6 overflow-y-auto bg-surface-50-950 p-6 shadow-xl"
			>
				<header class="flex items-start justify-between gap-4">
					<div>
						<Dialog.Title class="h4">Help</Dialog.Title>
						<Dialog.Description class="text-sm opacity-70">
							How to read the borehole map.
						</Dialog.Description>
					</div>
					<Dialog.CloseTrigger class="btn-icon preset-tonal" aria-label="Close help">
						<XIcon class="size-4" />
					</Dialog.CloseTrigger>
				</header>

				<section class="space-y-3">
					<h5 class="h6">Dots</h5>
					<ul class="space-y-3 text-sm">
						<li class="flex items-center gap-3">
							{@render dot(mapColors.verified)}
							<span
								><strong>Verified</strong> (filled): the extracted data was checked and released.</span
							>
						</li>
						<li class="flex items-center gap-3">
							{@render dot(mapColors.unverified, false, true)}
							<span>
								<strong>Not verified</strong> (hollow): extracted automatically, not released yet.
							</span>
						</li>
						<li class="flex items-center gap-3">
							<span
								class="flex size-9 shrink-0 items-center justify-center rounded-full border-2 border-white bg-primary-500 text-xs font-semibold text-white shadow-md"
								>12</span
							>
							<span>
								<strong>Cluster</strong>: that many boreholes close together. Click it to zoom in.
							</span>
						</li>
						<li class="flex items-center gap-3">
							{@render dot(mapColors.location, true)}
							<span><strong>Your location</strong>, after you allowed it in the browser.</span>
						</li>
					</ul>
				</section>

				<section class="space-y-2">
					<h5 class="h6">Detail view</h5>
					<ul class="list-disc space-y-1 pl-5 text-sm">
						<li>
							Zoom in to level 11 or closer and press <em>Detail view</em>: the map tilts and each
							borehole becomes a column of its layers.
						</li>
						<li>
							The column is the borehole lifted out of the ground: the surface layer is on top, the
							deepest layer stands on the map. Columns are 10 times taller than the borehole is
							deep.
						</li>
						<li>
							Each layer shows the DIN 4023 hatch and colour of its main material; grey layers could
							not be classified, empty parts are depths without a recorded layer.
						</li>
						<li>
							Hover or tap a layer to see its depth and material. Zooming out leaves the view.
						</li>
						<li>Drag with the right mouse button (or two fingers) to rotate and tilt.</li>
					</ul>
				</section>

				<section class="space-y-2">
					<h5 class="h6">Section</h5>
					<ul class="list-disc space-y-1 pl-5 text-sm">
						<li>
							Press <em>Section</em>, click the start and the end of a line (Esc cancels). The map
							shows the boreholes within 100 m of it.
						</li>
						<li>
							<em>Show section</em> shows them side by side at their distance along the line, all starting
							at the same height, so equal depths line up.
						</li>
						<li>
							Between neighbouring boreholes, layers of the same material are connected unless they
							would slope more than 45° (at 10× vertical exaggeration); layers without a partner
							wedge out halfway. These predictions are lighter with dashed outlines and can be
							switched off.
						</li>
						<li>Hover a layer for details, click a column to open the borehole.</li>
					</ul>
				</section>

				<section class="space-y-2">
					<h5 class="h6">Using the map</h5>
					<ul class="list-disc space-y-1 pl-5 text-sm">
						<li>Hover or tap a dot for title, date, height and depth.</li>
						<li>
							Use <em>Details</em> in the card to open the borehole log, <em>Share</em> to copy its link.
						</li>
						<li>The button in the lower right corner moves the map to your location.</li>
						<li>The address bar always holds the current view, so you can share it as a link.</li>
					</ul>
				</section>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog>
