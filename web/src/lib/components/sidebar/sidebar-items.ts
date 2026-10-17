import { InfoIcon, MapIcon, SearchIcon, ListIcon } from '@lucide/svelte';

import type { SidebarItem } from './types';

/** Sidebar content for the start page. Other pages can pass their own `SidebarItem[]`. */
export const defaultSidebarItems: SidebarItem[] = [
	{ type: 'link', label: 'Search', href: '/search', icon: SearchIcon },
	{ type: 'link', label: 'Map', href: '/map', icon: MapIcon },
	{ type: 'link', label: 'List', href: '/borehole', icon: ListIcon },
	{ type: 'hr' },
	{ type: 'link', label: 'About', href: '/about', icon: InfoIcon }
];
