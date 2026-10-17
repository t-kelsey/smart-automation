import type { Handle } from '@sveltejs/kit/hooks';
import { env } from 'node:process';

// In the Docker deployment the browser reaches the API through the UI origin (PUBLIC_API_URL=/api),
// so forward /api/* to the API container. In `pnpm dev` the Vite proxy handles this before it gets here.
const apiInternalUrl = env.API_INTERNAL_URL ?? 'http://localhost:4000';

export const handle: Handle = async ({ event, resolve }) => {
	if (event.url.pathname === '/api' || event.url.pathname.startsWith('/api/')) {
		const target = new URL(event.url.pathname + event.url.search, apiInternalUrl);
		const headers = new Headers(event.request.headers);
		headers.delete('host');
		const response = await fetch(target, {
			method: event.request.method,
			headers,
			body: event.request.body,
			// @ts-expect-error required by Node's fetch when streaming a request body
			duplex: 'half',
			redirect: 'manual'
		});
		// Node's fetch has already decompressed the body, so the upstream encoding headers no longer apply
		const responseHeaders = new Headers(response.headers);
		responseHeaders.delete('content-encoding');
		responseHeaders.delete('content-length');
		return new Response(response.body, {
			status: response.status,
			statusText: response.statusText,
			headers: responseHeaders
		});
	}
	return resolve(event);
};
