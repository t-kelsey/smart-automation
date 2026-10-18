<script lang="ts">
	import { Avatar, Carousel } from '@skeletonlabs/skeleton-svelte';
	import { ChevronLeftIcon, ChevronRightIcon } from '@lucide/svelte';
	import Mermaid from '#lib/components/about/Mermaid.svelte';

	let innerWidth = $state(1024);

	/** First letters of the first and last word, or the first two letters of a single name. */
	function initials(name: string): string {
		const words = name.trim().split(/\s+/);
		return (words.length > 1 ? words[0][0] + words.at(-1)![0] : name.slice(0, 2)).toUpperCase();
	}

	const challengeUrl =
		'https://hackathon.badencampus.de/en/challenges/66f8c41f-b62a-4a84-a356-79546bc9c68b';

	const team = [
		{
			name: 'Julia',
			tags: ['API', 'Database', 'Elixir'],
			task: 'Designed the PostGIS data model and built the Phoenix API that stores, georeferences and serves the boreholes.'
		},
		{
			name: 'Tyler',
			tags: ['BEM', 'Python', 'Data Processing'],
			task: 'Sorts the incoming files and translates logs into DIN 4023 terms with a glossary and local translation models.'
		},
		{
			name: 'Kai',
			tags: ['BEM', 'Python', 'OCR'],
			task: 'Turns scans and PDFs into markdown with table-aware OCR and a vision-language model for hard pages.'
		},
		{
			name: 'Manuel',
			tags: ['BEM', 'Python', 'Data Extraction'],
			task: 'Extracts metadata, depth intervals, stratigraphy and lithology from the text into the borehole format.'
		},
		{
			name: 'Kasimir',
			tags: ['Architecture', 'UI', 'Svelte'],
			task: 'Designed the system architecture and how the database, API, BEM pipeline and UI fit together, and built the UI.'
		}
	];

	const infrastructure = [
		{
			name: 'Database',
			text: 'PostgreSQL with PostGIS. Boreholes, layers, documents and pipeline runs are stored with a WGS84 point, so the map can query by bounding box. Coordinates in local systems (for example Gauss-Krüger) are reprojected to WGS84 in the database, and the raw extraction of every stage is kept next to the standardised values.'
		},
		{
			name: 'API',
			text: 'A Phoenix (Elixir) JSON API. It stores the uploaded documents, starts and stops pipeline runs, tracks every stage, and validates and georeferences the boreholes the pipeline sends back. It also serves paged borehole lists, a search with its own query language and autocompletion, and the source files. It owns the data model, and it is the only thing that touches the database and the file storage.'
		},
		{
			name: 'UI',
			text: 'A SvelteKit app with an upload and pipeline monitor, a clustered MapLibre map, search by name, place and date with autocompletion, and borehole profile columns drawn after DIN 4023 next to the source document. It talks only to the API, through a service and repository layer.'
		},
		{
			name: 'BEM',
			text: 'The borehole extraction pipeline in Python, run as a small HTTP service. It gets a document from the API, runs four Claude stages over it and posts the finished boreholes back. Like the UI, it only uses the API. The AI backend is pluggable.'
		}
	];

	const bemSteps = [
		{
			name: 'Filter',
			text: 'A report holds far more than borehole logs. This stage classifies the pages in chunks and keeps only the real log pages. Default: Haiku, high effort.'
		},
		{
			name: 'Split',
			text: 'One file can hold several boreholes, so the filtered pages are grouped and cut into one PDF per borehole. Default: Haiku, medium effort.'
		},
		{
			name: 'Extract',
			text: 'Claude reads each borehole PDF, including colours and hatch patterns, and captures all data in the original wording and language: metadata, elevation, depth intervals, stratigraphy and lithology. It also checks that the file holds exactly one borehole. Default: Sonnet, high effort.'
		},
		{
			name: 'Transform',
			text: 'The raw extraction is translated into English and shaped like the database tables. Petrography is mapped to the terms of DIN 4023, and a borehole with a layer that cannot be mapped is not uploaded. Default: Haiku, high effort.'
		}
	];

	const runSteps = [
		'Files are queued in the browser, nothing is stored yet. The user picks a model and effort per stage, then starts the extraction.',
		'The UI uploads each file to the API, which stores it and creates a pipeline run.',
		'The API tells BEM to execute the run. BEM answers at once and queues the job. A queued or running run can be stopped from the UI.',
		'A BEM worker downloads the document from the API and runs the four stages.',
		'After every stage, BEM uploads its output to the API, so the UI can show live progress.',
		'Each valid borehole is posted to the API and linked to its source document. The run ends as completed, failed or stopped.'
	];

	const diagram = `flowchart LR
    user(["User"])
    subgraph web["SvelteKit UI"]
        ui["Upload, pipeline,<br/>map, search, profiles"]
    end
    subgraph api["Phoenix API"]
        ctx["Documents, runs,<br/>stages, boreholes"]
    end
    db[("PostgreSQL<br/>+ PostGIS")]
    fs[("Document storage")]
    subgraph bem["BEM (Python)"]
        direction LR
        filter["1 Filter"] --> split["2 Split"] --> extract["3 Extract"] --> transform["4 Transform<br/>DIN 4023"]
    end
    claude{{"Claude models"}}
    user <--> ui
    ui <-->|"/api"| ctx
    ctx <--> db
    ctx <--> fs
    ctx -->|"start run"| filter
    bem -->|"download document,<br/>stage results, boreholes"| ctx
    bem <--> claude`;
