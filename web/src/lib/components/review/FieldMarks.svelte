<!--
@component
History marks of one field: who changed it last (blue "corrected by validator", violet
"edited"), ↶ to undo the last change, and a popover with the field's history ("Restore" reverts an
edit). Renders nothing for a field without edits. Open flags are shown by `ReviewField`.

@param review - Review of the borehole.
@param field - API field name.
@param [layerId] - Layer of a layer field.
-->
<script lang="ts">
	import { Popover, Portal } from '@skeletonlabs/skeleton-svelte';
	import { SparklesIcon, Undo2Icon, UserPenIcon } from '@lucide/svelte';
	import { formatRelative } from '#lib/domain/pipelines.ts';
	import { formatValue, type Review } from './review.ts';

	interface Props {
		review: Review;
		field: string;
		layerId?: string | null;
	}

	let { review, field, layerId = null }: Props = $props();

	let edits = $derived(review.edits(field, layerId));
	let last = $derived(edits[0]);

	let summary = $derived(
		last &&
			`${last.source === 'validator' ? 'Corrected by validator' : 'Edited'}, was: ${formatValue(last.oldValue)}`
	);
</script>

{#if last}
	<span class="inline-flex shrink-0 items-center gap-0.5">
		<Popover positioning={{ placement: 'bottom-end' }}>
			<Popover.Trigger
				class="btn-icon size-6 hover:preset-tonal"
				title="{summary}\n(click for the history)"
				aria-label="History: {summary}"
			>
				{#if last.source === 'validator'}
					<SparklesIcon class="size-3.5 text-sky-500" />
				{:else}
					<UserPenIcon class="size-3.5 text-violet-500" />
				{/if}
			</Popover.Trigger>
			<Portal>
				<Popover.Positioner class="z-50">
					<Popover.Content
						class="max-h-96 w-80 space-y-3 overflow-y-auto card border border-surface-200-800 bg-surface-50-950 p-3 text-sm shadow-xl"
					>
						<div class="space-y-2">
							<p class="text-xs font-semibold uppercase opacity-60">History</p>
							<ol class="space-y-2">
								{#each edits as edit (edit.id)}
									<li class="flex items-start gap-2">
										{#if edit.source === 'validator'}
											<SparklesIcon class="mt-0.5 size-4 shrink-0 text-sky-500" />
										{:else}
											<UserPenIcon class="mt-0.5 size-4 shrink-0 text-violet-500" />
										{/if}
										<span class="min-w-0 flex-1">
											<span class="line-through opacity-60">{formatValue(edit.oldValue)}</span>
											→ {formatValue(edit.newValue)}
											<span class="block text-xs opacity-60">
												{edit.source === 'validator' ? 'Validator' : 'Edited'} · {formatRelative(
													new Date(edit.createdAt)
												)}{edit.reason ? ` · ${edit.reason}` : ''}
											</span>
										</span>
										<button
											type="button"
											class="btn preset-tonal btn-sm"
											title="Restore {formatValue(edit.oldValue)}"
											onclick={() => review.revert(edit.id)}
										>
											Restore
										</button>
									</li>
								{/each}
							</ol>
						</div>
					</Popover.Content>
				</Popover.Positioner>
			</Portal>
		</Popover>

		<button
			type="button"
			class="btn-icon size-6 hover:preset-tonal"
			title="Undo: restore {formatValue(last.oldValue)}"
			aria-label="Undo last change"
			onclick={() => review.revert(last.id)}
		>
			<Undo2Icon class="size-3.5" />
		</button>
	</span>
{/if}
