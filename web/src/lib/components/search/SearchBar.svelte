<!--
@component
Rounded search bar with completions while typing (ADR-0043). The API completes the term at the end
of the query by trigram (q-gram) matching on names and places, so typos still complete. Arrow keys
pick a completion, Enter takes it; Enter without a picked completion searches.

@param query - The current query; the input follows it when it changes (e.g. after navigating).
@param onsearch - Called with the query when the user searches.
-->
<script lang="ts">
	import { Combobox, Portal, useListCollection } from '@skeletonlabs/skeleton-svelte';
	import { Drill, KeyRoundIcon, MapPinIcon, SearchIcon } from '@lucide/svelte';
	import type { SearchCompletion } from '#lib/domain/borehole.ts';
	import { createServices, type Services } from '#lib/services/index.ts';

	interface Props {
		query: string;
		onsearch: (query: string) => void;
	}

	let { query, onsearch }: Props = $props();

	let text = $derived(query);
	let completions = $state<SearchCompletion[]>([]);
	let open = $state(false);

	const collection = $derived(
		useListCollection({
			items: completions,
			itemToValue: (item) => item.query,
			itemToString: (item) => item.query
		})
	);

	const kinds = {
		key: { label: 'Key', icon: KeyRoundIcon },
		name: { label: 'Name', icon: Drill },
		place: { label: 'Place', icon: MapPinIcon }
	} as const;

	let services: Promise<Services> | undefined;
	let timer: ReturnType<typeof setTimeout> | undefined;
	let request = 0;

	// Waits for a short pause in typing, and drops answers that arrive after a newer request.
	function suggest(value: string) {
		clearTimeout(timer);
		const current = ++request;
		timer = setTimeout(async () => {
			try {
				services ??= createServices({ fetch });
				const found = await (await services).search.complete(value);
				if (current !== request) return;
				completions = found;
				open = found.length > 0;
			} catch {
				// Completions are a convenience; typing and searching work without them.
				if (current === request) open = false;
			}
		}, 120);
	}

	function submit(event: SubmitEvent) {
		event.preventDefault();
		clearTimeout(timer);
		request++;
		open = false;
		onsearch(text);
	}
</script>

<!-- Without JavaScript the GET form still searches. -->
<form method="GET" role="search" onsubmit={submit}>
	<Combobox
		{collection}
		inputValue={text}
		onInputValueChange={(details) => {
			text = details.inputValue;
			if (details.reason === 'input-change') suggest(details.inputValue);
		}}
		value={[]}
		onSelect={(details) => {
			text = details.itemValue;
			open = false;
		}}
		{open}
		onOpenChange={(details) => (open = details.open && completions.length > 0)}
		inputBehavior="none"
		selectionBehavior="preserve"
		allowCustomValue
		openOnClick={false}
		openOnKeyPress={false}
		positioning={{ sameWidth: true, gutter: 8 }}
	>
		<Combobox.Control
			class="flex items-center gap-3 rounded-full border border-surface-200-800 bg-surface-50-950 py-2 pr-2 pl-5 shadow-sm transition-colors focus-within:border-primary-500"
		>
			<SearchIcon class="size-5 shrink-0 opacity-60" />
			<Combobox.Input
				name="q"
				class="min-w-0 flex-1 border-0 bg-transparent px-0 py-2 text-base ring-0 placeholder:opacity-60 focus:ring-0 focus:outline-none"
				placeholder="Name, place or date, e.g. place:Stuttgart 1950..1960"
				aria-label="Search boreholes"
				autocomplete="off"
				spellcheck="false"
			/>
			<button type="submit" class="btn rounded-full preset-filled-primary-500 px-6">Search</button>
		</Combobox.Control>
		<Portal>
			<Combobox.Positioner class="z-50">
				<Combobox.Content
					class="max-h-80 overflow-y-auto rounded-3xl border border-surface-200-800 bg-surface-50-950 p-2 shadow-xl"
				>
					{#each completions as item (item.query)}
						{@const kind = kinds[item.kind]}
						<Combobox.Item
							{item}
							class="flex cursor-pointer items-center gap-3 rounded-2xl px-3 py-2 text-sm data-highlighted:preset-tonal"
						>
							<kind.icon class="size-4 shrink-0 opacity-60" />
							<Combobox.ItemText class="min-w-0 flex-1 truncate">{item.value}</Combobox.ItemText>
							<span class="badge preset-tonal-surface text-xs">{kind.label}</span>
						</Combobox.Item>
					{/each}
				</Combobox.Content>
			</Combobox.Positioner>
		</Portal>
	</Combobox>
</form>
