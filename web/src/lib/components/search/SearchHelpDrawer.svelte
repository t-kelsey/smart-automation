<!--
@component
Help button and drawer explaining the search query language (ADR-0042). Examples are links that
run the search and close the drawer.
-->
<script lang="ts">
	import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';
	import { CircleHelpIcon, XIcon } from '@lucide/svelte';
	import { searchHref } from './search-href.ts';

	interface Rule {
		syntax: string;
		meaning: string;
		example: string;
	}

	let open = $state(false);

	const textRules: Rule[] = [
		{
			syntax: 'word',
			meaning: 'Name, external id or place contains the word.',
			example: 'Schönberg'
		},
		{
			syntax: '"a phrase"',
			meaning: 'Contains the exact text, spaces included.',
			example: '"B 1/59"'
		},
		{ syntax: 'name:word', meaning: 'Only the name or external id. Short: n:', example: 'name:KB' },
		{
			syntax: 'place:word',
			meaning: 'Only the place. Also location: or loc:',
			example: 'place:Stuttgart'
		}
	];

	const dateRules: Rule[] = [
		{ syntax: '1959', meaning: 'Drilled in that year.', example: '1959' },
		{ syntax: 'date:1959-06', meaning: 'In that month.', example: 'date:1959-06' },
		{
			syntax: 'date:1959-06-12',
			meaning: 'On that day. 12.06.1959 works too.',
			example: 'date:12.06.1959'
		},
		{ syntax: '1950..1960', meaning: 'From 1950 up to and including 1960.', example: '1950..1960' },
		{
			syntax: 'date:1990..',
			meaning: 'In 1990 or later. ..1960 for up to 1960.',
			example: 'date:1990..'
		},
		{
			syntax: 'date:>1990',
			meaning: 'After 1990. Also >=, < and <=.',
			example: 'date:>=1990'
		},
		{
			syntax: 'after:1990',
			meaning: 'Same as date:>1990; before: for date:<',
			example: 'after:1980 before:2000'
		}
	];

	const combineRules: Rule[] = [
		{
			syntax: 'a b',
			meaning: 'Spaces: every term must match.',
			example: 'place:Stuttgart 1950..1960'
		},
		{ syntax: 'a,b', meaning: 'Commas: either value.', example: 'place:Bern,Basel' },
		{ syntax: '-term', meaning: 'Minus: must not match.', example: 'Schönberg -place:Stuttgart' }
	];
</script>

{#snippet rules(list: Rule[])}
	<ul class="space-y-3 text-sm">
		{#each list as rule (rule.syntax)}
			<li class="space-y-1">
				<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
					<code class="code">{rule.syntax}</code>
					<span class="opacity-80">{rule.meaning}</span>
				</div>
				<a
					class="chip preset-tonal-primary font-mono text-xs"
					href={searchHref(rule.example)}
					onclick={() => (open = false)}
				>
					Try: {rule.example}
				</a>
			</li>
		{/each}
	</ul>
{/snippet}

<Dialog {open} onOpenChange={(details) => (open = details.open)}>
	<Dialog.Trigger class="btn preset-tonal">
		<CircleHelpIcon class="size-4" />
		Help
	</Dialog.Trigger>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-40 bg-surface-950/50" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex justify-end">
			<Dialog.Content
				class="flex h-full w-full max-w-md flex-col gap-6 overflow-y-auto bg-surface-50-950 p-6 shadow-xl"
			>
				<header class="flex items-start justify-between gap-4">
					<div>
						<Dialog.Title class="h4">Help</Dialog.Title>
						<Dialog.Description class="text-sm opacity-70">
							How to search boreholes by name, place and date.
						</Dialog.Description>
					</div>
					<Dialog.CloseTrigger class="btn-icon preset-tonal" aria-label="Close help">
						<XIcon class="size-4" />
					</Dialog.CloseTrigger>
				</header>

				<p class="text-sm">
					Type one or more terms. Upper and lower case do not matter, and a word also matches part
					of a longer word: <em>stutt</em> finds <em>Stuttgart</em>. Click an example to try it.
				</p>

				<section class="space-y-3">
					<h5 class="h6">Names and places</h5>
					{@render rules(textRules)}
				</section>

				<section class="space-y-3">
					<h5 class="h6">Dates</h5>
					<p class="text-sm opacity-80">
						Dates are the drilling date. A bare year, date or range is always a date; put it in
						quotes (<code class="code">"1959"</code>) to find it in names instead.
					</p>
					{@render rules(dateRules)}
				</section>

				<section class="space-y-3">
					<h5 class="h6">Combining terms</h5>
					{@render rules(combineRules)}
				</section>

				<section class="space-y-2">
					<h5 class="h6">Suggestions while typing</h5>
					<ul class="list-disc space-y-1 pl-5 text-sm">
						<li>
							From the second letter on, the word you are typing is completed with matching names
							and places, and with keys (<em>pla</em> suggests <em>place:</em>). After
							<em>place:</em> only places are suggested, after <em>name:</em> only names.
						</li>
						<li>A missing or extra letter is fine: <em>Stutgart</em> still suggests Stuttgart.</li>
						<li>
							<kbd class="kbd">↑</kbd> <kbd class="kbd">↓</kbd> pick a suggestion,
							<kbd class="kbd">Enter</kbd> takes it, <kbd class="kbd">Esc</kbd> closes the list.
						</li>
					</ul>
				</section>

				<section class="space-y-2">
					<h5 class="h6">Autocorrection</h5>
					<ul class="list-disc space-y-1 pl-5 text-sm">
						<li>
							If nothing is found, misspelt words are replaced by the most similar word in the names
							and places, and misspelt keys by the closest key (<em>plase:</em> becomes
							<em>place:</em>).
						</li>
						<li>
							The results then show what was searched instead. Use <em>Search instead for …</em> to go
							back to what you typed.
						</li>
						<li>
							Words in quotes, words after a minus and words shorter than 3 letters stay as typed.
						</li>
					</ul>
				</section>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog>
