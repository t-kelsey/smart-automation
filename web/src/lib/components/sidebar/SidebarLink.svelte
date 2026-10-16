<script lang="ts">
	import { Navigation } from '@skeletonlabs/skeleton-svelte';
	import { page } from '$app/state';

	import type { SidebarLinkItem } from './types';

	interface Props {
		link: SidebarLinkItem;
		collapsed?: boolean;
	}

	let { link, collapsed = false }: Props = $props();

	let active = $derived(
		page.url.pathname === link.href || page.url.pathname.startsWith(`${link.href}/`)
	);
</script>

<Navigation.TriggerAnchor
	href={link.href}
	title={link.label}
	aria-label={link.label}
	aria-current={active ? 'page' : undefined}
	class="flex h-10 items-center gap-3 rounded-2xl px-3 text-sm transition-colors {active
		? 'preset-filled-primary-500 font-medium'
		: 'hover:preset-tonal'} {collapsed ? 'justify-center' : ''}"
>
	{#if link.icon}
		{@const Icon = link.icon}
		<Icon class="size-4 shrink-0" />
	{:else}
		<span class="size-1.5 shrink-0 rounded-full bg-current opacity-50"></span>
	{/if}
	{#if !collapsed}
		<Navigation.TriggerText class="min-w-0 flex-1 truncate">{link.label}</Navigation.TriggerText>
	{/if}
</Navigation.TriggerAnchor>
