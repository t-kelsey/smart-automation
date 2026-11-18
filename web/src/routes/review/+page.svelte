<script lang="ts">
	import { resolve } from '$app/paths';
	import { PartyPopperIcon } from '@lucide/svelte';
</script>

<svelte:head>
	<title>Review</title>
</svelte:head>

<div class="flex h-full flex-col items-center justify-center gap-4 text-center">
	<PartyPopperIcon class="size-12 text-success-500" />
	<h1 class="h2">All checked 🎉</h1>
	<p class="opacity-70">Every borehole is verified.</p>
	<a href={resolve('/borehole')} class="btn preset-tonal">Show all boreholes</a>
</div>
