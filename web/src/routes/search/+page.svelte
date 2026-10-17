<script lang="ts">
	import { Pagination } from '@skeletonlabs/skeleton-svelte';
	import { ArrowLeft, ArrowRight, SparklesIcon } from '@lucide/svelte';
	import { Alert } from '#lib/components/alert/index.ts';
	import BoreholeTable from '#lib/components/borehole/BoreholeTable.svelte';
	import SearchBar from '#lib/components/search/SearchBar.svelte';
	import SearchHelpDrawer from '#lib/components/search/SearchHelpDrawer.svelte';
	import { searchHref } from '#lib/components/search/search-href.ts';
	import { notify } from '#lib/components/toast/index.ts';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let result = $derived(data.result);
	let searched = $derived(data.q.trim() !== '');

	$effect(() => {
		if (data.loadError) notify.fromError(data.loadError, 'Could not search boreholes');
	});

	const examples = ['Schönberg', 'place:Stuttgart', '1950..1960', 'name:KB after:1990'];
	const pageSizes = [10, 20, 50];

	const first = $derived(result.total === 0 ? 0 : (result.page - 1) * result.pageSize + 1);
	const last = $derived(Math.min(result.page * result.pageSize, result.total));

	// Query, page and page size live in the URL so that searches are linkable and the back button
	// works. Paging keeps `exact` and searches the query the hits are for.
	function show(pageNumber: number, pageSize: number) {
		const exact = page.url.searchParams.get('exact') === '1' || !!result.correctedFrom;
		goto(searchHref(result.query, { exact, page: pageNumber, pageSize }));
	}
</script>

<div class="space-y-6">
	<header class="flex items-center justify-between gap-4">
		<h1 class="h1">Search</h1>
		<SearchHelpDrawer />
	</header>

	<div class="py-2">
		<SearchBar query={result.query} onsearch={(q) => goto(searchHref(q))} />
		<p class="mt-3 px-5 text-xs opacity-60">
			Suggestions appear while you type: <kbd class="kbd">↑</kbd> <kbd class="kbd">↓</kbd> to pick
			one, <kbd class="kbd">Enter</kbd> to take it or to search.
		</p>
	</div>

	{#if data.queryError}
		<Alert type="error" title="The query is not valid" message={data.queryError} />
	{:else if !searched}
		<div class="flex flex-wrap items-center gap-2 text-sm">
			<span class="opacity-70">Try:</span>
			{#each examples as example (example)}
				<a class="chip preset-tonal-primary font-mono text-xs" href={searchHref(example)}>
					{example}
				</a>
			{/each}
			<span class="opacity-70">or open <em>Help</em> for everything the search understands.</span>
		</div>
	{:else}
		{#if result.correctedFrom}
			<div class="flex items-start gap-3 card preset-tonal-primary p-4 text-sm">
				<SparklesIcon class="mt-0.5 size-4 shrink-0" />
				<p>
					Showing results for <strong class="font-mono">{result.query}</strong>.
					<span class="block opacity-80">
						Search instead for
						<a class="anchor font-mono" href={searchHref(result.correctedFrom, { exact: true })}>
							{result.correctedFrom}
						</a>
					</span>
				</p>
			</div>
		{/if}

		<BoreholeTable items={result.items.map((hit) => hit.borehole)} />

		{#if result.total > 0}
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
		{/if}
	{/if}
</div>
