<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import { Sidebar, defaultSidebarItems } from '#lib/components/sidebar/index.ts';
	import { Toaster } from '#lib/components/toast/index.ts';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	let items = $derived(
		defaultSidebarItems.map((item) =>
			item.type === 'link' && item.href === '/review' ? { ...item, badge: data.reviewCount } : item
		)
	);

	// TODO: replace with the authenticated user.
	const user = { name: 'Jane Doe', subtitle: 'Geologist' };
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="flex h-screen">
	<Sidebar {items} {user} />
	<main class="min-w-0 flex-1 overflow-y-auto p-6">
		{@render children()}
	</main>
</div>
<Toaster />
