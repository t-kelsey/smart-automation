import type {
	Borehole,
	DocumentDetail,
	BoreholeSummary,
	ListParams,
	MapPoint,
	Page
} from '#lib/domain/borehole.ts';

/** Thrown by repositories on transport or server errors (not for "not found"). */
export class RepositoryError extends Error {
	/** The API's `errors.detail`, if the response had one (e.g. why a parameter is invalid). */
	readonly detail?: string;

	constructor(
		message: string,
		readonly status?: number,
		options?: ErrorOptions & { detail?: string }
	) {
		super(message, options);
		this.name = 'RepositoryError';
		this.detail = options?.detail;
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
	/** Returns one document with its linked boreholes, or `null` if it does not exist. */
	getDocument(id: string): Promise<DocumentDetail | null>;
}
