import type { Borehole, BoreholeSummary, ListParams, Page } from '#lib/domain/borehole.ts';
import { RepositoryError, type BoreholeRepository } from '../borehole-repository';
import type { ApiBorehole, ApiItemResponse, ApiListResponse } from './api-types';
import { toBorehole, toSummary } from './mappers';

interface Options {
	baseUrl: string;
	fetch: typeof fetch;
}

/** Repository backed by the Phoenix JSON API. */
export class ApiBoreholeRepository implements BoreholeRepository {
	constructor(private readonly options: Options) {}

	async list(params: ListParams = {}): Promise<Page<BoreholeSummary>> {
		const { sort, ...rest } = params;
		const query = new URLSearchParams();
		for (const [key, value] of Object.entries(rest)) {
			if (value !== undefined && value !== '') query.set(key, String(value));
		}
		if (sort) query.set('sort', `${sort.direction === 'desc' ? '-' : ''}${sort.field}`);
		const qs = query.size ? `?${query}` : '';

		const response = await this.get(`/boreholes${qs}`);
		const body = (await response.json()) as ApiListResponse<ApiBorehole>;
		return { items: body.data.map(toSummary), total: body.total };
	}

	async getById(id: string): Promise<Borehole | null> {
		const response = await this.get(`/boreholes/${encodeURIComponent(id)}`, [404]);
		if (response.status === 404) return null;
		const body = (await response.json()) as ApiItemResponse<ApiBorehole>;
		return toBorehole(body.data);
	}

	private async get(path: string, allowedStatuses: number[] = []): Promise<Response> {
		let response: Response;
		try {
			response = await this.options.fetch(`${this.options.baseUrl}${path}`, {
				headers: { accept: 'application/json' }
			});
		} catch (cause) {
			throw new RepositoryError(`API request failed: ${path}`, undefined, { cause });
		}
		if (!response.ok && !allowedStatuses.includes(response.status)) {
			throw new RepositoryError(`API ${path} returned ${response.status}`, response.status);
		}
		return response;
	}
}
