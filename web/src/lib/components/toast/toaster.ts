import { createToaster } from '@skeletonlabs/skeleton-svelte';
import { RepositoryError } from '#lib/services/index.ts';

export const toaster = createToaster({ placement: 'bottom-end' });

/** Describes a failed call in terms a user can act on. */
function describe(error: unknown): { title: string; description: string } {
	if (error instanceof RepositoryError) {
		if (error.status === undefined) {
			return {
				title: 'API connection failed',
				description: 'The server could not be reached. Check your connection and try again.'
			};
		}
		return { title: 'Server error', description: `The API responded with status ${error.status}.` };
	}
	return {
		title: 'Something went wrong',
		description: error instanceof Error ? error.message : 'An unexpected error occurred.'
	};
}

export const notify = {
	success: (title: string, description?: string) => toaster.success({ title, description }),
	info: (title: string, description?: string) => toaster.info({ title, description }),
	warning: (title: string, description?: string) => toaster.warning({ title, description }),
	error: (title: string, description?: string) => toaster.error({ title, description }),
	/** Shows a toast for a caught error; `title` overrides the generated one. */
	fromError: (error: unknown, title?: string) => {
		const d = describe(error);
		return toaster.error({ title: title ?? d.title, description: d.description });
	}
};
