import type { Component } from 'svelte';
import type { LucideProps } from '@lucide/svelte';

type LucideIcon = Component<LucideProps>;

export interface SidebarLinkItem {
	type: 'link';
	label: string;
	href: string;
	icon?: LucideIcon;
}

export interface SidebarTitleItem {
	type: 'title';
	label: string;
}

export interface SidebarDividerItem {
	type: 'hr';
}

export interface SidebarCollapsibleItem {
	type: 'collapsible';
	label: string;
	icon?: LucideIcon;
	links: SidebarLinkItem[];
	defaultOpen?: boolean;
}

export type SidebarItem =
	SidebarTitleItem | SidebarDividerItem | SidebarLinkItem | SidebarCollapsibleItem;

export interface SidebarUser {
	name: string;
	/** Secondary line below the name, e.g. role or email. */
	subtitle?: string;
	avatarSrc?: string;
}

export interface SidebarMenuAction {
	label: string;
	icon?: LucideIcon;
	href?: string;
	onSelect?: () => void;
}
