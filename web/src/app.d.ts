// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		interface PageState {
			/** The open section on the map page (`lon1,lat1,lon2,lat2`), set by shallow routing. */
			section?: string;
		}
		// interface Platform {}
	}
}

export {};
