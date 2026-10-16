<!-- Must live inside a <Navigation> root — every Navigation.* part reads that context. -->
<script lang="ts">
	import { Navigation } from '@skeletonlabs/skeleton-svelte';

	import SidebarCollapsibleGroup from './SidebarCollapsibleGroup.svelte';
	import SidebarLink from './SidebarLink.svelte';
	import type { SidebarItem, SidebarLinkItem } from './types';

	interface Props {
		items: SidebarItem[];
		collapsed?: boolean;
	}

	let { items, collapsed = false }: Props = $props();

	// Adjacent links share one Navigation.Menu (roving-tabindex context).
	type Block = { kind: 'links'; links: SidebarLinkItem[] } | { kind: 'item'; item: SidebarItem };

	let blocks = $derived(
		items.reduce<Block[]>((acc, item) => {
			const last = acc[acc.length - 1];
			if (item.type === 'link') {
				if (last?.kind === 'links') {
					last.links.push(item);
				} else {
					acc.push({ kind: 'links', links: [item] });
				}
			} else {
				acc.push({ kind: 'item', item });
			}
			return acc;
		}, [])
	);
</script>

{#each blocks as block, index (index)}
	{#if block.kind === 'links'}
		<Navigation.Group>
			<Navigation.Menu class="flex flex-col gap-1">
				{#each block.links as link (link.href)}
					<SidebarLink {link} {collapsed} />
				{/each}
			</Navigation.Menu>
		</Navigation.Group>
	{:else if block.item.type === 'hr'}
		<hr class="my-1 hr" />
	{:else if block.item.type === 'title'}
		<Navigation.Label
			class="h-5 px-3 text-xs font-semibold tracking-wide text-surface-500 uppercase"
		>
			{#if !collapsed}{block.item.label}{/if}
		</Navigation.Label>
	{:else if block.item.type === 'collapsible'}
		<SidebarCollapsibleGroup item={block.item} {collapsed} />
	{/if}
{/each}
