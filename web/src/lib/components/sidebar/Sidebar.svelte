<script lang="ts">
	import { Avatar, Menu, Navigation, Portal } from '@skeletonlabs/skeleton-svelte';
	import {
		ChevronsUpDownIcon,
		LogOutIcon,
		PanelLeftCloseIcon,
		PanelLeftIcon,
		SettingsIcon,
		UserIcon
	} from '@lucide/svelte';
	import { resolve } from '$app/paths';
	import type { HTMLAnchorAttributes, HTMLButtonAttributes } from 'svelte/elements';

	import SidebarNav from './SidebarNav.svelte';
	import type { SidebarItem, SidebarMenuAction, SidebarUser } from './types';

	interface Props {
		/** Content of the sidebar; pass different items depending on the page. */
		items: SidebarItem[];
		user: SidebarUser;
		/** Entries of the user menu opened from the bottom of the sidebar. */
		userMenu?: SidebarMenuAction[];
		title?: string;
	}

	let {
		items,
		user,
		userMenu = [
			{ label: 'Profile', icon: UserIcon, href: '/profile' },
			{ label: 'Settings', icon: SettingsIcon, href: '/settings' },
			{ label: 'Log out', icon: LogOutIcon }
		],
		title = 'BEM'
	}: Props = $props();

	let collapsed = $state(false);

	let initials = $derived(
		user.name
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0].toUpperCase())
			.join('')
	);

	const itemClass =
		'flex w-full items-center justify-start gap-2 rounded-xl px-3 py-2 text-sm hover:preset-tonal';
</script>

<Navigation
	layout="sidebar"
	class="relative z-10 m-3 flex h-[calc(100%-1.5rem)] shrink-0 flex-col gap-2! rounded-3xl border border-surface-200-800 bg-surface-50-950 p-2! shadow-lg transition-[width] duration-200 {collapsed
		? 'w-18'
		: 'w-64'}"
>
	<Navigation.Header class="flex h-12 items-center {collapsed ? 'justify-center' : 'px-2'}">
		<a
			href={resolve('/')}
			class="truncate rounded-xl font-bold {collapsed
				? 'text-base tracking-tighter'
				: 'px-1 text-xl tracking-wide'}"
			{title}
			aria-label="{title} – Home">{title}</a
		>
	</Navigation.Header>

	<Navigation.Content class="flex min-h-0 w-full flex-1 flex-col gap-1 overflow-y-auto">
		<SidebarNav {items} {collapsed} />
	</Navigation.Content>

	<button
		type="button"
		onclick={() => (collapsed = !collapsed)}
		class="flex h-10 w-full items-center gap-3 rounded-2xl px-3 hover:preset-tonal {collapsed
			? 'justify-center'
			: ''}"
		title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
		aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
		aria-expanded={!collapsed}
	>
		{#if collapsed}
			<PanelLeftIcon class="size-4" />
		{:else}
			<PanelLeftCloseIcon class="size-4 shrink-0" />
			<span class="flex-1 text-left text-sm opacity-60">Collapse</span>
		{/if}
	</button>

	<Navigation.Footer class="border-t border-surface-200-800 pt-2">
		<Menu positioning={{ placement: 'top-start' }}>
			<Menu.Trigger
				class="flex h-14 w-full items-center gap-3 rounded-2xl px-2 text-left hover:preset-tonal {collapsed
					? 'justify-center'
					: ''}"
			>
				<Avatar class="size-9 shrink-0">
					{#if user.avatarSrc}<Avatar.Image src={user.avatarSrc} alt={user.name} />{/if}
					<Avatar.Fallback class="preset-filled-primary-500 text-xs">{initials}</Avatar.Fallback>
				</Avatar>
				{#if !collapsed}
					<span class="min-w-0 flex-1">
						<span class="block truncate text-sm font-medium">{user.name}</span>
						{#if user.subtitle}
							<span class="block truncate text-xs opacity-60">{user.subtitle}</span>
						{/if}
					</span>
					<ChevronsUpDownIcon class="size-4 shrink-0 opacity-60" />
				{/if}
			</Menu.Trigger>
			<Portal>
				<Menu.Positioner>
					<Menu.Content class="w-56 card rounded-2xl bg-surface-100-900 p-2 shadow-xl">
						{#each userMenu as action (action.label)}
							<Menu.Item value={action.label} onclick={action.onSelect}>
								{#snippet element(attributes)}
									{#if action.href}
										<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- hrefs come from caller config -->
										<a {...attributes as HTMLAnchorAttributes} href={action.href} class={itemClass}>
											{#if action.icon}{@const Icon = action.icon}<Icon class="size-4" />{/if}
											<Menu.ItemText>{action.label}</Menu.ItemText>
										</a>
									{:else}
										<button {...attributes as HTMLButtonAttributes} type="button" class={itemClass}>
											{#if action.icon}{@const Icon = action.icon}<Icon class="size-4" />{/if}
											<Menu.ItemText>{action.label}</Menu.ItemText>
										</button>
									{/if}
								{/snippet}
							</Menu.Item>
						{/each}
					</Menu.Content>
				</Menu.Positioner>
			</Portal>
		</Menu>
	</Navigation.Footer>
</Navigation>
