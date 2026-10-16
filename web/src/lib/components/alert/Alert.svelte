<!--
@component
A dismissable alert with custom message, title and color, using a rounded look to match the sidebar.

@param message - Message to display in the alert.
@param [title] - Heading of the alert. Defaults to a label for the type.
@param [type] - Type defines the color. Defaults to `info`.
@param [dismissable] - Shows a dismiss button that hides the alert. Defaults to `false`.
@param [onDismiss] - Called after the alert has been dismissed.

@example
```html
<Alert type="success" message="The task has been completed successfully." />
```
@example
```html
<Alert title="Example" message="Hello there" type="error" dismissable />
```
-->

<script lang="ts">
	import { TriangleAlertIcon, XIcon } from '@lucide/svelte';

	interface Props {
		/** Message of the alert */
		message: string;
		/** Title of the alert */
		title?: string;
		/** Type of the alert */
		type?: 'info' | 'success' | 'warning' | 'error';
		/** If true, shows a dismiss button */
		dismissable?: boolean;
		/** Called after the alert has been dismissed */
		onDismiss?: () => void;
	}

	let { message, title, type = 'info', dismissable = false, onDismiss }: Props = $props();

	let dismissed = $state(false);

	/** Border color, default title and icon per type */
	const alertConfig = {
		info: { class: 'preset-outlined-surface-950-50', defaultTitle: 'Info', showIcon: false },
		success: { class: 'preset-outlined-success-500', defaultTitle: 'Success', showIcon: false },
		warning: { class: 'preset-outlined-warning-500', defaultTitle: 'Warning', showIcon: true },
		error: { class: 'preset-outlined-error-500', defaultTitle: 'Error', showIcon: true }
	} as const;

	const config = $derived(alertConfig[type]);

	function dismiss() {
		dismissed = true;
		onDismiss?.();
	}
</script>

{#if !dismissed}
	<div
		role={type === 'error' || type === 'warning' ? 'alert' : 'status'}
		class="card {config.class} flex w-full items-center gap-4 rounded-3xl px-5 py-4"
	>
		{#if config.showIcon}
			<TriangleAlertIcon class="size-5 shrink-0" />
		{/if}
		<div class="min-w-0 flex-1">
			<p class="font-bold">{title || config.defaultTitle}</p>
			<p class="text-xs opacity-60">{message}</p>
		</div>
		{#if dismissable}
			<button
				type="button"
				onclick={dismiss}
				class="btn-icon size-8 shrink-0 rounded-full preset-tonal hover:preset-filled"
				title="Dismiss"
				aria-label="Dismiss"
			>
				<XIcon class="size-4" />
			</button>
		{/if}
	</div>
{/if}
