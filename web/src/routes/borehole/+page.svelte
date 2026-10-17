<script lang="ts">
	import { Pagination } from '@skeletonlabs/skeleton-svelte';
	import { ArrowLeft, ArrowRight } from '@lucide/svelte';
	import BoreholeTable from '#lib/components/borehole/BoreholeTable.svelte';
	import { goto } from '$app/navigation';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let result = $derived(data.result);

	const pageSizes = [10, 20, 50];

	const first = $derived(result.total === 0 ? 0 : (result.page - 1) * result.pageSize + 1);
	const last = $derived(Math.min(result.page * result.pageSize, result.total));

	// Page and page size live in the URL so that pages are linkable and the back button works.
	function show(page: number, pageSize: number) {
		const query = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- only the query string changes
		goto(`?${query}`, { reset: false });
	}
</script>

<div class="space-y-4">
	<h1 class="h1">Boreholes</h1>

	<BoreholeTable items={result.items} />

	<footer class="flex flex-wrap items-center justify-between gap-4">
		<div class="flex items-center gap-4 text-sm">
			<label class="flex items-center gap-2">
				Rows per page
				<select
					class="select w-auto"
					value={result.pageSize}
					onchange={(e) => show(1, Number(e.currentTarget.value))}
				>
					{#each pageSizes as size (size)}
						<option value={size}>{size}</option>
					{/each}
				</select>
			</label>
			<span class="opacity-70">{first}–{last} of {result.total}</span>
		</div>

		<Pagination
			count={result.total}
			pageSize={result.pageSize}
			page={result.page}
			onPageChange={(e) => show(e.page, result.pageSize)}
		>
			<Pagination.PrevTrigger>
				<ArrowLeft class="size-4" />
			</Pagination.PrevTrigger>
			<Pagination.Context>
				{#snippet children(pagination)}
					{#each pagination().pages as p, i (p.type === 'page' ? p.value : `ellipsis-${i}`)}
						{#if p.type === 'page'}
							<Pagination.Item {...p}>{p.value}</Pagination.Item>
						{:else}
							<Pagination.Ellipsis index={i}>&#8230;</Pagination.Ellipsis>
						{/if}
					{/each}
				{/snippet}
			</Pagination.Context>
			<Pagination.NextTrigger>
				<ArrowRight class="size-4" />
			</Pagination.NextTrigger>
		</Pagination>
	</footer>
</div>
