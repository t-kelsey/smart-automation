import { RepositoryError } from '../borehole-repository';

export interface ApiClientOptions {
	baseUrl: string;
	fetch: typeof fetch;
}

/** Thin JSON GET client shared by the API repositories. */
export class ApiClient {
	constructor(private readonly options: ApiClientOptions) {}

	/**
	 * Returns the parsed JSON body, or `null` if the status is one of `nullOn` (e.g. 404).
	 * Other non-2xx statuses and network errors throw a `RepositoryError`.
	 */
	async getJson<T>(path: string, nullOn: number[] = []): Promise<T | null> {
		let response: Response;
		try {
			response = await this.options.fetch(`${this.options.baseUrl}${path}`, {
				headers: { accept: 'application/json' }
			});
		} catch (cause) {
			throw new RepositoryError(`API request failed: ${path}`, undefined, { cause });
		}
		if (nullOn.includes(response.status)) return null;
		if (!response.ok) {
			throw new RepositoryError(`API ${path} returned ${response.status}`, response.status);
		}
		return (await response.json()) as T;
	}
}
