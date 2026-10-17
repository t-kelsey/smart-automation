import { notify } from '#lib/components/toast/index.ts';
import type { HandleClientError } from '@sveltejs/kit/hooks';

// Failed loads (e.g. API unreachable) also surface as a toast, next to SvelteKit's error page.
// Expected errors such as a 404 are shown by the error page only.
export const handleError: HandleClientError = ({ kind, error }) => {
	if (kind === 'unknown') notify.fromError(error);
};
