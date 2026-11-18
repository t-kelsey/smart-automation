import { RepositoryError, ValidationError } from '../borehole-repository';

export interface ApiClientOptions {
	baseUrl: string;
	fetch: typeof fetch;
}

/** Thin JSON client shared by the API repositories. */
export class ApiClient {
	constructor(private readonly options: ApiClientOptions) {}

	/**
	 * Returns the parsed JSON body, or `null` if the status is one of `nullOn` (e.g. 404).
	 * Other non-2xx statuses and network errors throw a `RepositoryError`.
	 */
	getJson<T>(path: string, nullOn: number[] = []): Promise<T | null> {
		return this.request<T>('GET', path, undefined, nullOn);
	}

	/** A write with a JSON body; a 422 throws a `ValidationError` with the changeset errors. */
	async send<T>(method: 'POST' | 'PATCH' | 'DELETE', path: string, body?: unknown): Promise<T> {
		return (await this.request<T>(method, path, body))!;
	}

	private async request<T>(
		method: string,
		path: string,
		body?: unknown,
		nullOn: number[] = []
	): Promise<T | null> {
		let response: Response;
		try {
			response = await this.options.fetch(`${this.options.baseUrl}${path}`, {
				method,
				headers: {
					accept: 'application/json',
					...(body === undefined ? {} : { 'content-type': 'application/json' })
				},
				body: body === undefined ? undefined : JSON.stringify(body)
			});
		} catch (cause) {
			throw new RepositoryError(`API request failed: ${path}`, undefined, { cause });
		}
		if (nullOn.includes(response.status)) return null;
		if (response.status === 422) throw new ValidationError(await changesetErrors(response));
		if (!response.ok) {
			const detail = await errorDetail(response);
			throw new RepositoryError(`API ${path} returned ${response.status}`, response.status, {
				detail
			});
		}
		return (await response.json()) as T;
	}
}

/** Phoenix changeset errors (`{"errors": {"field": ["message"]}}`), flattened to strings. */
async function changesetErrors(response: Response): Promise<Record<string, string[]>> {
	try {
		const { errors } = (await response.json()) as { errors?: Record<string, unknown> };
		return Object.fromEntries(
			Object.entries(errors ?? {}).map(([field, value]) => [
				field,
				Array.isArray(value) && value.every((v) => typeof v === 'string')
					? value
					: [typeof value === 'string' ? value : JSON.stringify(value)]
			])
		);
	} catch {
		return {};
	}
}

/** `errors.detail` of an API error body, if there is one. */
async function errorDetail(response: Response): Promise<string | undefined> {
	try {
		const body = (await response.json()) as { errors?: { detail?: unknown } };
		return typeof body.errors?.detail === 'string' ? body.errors.detail : undefined;
	} catch {
		return undefined;
	}
}
