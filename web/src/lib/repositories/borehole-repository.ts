import type {
	BBox,
	Borehole,
	BoreholeChanges,
	BoreholeColumnData,
	LayerChanges,
	DocumentDetail,
	BoreholeSummary,
	ListParams,
	MapPoint,
	Page
} from '#lib/domain/borehole.ts';

/** Thrown by repositories on transport or server errors (not for "not found"). */
/** An EPSG code that puts x/y `distanceM` metres from the borehole `near`, written in that code. */
export interface EpsgGuess {
	epsg: number;
	distanceM: number;
	near: string;
}

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
	/** Located boreholes in `bbox` with their layers, for drawing them as columns. */
	listColumns(bbox: BBox): Promise<BoreholeColumnData[]>;
	/** Returns the borehole including layers and documents, or `null` if it does not exist. */
	getById(id: string): Promise<Borehole | null>;
	/** Returns one document with its linked boreholes, or `null` if it does not exist. */
	getDocument(id: string): Promise<DocumentDetail | null>;
	/** Probable EPSG codes for x/y written without one, judged by nearby boreholes; best first. */
	guessEpsg(
		id: string,
		x: number,
		y: number,
		area?: { lon: number; lat: number }
	): Promise<EpsgGuess[]>;

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
	/** Deletes the borehole with its layers, flags and history; its documents stay. */
	delete(id: string): Promise<void>;
}
