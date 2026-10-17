import type {
	Borehole,
	BoreholeSortField,
	BoreholeSummary,
	ListParams,
	MapPoint,
	Page
} from '#lib/domain/borehole.ts';
import type { BoreholeRepository } from '../borehole-repository';
import { ApiClient, type ApiClientOptions } from './api-client';
import type {
	ApiBoreholeDetail,
	ApiFeatureCollection,
	ApiItemResponse,
	ApiPointFeature
} from './api-types';
import { featureToMapPoint, featureToSummary, toBorehole } from './mappers';

const sortFields: Record<BoreholeSortField, string> = {
	name: 'name',
	date: 'drilled_at',
	totalDepth: 'total_depth_m'
};

/** Query string for the list endpoints; empty values are left out. */
export function listQuery(params: Record<string, string | number | boolean | undefined>): string {
	const query = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== '') query.set(key, String(value));
	}
	return query.size ? `?${query}` : '';
}

/** Repository backed by the Phoenix JSON API; filtering, sorting and paging happen server-side. */
export class ApiBoreholeRepository implements BoreholeRepository {
	private readonly client: ApiClient;

	constructor(private readonly options: ApiClientOptions) {
		this.client = new ApiClient(options);
	}

	async list({
		search,
		verified,
		drilledFrom,
		drilledTo,
		minDepth,
		maxDepth,
		sort,
		limit,
		offset
	}: ListParams = {}): Promise<Page<BoreholeSummary>> {
		const qs = listQuery({
			q: search?.trim(),
			verified,
			drilled_from: drilledFrom,
			drilled_to: drilledTo,
			min_depth: minDepth,
			max_depth: maxDepth,
			sort: sort && `${sort.direction === 'desc' ? '-' : ''}${sortFields[sort.field]}`,
			limit,
			offset
		});
		const collection = (await this.client.getJson<ApiFeatureCollection>(`/boreholes${qs}`))!;
		return { items: collection.features.map(featureToSummary), total: collection.total };
	}

	async listMapPoints(): Promise<MapPoint[]> {
		const collection =
			(await this.client.getJson<ApiFeatureCollection<ApiPointFeature>>('/boreholes?view=points'))!;
		return collection.features.flatMap(featureToMapPoint);
	}

	async getById(id: string): Promise<Borehole | null> {
		const body = await this.client.getJson<ApiItemResponse<ApiBoreholeDetail>>(
			`/boreholes/${encodeURIComponent(id)}`,
			[404]
		);
		return body ? toBorehole(body.data, this.options.baseUrl) : null;
	}
}
