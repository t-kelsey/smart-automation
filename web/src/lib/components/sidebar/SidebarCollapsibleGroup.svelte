<script lang="ts">
	import { Collapsible, Navigation } from '@skeletonlabs/skeleton-svelte';
	import { ChevronDownIcon } from '@lucide/svelte';

	import SidebarLink from './SidebarLink.svelte';
	import type { SidebarCollapsibleItem } from './types';

	interface Props {
		item: SidebarCollapsibleItem;
		collapsed?: boolean;
	}

	let { item, collapsed = false }: Props = $props();

	// `defaultOpen` only seeds the initial state.
	// svelte-ignore state_referenced_locally
	let open = $state(item.defaultOpen ?? true);
</script>

<Collapsible {open} onOpenChange={(details) => (open = details.open)} class="items-stretch!">
	<Collapsible.Trigger
		class="flex h-10 w-full items-center gap-3 rounded-2xl px-3 text-left text-sm font-medium hover:preset-tonal {collapsed
			? 'justify-center'
			: ''}"
		title={item.label}
		aria-label={item.label}
	>
		{#if item.icon}
			{@const Icon = item.icon}
			<Icon class="size-4 shrink-0" />
		{/if}
		{#if !collapsed}
			<span class="flex-1 truncate">{item.label}</span>
			<ChevronDownIcon class="size-4 shrink-0 transition-transform {open ? 'rotate-180' : ''}" />
		{/if}
	</Collapsible.Trigger>
	<Collapsible.Content>
		<Navigation.Menu class="flex flex-col gap-1 py-1 {collapsed ? '' : 'pl-4'}">
			{#each item.links as link (link.href)}
				<SidebarLink {link} {collapsed} />
			{/each}
		</Navigation.Menu>
	</Collapsible.Content>
</Collapsible>
