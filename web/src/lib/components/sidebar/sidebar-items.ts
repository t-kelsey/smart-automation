import {
	ClipboardCheckIcon,
	InfoIcon,
	MapIcon,
	SearchIcon,
	UploadIcon,
	WorkflowIcon,
	Drill
} from '@lucide/svelte';

import type { SidebarItem } from './types';

/** Sidebar content for the start page. Other pages can pass their own `SidebarItem[]`. */
export const defaultSidebarItems: SidebarItem[] = [
	{ type: 'link', label: 'Search', href: '/search', icon: SearchIcon },
	{ type: 'link', label: 'Map', href: '/map', icon: MapIcon, keepMapView: true },
	{ type: 'link', label: 'Boreholes', href: '/borehole', icon: Drill },
	// Opens the next borehole to review; the layout adds the number of unverified ones as badge.
	{ type: 'link', label: 'Review', href: '/review', icon: ClipboardCheckIcon },
	{ type: 'link', label: 'Upload', href: '/upload', icon: UploadIcon },
	{ type: 'link', label: 'Pipelines', href: '/pipeline', icon: WorkflowIcon },
	{ type: 'hr' },
	{ type: 'link', label: 'About', href: '/about', icon: InfoIcon }
];
