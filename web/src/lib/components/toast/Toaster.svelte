<!--
@component
Renders the toasts created through `notify` / `toaster`. Mount once in the root layout.
-->

<script lang="ts">
	import { Toast } from '@skeletonlabs/skeleton-svelte';
	import { toaster } from './toaster.ts';
</script>

<Toast.Group {toaster}>
	{#snippet children(toast)}
		<Toast {toast}>
			<Toast.Message>
				<Toast.Title>{toast.title}</Toast.Title>
				<Toast.Description>{toast.description}</Toast.Description>
			</Toast.Message>
			<Toast.CloseTrigger />
		</Toast>
	{/snippet}
</Toast.Group>
