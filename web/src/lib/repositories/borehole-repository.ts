import type {
	Borehole,
	BoreholeSummary,
	ListParams,
	MapPoint,
	Page
} from '#lib/domain/borehole.ts';

/** Thrown by repositories on transport or server errors (not for "not found"). */
export class RepositoryError extends Error {
	constructor(
		message: string,
		readonly status?: number,
		options?: ErrorOptions
	) {
		super(message, options);
		this.name = 'RepositoryError';
	}
}

/**
 * Data access for boreholes. Implemented by the API repository and the mock repository.
 * Implementations return domain types; wire formats stay inside the implementation.
 */
export interface BoreholeRepository {
	list(params?: ListParams): Promise<Page<BoreholeSummary>>;
	/** Positions of all boreholes with a location, without any further details. */
	listMapPoints(): Promise<MapPoint[]>;
	/** Returns the borehole including layers and documents, or `null` if it does not exist. */
	getById(id: string): Promise<Borehole | null>;
}
