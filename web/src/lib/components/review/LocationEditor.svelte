<!--
@component
Coordinates of a borehole as x, y and EPSG code, as written in the document when known (so they
can be compared with the log), else in WGS84 (x = longitude, y = latitude, EPSG 4326). The WGS84
position is shown below. Any system can be typed in; the API converts it. Saved together once the
focus leaves the three fields and only if something changed. Enter moves to the next field, Escape
restores the values.

@param review - Review of the borehole.
-->
<script lang="ts">
	import { untrack } from 'svelte';
	import { CheckIcon } from '@lucide/svelte';
	import { focusNext, type Review } from './review.ts';

	let { review }: { review: Review } = $props();

	const WGS84 = '4326';
	const deg = (value: number, pos: string, neg: string) =>
		`${Math.abs(value).toFixed(5)}° ${value < 0 ? neg : pos}`;

	let location = $derived(review.borehole.location);
	/** x, y and EPSG as stored: as written in the document, else WGS84, else empty. */
	function storedValues(): [string, string, string] {
		const { sourceCoordinates: s, location: l } = review.borehole;
		if (s) return [String(s.x), String(s.y), String(s.epsg)];
		if (l) return [String(l.lon), String(l.lat), WGS84];
		return ['', '', ''];
	}
	// A string, so that the inputs are only reset when the stored coordinates change.
	let stored = $derived(storedValues().join(' '));
	let x = $state('');
	let y = $state('');
	let epsg = $state('');
	$effect(() => {
		void stored;
		untrack(reset);
	});

	let error = $state<string | null>(null);
	let saving = $state(false);
	let saved = $state(false);
	let group = $state<HTMLDivElement>();

	function reset() {
		[x, y, epsg] = storedValues();
		error = null;
	}

	async function commit() {
		const values = [x, y, epsg].map((v) => v.trim().replace(',', '.'));
		const [vx, vy, ve] = values;
		if (values.join() === storedValues().join()) {
			error = null;
			return;
		}
		if (!vx || !vy || !ve) {
			error = 'Give x, y and EPSG code.';
			return;
		}
		if (values.some((v) => Number.isNaN(Number(v)))) {
			error = 'x, y and EPSG must be numbers.';
			return;
		}
		saving = true;
		error = await review.run(
			(s) => s.setLocation(review.borehole.id, { x: Number(vx), y: Number(vy), epsg: Number(ve) }),
			'epsg'
		);
		saving = false;
		if (error) return;
		reset();
		saved = true;
		setTimeout(() => (saved = false), 1500);
	}

	function onkeydown(event: KeyboardEvent & { currentTarget: HTMLInputElement }) {
		if (event.key === 'Enter' && !event.ctrlKey && !event.metaKey) {
			event.preventDefault();
			focusNext(event.currentTarget);
		} else if (event.key === 'Escape') {
			reset();
			event.currentTarget.blur();
		}
	}

	// Saves once the focus has left all three fields, not when moving between them.
	function onfocusout(event: FocusEvent) {
		if (!group?.contains(event.relatedTarget as Node | null)) void commit();
	}

	const inputClass =
		'input h-8 w-full border-transparent bg-transparent px-2 py-1 text-sm hover:border-surface-300-700 focus:border-primary-500';
</script>

<div class="min-w-0">
	<div
		bind:this={group}
		class="relative grid grid-cols-[1fr_1fr_5.5rem] gap-1 {saving ? 'opacity-60' : ''}"
		{onfocusout}
	>
		<input
			type="text"
			inputmode="decimal"
			value={x}
			oninput={(event) => (x = event.currentTarget.value)}
			aria-label="x (easting, or longitude in WGS84)"
			title="x (easting, or longitude in WGS84)"
			placeholder="x"
			data-review-input
			class={inputClass}
			{onkeydown}
		/>
		<input
			type="text"
			inputmode="decimal"
			value={y}
			oninput={(event) => (y = event.currentTarget.value)}
			aria-label="y (northing, or latitude in WGS84)"
			title="y (northing, or latitude in WGS84)"
			placeholder="y"
			data-review-input
			class={inputClass}
			{onkeydown}
		/>
		<input
			type="text"
			inputmode="numeric"
			bind:value={epsg}
			aria-label="EPSG code of x and y"
			title="EPSG code of x and y: 4326 = GPS (WGS84), 25832 = UTM 32N, 31467 = Gauss-Krüger"
			placeholder="e.g. 4326"
			data-review-input
			class="{inputClass} pr-7"
			{onkeydown}
		/>
		{#if saved}
			<CheckIcon
				class="pointer-events-none absolute top-2 right-2 size-4 text-success-600-400"
				aria-label="Saved"
			/>
		{/if}
	</div>
	{#if error}
		<p class="px-2 text-xs text-error-600-400" role="alert">{error}</p>
	{:else if location && epsg.trim() !== WGS84}
		<p class="px-2 text-xs opacity-60">
			= {deg(location.lat, 'N', 'S')}, {deg(location.lon, 'E', 'W')} (GPS)
		</p>
	{/if}
</div>
