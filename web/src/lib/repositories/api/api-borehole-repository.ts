import type {
	Borehole,
	BoreholeChanges,
	BoreholeSort,
	LayerChanges,
	BoreholeSortField,
	BoreholeSummary,
	DocumentDetail,
	ListParams,
	MapPoint,
	Page
} from '#lib/domain/borehole.ts';
import type { BoreholeRepository } from '../borehole-repository';
import { ApiClient, type ApiClientOptions } from './api-client';
import type {
	ApiBoreholeDetail,
	ApiDocumentDetail,
	ApiFeatureCollection,
	ApiItemResponse,
	ApiPointFeature
} from './api-types';
import { featureToMapPoint, featureToSummary, toBorehole, toDocumentDetail } from './mappers';

const sortFields: Record<BoreholeSortField, string> = {
	name: 'name',
	date: 'drilled_at',
	totalDepth: 'total_depth_m',
	openFlags: 'open_flags'
};

/** `-` marks descending, except for `open_flags`, which sorts most flags first without it. */
function sortParam({ field, direction }: BoreholeSort): string {
	const descending = field === 'openFlags' ? direction === 'asc' : direction === 'desc';
	return `${descending ? '-' : ''}${sortFields[field]}`;
}

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
			sort: sort && sortParam(sort),
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

	update(id: string, changes: BoreholeChanges): Promise<Borehole> {
		return this.write('PATCH', `/boreholes/${encodeURIComponent(id)}`, { borehole: changes });
	}

	addLayer(id: string, layer: LayerChanges): Promise<Borehole> {
		return this.write('POST', `/boreholes/${encodeURIComponent(id)}/layers`, { layer });
	}

	updateLayer(id: string, layerId: string, changes: LayerChanges): Promise<Borehole> {
		return this.write('PATCH', this.layerPath(id, layerId), { layer: changes });
	}

	deleteLayer(id: string, layerId: string): Promise<Borehole> {
		return this.write('DELETE', this.layerPath(id, layerId));
	}

	revertEdit(id: string, editId: string): Promise<Borehole> {
		return this.write(
			'POST',
			`/boreholes/${encodeURIComponent(id)}/edits/${encodeURIComponent(editId)}/revert`
		);
	}

	resolveFlag(flagId: string): Promise<Borehole> {
		return this.write('POST', `/flags/${encodeURIComponent(flagId)}/resolve`);
	}

	setVerified(id: string, verified: boolean): Promise<Borehole> {
		return this.write('POST', `/boreholes/${encodeURIComponent(id)}/verify`, { verified });
	}

	async delete(id: string): Promise<void> {
		await this.client.send('DELETE', `/boreholes/${encodeURIComponent(id)}`);
	}

	private layerPath(id: string, layerId: string) {
		return `/boreholes/${encodeURIComponent(id)}/layers/${encodeURIComponent(layerId)}`;
	}

	/** Every write answers with the borehole as `GET /boreholes/:id` would. */
	private async write(method: 'POST' | 'PATCH' | 'DELETE', path: string, body?: unknown) {
		const { data } = await this.client.send<ApiItemResponse<ApiBoreholeDetail>>(method, path, body);
		return toBorehole(data, this.options.baseUrl);
	}

	async getDocument(id: string): Promise<DocumentDetail | null> {
		const body = await this.client.getJson<ApiItemResponse<ApiDocumentDetail>>(
			`/documents/${encodeURIComponent(id)}`,
			[404]
		);
		return body ? toDocumentDetail(body.data, this.options.baseUrl) : null;
	}
}