</script>

<svelte:head>
	<title>About · Borehole Atlas</title>
</svelte:head>

<svelte:window bind:innerWidth />

<div class="mx-auto max-w-4xl space-y-12">
	<header class="space-y-2">
		<h1 class="h1">About</h1>
		<p class="text-lg opacity-80">
			A geodatabase that turns legacy borehole logs into structured, searchable data.
		</p>
	</header>

	<section class="space-y-4">
		<h2 class="h2">The hackathon and the challenge</h2>
		<p>
			This project was built at the Black Forest Hackathon 2026 for the
			<a class="anchor" href={challengeUrl} target="_blank" rel="noreferrer">
				Herrenknecht challenge
			</a>
			on smart automation of borehole data.
		</p>
		<p>
			Boreholes are usually the only accurate description of the subsurface, and they drive the
			design of tunnel boring machines (TBM). Many of them exist only as old logs: unstructured,
			multilingual, formatted differently by every company and decade, and ranging from scanned
			paper to native digital files. Much of the meaning sits in colours and hatch patterns.
		</p>
		<p>The challenge is to automate the whole path from a log to a searchable base:</p>
		<ul class="list-inside list-disc space-y-1">
			<li>read scans and PDFs (OCR),</li>
			<li>extract elevation, depth intervals, stratigraphy and lithology,</li>
			<li>collect metadata such as location and date,</li>
			<li>show the boreholes on a map and as profiles,</li>
			<li>make the right log quick to find,</li>
		</ul>
		<p>and to do it securely, since the source data is confidential.</p>
	</section>

	<section class="space-y-4">
		<h2 class="h2">Team</h2>
		<Carousel
			slideCount={team.length}
			slidesPerPage={innerWidth >= 1024 ? 3 : innerWidth >= 640 ? 2 : 1}
			spacing="16px"
			allowMouseDrag
		>
			<Carousel.Control class="flex items-center gap-3">
				<Carousel.PrevTrigger
					class="btn-icon shrink-0 preset-tonal"
					aria-label="Previous team member"
				>
					<ChevronLeftIcon class="size-5" />
				</Carousel.PrevTrigger>
				<Carousel.ItemGroup class="min-w-0 flex-1 py-1">
					{#each team as member, i (member.name)}
						<Carousel.Item index={i}>
							<div
								class="flex h-full flex-col items-center gap-3 card border border-surface-200-800 preset-filled-surface-100-900 p-6 text-center shadow-md"
							>
								<Avatar class="size-24">
									<Avatar.Fallback class="preset-filled-primary-500 text-3xl font-semibold">
										{initials(member.name)}
									</Avatar.Fallback>
								</Avatar>
								<p class="h5">{member.name}</p>
								<ul class="flex flex-wrap justify-center gap-2" aria-label="Focus areas">
									{#each member.tags as tag (tag)}
										<li class="chip preset-tonal-primary">{tag}</li>
									{/each}
								</ul>
								<p class="text-sm">{member.task}</p>
							</div>
						</Carousel.Item>
					{/each}
				</Carousel.ItemGroup>
				<Carousel.NextTrigger class="btn-icon shrink-0 preset-tonal" aria-label="Next team member">
					<ChevronRightIcon class="size-5" />
				</Carousel.NextTrigger>
			</Carousel.Control>
			<Carousel.IndicatorGroup class="mt-4 flex justify-center gap-2">
				{#each team as member, i (member.name)}
					<Carousel.Indicator
						index={i}
						class="size-2.5 rounded-full bg-surface-300-700 transition-colors data-current:bg-primary-500"
						aria-label="Show {member.name}"
					/>
				{/each}
			</Carousel.IndicatorGroup>
		</Carousel>
	</section>

	<section class="space-y-6">
		<h2 class="h2">How it works</h2>

		<div class="space-y-4">
			<h3 class="h3">Infrastructure</h3>
			<p>
				Four parts work together, from the raw file to the map. They run as separate services,
				started together with Docker Compose.
			</p>
			<dl class="grid gap-3 sm:grid-cols-2">
				{#each infrastructure as part (part.name)}
					<div class="card preset-tonal-surface p-4">
						<dt class="h5">{part.name}</dt>
						<dd class="mt-1 text-sm opacity-80">{part.text}</dd>
					</div>
				{/each}
			</dl>
		</div>

		<div class="space-y-4">
			<h3 class="h3">How the parts connect</h3>
			<div class="card preset-outlined-surface-200-800 p-4">
				<Mermaid code={diagram} label="Architecture of UI, API, database and BEM pipeline" />
			</div>
		</div>

		<div class="space-y-4">
			<h3 class="h3">From upload to borehole</h3>
			<ol class="list-inside list-decimal space-y-1">
				{#each runSteps as step (step)}
					<li>{step}</li>
				{/each}
			</ol>
		</div>

		<div class="space-y-4">
			<h3 class="h3">BEM in detail</h3>
			<p>
				BEM runs four stages on the Claude CLI, each with its own model and effort. Each stage is
				small and can be tuned or swapped on its own. The UI shows every stage output, and the run
				report lists time, tokens and cost per stage. Source documents stay linked to their
				boreholes. Note that the pages are sent to Claude, so confidential files need an approved
				setup.
			</p>
			<ol class="space-y-3">
				{#each bemSteps as step, i (step.name)}
					<li class="flex gap-4 card preset-tonal-surface p-4">
						<span class="h3 opacity-60">{i + 1}</span>
						<div>
							<p class="h5">{step.name}</p>
							<p class="mt-1 text-sm opacity-80">{step.text}</p>
						</div>
					</li>
				{/each}
			</ol>
		</div>

		<div class="space-y-4">
			<h3 class="h3">Limitations</h3>
			<ul class="list-inside list-disc space-y-1">
				<li>
					This is a research prototype. There is no authentication: anyone who can reach the API can
					read, create and delete data, including source documents.
				</li>
				<li>There is no accuracy evaluation against ground truth yet.</li>
				<li>
					The transform stage uses a small model for translation and unit conversion, so check the
					validation issues and metadata notes of each borehole.
				</li>
				<li>The pipeline queue is in memory, so a restart of BEM loses queued runs.</li>
			</ul>
		</div>
	</section>
</div>
