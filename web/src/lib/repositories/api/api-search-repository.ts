import type { Page, SearchHit, SearchQuery } from '#lib/domain/borehole.ts';
import type { SearchRepository } from '../search-repository';
import { listQuery } from './api-borehole-repository';
import { ApiClient, type ApiClientOptions } from './api-client';
import type { ApiFeatureCollection } from './api-types';
import { featureToSummary } from './mappers';

/** Forwards queries to `GET /boreholes/search`, which ranks hits and returns a snippet. */
export class ApiSearchRepository implements SearchRepository {
	private readonly client: ApiClient;

	constructor(options: ApiClientOptions) {
		this.client = new ApiClient(options);
	}

	async search({ q, limit, offset }: SearchQuery): Promise<Page<SearchHit>> {
		const qs = listQuery({ q, limit, offset });
		const collection = (await this.client.getJson<ApiFeatureCollection>(`/boreholes/search${qs}`))!;
		return {
			items: collection.features.map((feature) => ({
				borehole: featureToSummary(feature),
				score: feature.score,
				snippet: feature.snippet ?? undefined
			})),
			total: collection.total
		};
	}
}
