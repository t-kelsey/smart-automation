import type {
	Borehole,
	BoreholeFilter,
	BoreholeSort,
	BoreholeSummary,
	MapPoint
} from '#lib/domain/borehole.ts';
import type { BoreholeRepository } from '#lib/repositories/borehole-repository.ts';

export class BoreholeNotFoundError extends Error {
	constructor(readonly id: string) {
		super(`Borehole ${id} not found`);
		this.name = 'BoreholeNotFoundError';
	}
}

export const DEFAULT_PAGE_SIZE = 20;
const MAX_PAGE_SIZE = 100;

export interface BoreholeListQuery extends BoreholeFilter {
	sort?: BoreholeSort;
	/** 1-based page number. */
	page?: number;
	pageSize?: number;
}

export interface PagedResult<T> {
	items: T[];
	total: number;
	page: number;
	pageSize: number;
	pageCount: number;
	hasPrevious: boolean;
	hasNext: boolean;
}

/** Use cases for boreholes. The only data entry point for the UI. */
export class BoreholeService {
	constructor(private readonly repository: BoreholeRepository) {}

	/**
	 * One page of boreholes matching the filter. Page and page size are clamped to valid values;
	 * a page beyond the last one is replaced by the last page.
	 */
	async list({
		page = 1,
		pageSize = DEFAULT_PAGE_SIZE,
		...params
	}: BoreholeListQuery = {}): Promise<PagedResult<BoreholeSummary>> {
		const size = Math.min(MAX_PAGE_SIZE, Math.max(1, Math.floor(pageSize)));
		let current = Math.max(1, Math.floor(page));

		let result = await this.repository.list({
			...params,
			limit: size,
			offset: (current - 1) * size
		});
		const pageCount = Math.max(1, Math.ceil(result.total / size));
		if (current > pageCount) {
			current = pageCount;
			result = await this.repository.list({ ...params, limit: size, offset: (current - 1) * size });
		}
		return {
			items: result.items,
			total: result.total,
			page: current,
			pageSize: size,
			pageCount,
			hasPrevious: current > 1,
			hasNext: current < pageCount
		};
	}

	/** Positions of all boreholes for the map; one light request instead of paging through the list. */
	listMapPoints(): Promise<MapPoint[]> {
		return this.repository.listMapPoints();
	}

	/** Summary of one borehole, e.g. for a map tooltip. Throws `BoreholeNotFoundError` if it does not exist. */
	async getSummary(id: string): Promise<BoreholeSummary> {
		const { name, date, elevation, totalDepth, location, verified } = await this.getById(id);
		return { id, name, date, elevation, totalDepth, location, verified };
	}

	/** Borehole with layers ordered by depth. Throws `BoreholeNotFoundError` if it does not exist. */
	async getById(id: string): Promise<Borehole> {
		const borehole = await this.repository.getById(id);
		if (!borehole) throw new BoreholeNotFoundError(id);
		return {
			...borehole,
			layers: [...borehole.layers].sort((a, b) => a.startDepth - b.startDepth)
		};
	}
}
