import type {
	Borehole,
	SearchCompletion,
	SearchHit,
	SearchPage,
	SearchQuery
} from '#lib/domain/borehole.ts';
import type { SearchRepository } from '../search-repository';
import { toSummary } from './mock-borehole-repository';
import { mockBoreholes } from './mock-data';

/** Naive in-memory search: counts term occurrences in borehole and layer text. */
export class MockSearchRepository implements SearchRepository {
	constructor(private readonly boreholes: Borehole[] = mockBoreholes) {}

	async search({ q, limit, offset = 0 }: SearchQuery): Promise<SearchPage> {
		const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
		if (!terms.length) return { items: [], total: 0 };

		const hits: SearchHit[] = [];
		for (const b of this.boreholes) {
			const texts = [
				b.name,
				b.cause,
				b.location?.place,
				b.drillingMethod,
				...b.layers.map((l) => l.petrography.description),
				...b.layers.map((l) => l.stratigraphy.name)
			].filter((t): t is string => !!t);
			// Every term must occur somewhere; the score is the number of matching texts.
			const perTerm = terms.map((t) => texts.filter((x) => x.toLowerCase().includes(t)));
			if (perTerm.some((m) => m.length === 0)) continue;
			hits.push({
				borehole: toSummary(b),
				score: perTerm.reduce((sum, m) => sum + m.length, 0),
				snippet: perTerm[0][0]
			});
		}
		hits.sort(
			(a, b) => (b.score ?? 0) - (a.score ?? 0) || a.borehole.name.localeCompare(b.borehole.name)
		);
		const end = limit === undefined ? undefined : offset + limit;
		return { items: hits.slice(offset, end), total: hits.length };
	}

	/** No completions in the mock. */
	async complete(): Promise<SearchCompletion[]> {
		return [];
	}
}
