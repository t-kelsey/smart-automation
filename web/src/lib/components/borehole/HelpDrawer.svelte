<script lang="ts">
	import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';
	import { CircleHelpIcon, XIcon } from '@lucide/svelte';
	import { lithologies } from './lithology';
	import type { LithologyKey } from './types';

	interface Props {
		/** Colours used by the layers of the current borehole. */
		colors?: { hex: string; name: string }[];
	}

	let { colors = [] }: Props = $props();

	const lithologyKeys = Object.keys(lithologies) as LithologyKey[];
</script>

<Dialog>
	<Dialog.Trigger class="btn preset-tonal">
		<CircleHelpIcon class="size-4" />
		Help
	</Dialog.Trigger>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-40 bg-surface-950/50" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex justify-end">
			<Dialog.Content
				class="flex h-full w-full max-w-sm flex-col gap-6 overflow-y-auto bg-surface-50-950 p-6 shadow-xl"
			>
				<header class="flex items-start justify-between gap-4">
					<div>
						<Dialog.Title class="h4">Help</Dialog.Title>
						<Dialog.Description class="text-sm opacity-70">
							How to read the borehole cross section.
						</Dialog.Description>
					</div>
					<Dialog.CloseTrigger class="btn-icon preset-tonal" aria-label="Close help">
						<XIcon class="size-4" />
					</Dialog.CloseTrigger>
				</header>

				<section class="space-y-2">
					<h5 class="h6">Rock types (hatch patterns)</h5>
					<ul class="space-y-2">
						{#each lithologyKeys as key (key)}
							<li class="flex items-center gap-3 text-sm">
								<svg
									viewBox="0 0 40 24"
									class="h-6 w-10 shrink-0 rounded-sm border border-black/50"
								>
									<rect width="40" height="24" class="fill-surface-100-900" />
									<rect width="40" height="24" fill="url(#{lithologies[key].patternId})" />
								</svg>
								{lithologies[key].label}
							</li>
						{/each}
					</ul>
				</section>

				{#if colors.length}
					<section class="space-y-2">
						<h5 class="h6">Layer colours</h5>
						<p class="text-sm opacity-70">
							Fill colour as recorded on the original log; it is shown behind the hatch pattern.
						</p>
						<ul class="space-y-2">
							{#each colors as color (color.hex)}
								<li class="flex items-center gap-3 text-sm">
									<span
										class="size-6 shrink-0 rounded-sm border border-black/50"
										style:background-color={color.hex}
									></span>
									{color.name}
								</li>
							{/each}
						</ul>
					</section>
				{/if}

				<section class="space-y-2">
					<h5 class="h6">Axes and markers</h5>
					<ul class="list-disc space-y-1 pl-5 text-sm">
						<li>The left axis shows height in metres above sea level (m ü. NN).</li>
						<li>Labels next to the column show the stratigraphy code and rock type.</li>
						<li>EOH marks the end of the borehole.</li>
						<li>Hover or click a layer to highlight it in the layer table.</li>
					</ul>
				</section>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog>
