import type {
	BBox,
	BoreholeColumnData,
	Borehole,
	BoreholeFilter,
	BoreholeSort,
	BoreholeChanges,
	BoreholeSummary,
	DocumentDetail,
	LayerChanges,
	MapPoint
} from '#lib/domain/borehole.ts';
import { ValidationError, type BoreholeRepository } from '#lib/repositories/borehole-repository.ts';

export class BoreholeNotFoundError extends Error {
	constructor(readonly id: string) {
		super(`Borehole ${id} not found`);
		this.name = 'BoreholeNotFoundError';
	}
}

export class DocumentNotFoundError extends Error {
	constructor(readonly id: string) {
		super(`Document ${id} not found`);
		this.name = 'DocumentNotFoundError';
	}
}

const NUMBER_FIELDS = new Set([
	'elevation_m',
	'total_depth_m',
	'groundwater_level_m',
	'depth_from_m',
	'depth_to_m'
]);

/** Typed text of a field as the API takes it: empty is `null`, numbers accept a decimal comma. */
function parseValue(field: string, text: string): string | number | null {
	const value = text.trim();
	if (!value) return null;
	if (!NUMBER_FIELDS.has(field)) return value;
	const number = Number(value.replace(',', '.'));
	if (Number.isNaN(number)) throw new ValidationError({ [field]: ['is not a number'] });
	return number;
}

const byDepth = (borehole: Borehole): Borehole => ({
	...borehole,
	layers: [...borehole.layers].sort((a, b) => a.startDepth - b.startDepth)
});

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

	/**
	 * The next borehole to review: unverified, most open flags first, with the number of unverified
	 * boreholes; `next` is `null` when everything is verified.
	 */
	async nextToReview(): Promise<{ next: BoreholeSummary | null; total: number }> {
		const { items, total } = await this.repository.list({
			verified: false,
			sort: { field: 'openFlags', direction: 'desc' },
			limit: 1
		});
		return { next: items[0] ?? null, total };
	}

	/** Positions of all boreholes for the map; one light request instead of paging through the list. */
	listMapPoints(): Promise<MapPoint[]> {
		return this.repository.listMapPoints();
	}

	/** Located boreholes in `bbox` with their layers ordered by depth, for drawing them as columns. */
	async listColumns(bbox: BBox): Promise<BoreholeColumnData[]> {
		const columns = await this.repository.listColumns(bbox);
		return columns.map((column) => ({
			...column,
			layers: [...column.layers].sort((a, b) => a.startDepth - b.startDepth)
		}));
	}

	/** Summary of one borehole, e.g. for a map tooltip. Throws `BoreholeNotFoundError` if it does not exist. */
	async getSummary(id: string): Promise<BoreholeSummary> {
		const { name, date, elevation, totalDepth, location, verified, openFlagCount } =
			await this.getById(id);
		return { id, name, date, elevation, totalDepth, location, verified, openFlagCount };
	}

	/** Borehole with layers ordered by depth. Throws `BoreholeNotFoundError` if it does not exist. */
	async getById(id: string): Promise<Borehole> {
		const borehole = await this.repository.getById(id);
		if (!borehole) throw new BoreholeNotFoundError(id);
		return byDepth(borehole);
	}

	// Review (ADR-0006): every write returns the borehole as stored afterwards, with its flags and
	// edits updated, and throws a `ValidationError` for rejected values.

	/** Saves the typed text of one borehole field, or of one field of the layer `layerId`. */
	async setField(id: string, field: string, text: string, layerId?: string | null) {
		const changes = { [field]: parseValue(field, text) };
		return byDepth(
			await (layerId
				? this.repository.updateLayer(id, layerId, changes)
				: this.repository.update(id, changes))
		);
	}

	/** Saves a value as it is (e.g. a validator's suggestion), without parsing it. */
	async setValue(id: string, field: string, value: unknown, layerId?: string | null) {
		const changes = { [field]: value } as BoreholeChanges & LayerChanges;
		return byDepth(
			await (layerId
				? this.repository.updateLayer(id, layerId, changes)
				: this.repository.update(id, changes))
		);
	}

	/** Moves the borehole to `x`/`y` in the coordinate system `epsg`. */
	async setLocation(id: string, location: { x: number; y: number; epsg: number }) {
		return byDepth(await this.repository.update(id, location));
	}

	async addLayer(id: string, layer: LayerChanges) {
		return byDepth(await this.repository.addLayer(id, layer));
	}

	async deleteLayer(id: string, layerId: string) {
		return byDepth(await this.repository.deleteLayer(id, layerId));
	}

	/** Undoes an edit (restores the old value, or a deleted layer). */
	async revertEdit(id: string, editId: string) {
		return byDepth(await this.repository.revertEdit(id, editId));
	}

	/** Marks a flagged value as right. */
	async resolveFlag(flagId: string) {
		return byDepth(await this.repository.resolveFlag(flagId));
	}

	/** Releases the borehole (or takes the release back); allowed with open flags. */
	async setVerified(id: string, verified: boolean) {
		return byDepth(await this.repository.setVerified(id, verified));
	}

	/** Deletes the borehole with its layers, flags and history (not its documents). */
	async deleteBorehole(id: string) {
		await this.repository.delete(id);
	}

	/** Document with its linked boreholes. Throws `DocumentNotFoundError` if it does not exist. */
	async getDocument(id: string): Promise<DocumentDetail> {
		const document = await this.repository.getDocument(id);
		if (!document) throw new DocumentNotFoundError(id);
		return document;
	}
}
