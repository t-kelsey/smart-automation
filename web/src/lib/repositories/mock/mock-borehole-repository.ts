import type {
	Borehole,
	BoreholeSummary,
	DocumentDetail,
	ListParams,
	MapPoint,
	Page
} from '#lib/domain/borehole.ts';
import type { BoreholeRepository } from '../borehole-repository';
import { mockBoreholes } from './mock-data';

export const toSummary = ({
	id,
	name,
	date,
	elevation,
	totalDepth,
	location,
	verified
}: Borehole): BoreholeSummary => ({ id, name, date, elevation, totalDepth, location, verified });

/** In-memory repository for development and tests. */
export class MockBoreholeRepository implements BoreholeRepository {
	constructor(private readonly boreholes: Borehole[] = mockBoreholes) {}

	async list({
		search,
		verified,
		drilledFrom,
		drilledTo,
		minDepth,
		maxDepth,
		sort,
		limit,
		offset = 0
	}: ListParams = {}): Promise<Page<BoreholeSummary>> {
		const term = search?.trim().toLowerCase();
		const matches = this.boreholes.filter(
			(b) =>
				(!term ||
					[b.name, b.externalId, b.location?.place].some((v) => v?.toLowerCase().includes(term))) &&
				(verified === undefined || b.verified === verified) &&
				(!drilledFrom || (b.date !== undefined && b.date >= drilledFrom)) &&
				(!drilledTo || (b.date !== undefined && b.date <= drilledTo)) &&
				(minDepth === undefined || (b.totalDepth !== null && b.totalDepth >= minDepth)) &&
				(maxDepth === undefined || (b.totalDepth !== null && b.totalDepth <= maxDepth))
		);
		if (sort) {
			const dir = sort.direction === 'asc' ? 1 : -1;
			matches.sort((a, b) => {
				const x = a[sort.field];
				const y = b[sort.field];
				// Missing values always sort last.
				if (x == null || y == null) return Number(x == null) - Number(y == null);
				return (x < y ? -1 : x > y ? 1 : 0) * dir;
			});
		}
		const end = limit === undefined ? undefined : offset + limit;
		return { items: matches.slice(offset, end).map(toSummary), total: matches.length };
	}

	async listMapPoints(): Promise<MapPoint[]> {
		return this.boreholes.flatMap(({ id, name, verified, location }) =>
			location ? [{ id, name, verified, lon: location.lon, lat: location.lat }] : []
		);
	}

	async getById(id: string): Promise<Borehole | null> {
		const borehole = this.boreholes.find((b) => b.id === id);
		return borehole ? structuredClone(borehole) : null;
	}

	async getDocument(id: string): Promise<DocumentDetail | null> {
		const linked = this.boreholes.filter((b) => b.documents.some((d) => d.id === id));
		const document = linked[0]?.documents.find((d) => d.id === id);
		if (!document) return null;
		return {
			...structuredClone(document),
			boreholes: linked.map(({ id, name }) => ({ id, name }))
		};
	}
}
