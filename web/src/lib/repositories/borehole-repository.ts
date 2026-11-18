import type {
	Borehole,
	BoreholeChanges,
	LayerChanges,
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

/** A write the API rejected (422); `errors` holds the messages per field. */
export class ValidationError extends Error {
	constructor(readonly errors: Record<string, string[]>) {
		super(
			Object.entries(errors)
				.map(([field, messages]) => `${field} ${messages.join(', ')}`)
				.join('; ') || 'The value was rejected.'
		);
		this.name = 'ValidationError';
	}

	/** The messages for `field`, or all of them if none is about it. */
	messageFor(field: string): string {
		return this.errors[field]?.join(', ') ?? this.message;
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

	// Writes of the review (ADR-0006). Each returns the borehole as stored afterwards and throws a
	// `ValidationError` when the API rejects the values.
	update(id: string, changes: BoreholeChanges): Promise<Borehole>;
	addLayer(id: string, layer: LayerChanges): Promise<Borehole>;
	updateLayer(id: string, layerId: string, changes: LayerChanges): Promise<Borehole>;
	deleteLayer(id: string, layerId: string): Promise<Borehole>;
	/** Writes the edit's old value back as a new edit; restores a deleted layer. */
	revertEdit(id: string, editId: string): Promise<Borehole>;
	/** Confirms the flagged value as right. */
	resolveFlag(flagId: string): Promise<Borehole>;
	setVerified(id: string, verified: boolean): Promise<Borehole>;
}
