import { mdsvex } from 'mdsvex';
import { enhancedImages } from '@sveltejs/enhanced-img';
import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-auto';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	// maplibre-gl starts its GeoJSON worker via new URL(..., import.meta.url), which breaks when the
	// dev server pre-bundles it ("Worker failed to load") and the circle layer then stays empty.
	optimizeDeps: { exclude: ['maplibre-gl'] },
	server: {
		// ADR-0022: the DIN 4023 standard file lives outside web/
		fs: { allow: ['..'] },
		// Dev proxy for PUBLIC_DATA_SOURCE=api with the default PUBLIC_API_URL=/api
		proxy: { '/api': 'http://localhost:4000' }
	},
	plugins: [
		enhancedImages(),
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// adapter-auto only supports some environments, see https://svelte.dev/docs/kit/adapter-auto for a list.
			// If your environment is not supported, or you settled on a specific environment, switch out the adapter.
			// See https://svelte.dev/docs/kit/adapters for more information about adapters.
			adapter: adapter(),
			preprocess: [mdsvex({ extensions: ['.svx', '.md'] })],
			extensions: ['.svelte', '.svx', '.md']
		})
	]
});
