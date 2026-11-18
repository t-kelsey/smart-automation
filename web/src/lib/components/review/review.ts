import { invalidateAll } from '$app/navigation';
import { notify } from '#lib/components/toast/index.ts';
import type { Borehole, FieldEdit, FieldFlag, SourceRef } from '#lib/domain/borehole.ts';
import { ValidationError, type BoreholeService } from '#lib/services/index.ts';

/**
 * Review state of one borehole (ADR-0006): flags, edits and sources per field, and the writes. A
 * field is addressed by its API name and, for layer fields, the layer id. Recreate it whenever the
 * borehole is reloaded.
 */
export class Review {
	constructor(
		readonly borehole: Borehole,
		readonly service: BoreholeService
	) {}

	openFlags = (field: string, layerId: string | null = null): FieldFlag[] =>
		this.borehole.flags.filter((f) => !f.resolvedAt && f.field === field && f.layerId === layerId);

	/** Newest first. */
	edits = (field: string, layerId: string | null = null): FieldEdit[] =>
		this.borehole.edits.filter((e) => e.field === field && e.layerId === layerId);

	source = (field: string, layerId: string | null = null): SourceRef | null =>
		layerId
			? (this.borehole.layers.find((l) => l.id === layerId)?.source ?? null)
			: (this.borehole.sources[field] ?? null);

	/** Worst open flag of a layer, for the profile. */
	layerSeverity = (layerId: string): FieldFlag['severity'] | null => {
		const flags = this.borehole.flags.filter((f) => !f.resolvedAt && f.layerId === layerId);
		if (flags.some((f) => f.severity === 'error')) return 'error';
		return flags.length ? 'warning' : null;
	};

	/** Background of a field: red/yellow for an open error/warning, blue for a validator correction. */
	tint = (field: string, layerId: string | null = null): string => {
		const flags = this.openFlags(field, layerId);
		if (flags.some((f) => f.severity === 'error')) return 'bg-error-500/15 ring-1 ring-error-500';
		if (flags.length) return 'bg-warning-500/15 ring-1 ring-warning-500';
		if (this.edits(field, layerId)[0]?.source === 'validator') return 'bg-sky-500/10';
		return '';
	};

	/**
	 * Runs a write and reloads the page data. Returns `null` on success, else the message for
	 * `field` (shown next to it); without a field the error is shown as a toast.
	 */
	run = async (write: (service: BoreholeService) => Promise<unknown>, field?: string) => {
		try {
			await write(this.service);
			await invalidateAll();
			return null;
		} catch (e) {
			const message = e instanceof ValidationError && field ? e.messageFor(field) : null;
			if (message) return message;
			notify.fromError(e, e instanceof ValidationError ? e.message : 'Could not save');
			return 'Not saved.';
		}
	};

	setField = (field: string, text: string, layerId: string | null = null) =>
		this.run((s) => s.setField(this.borehole.id, field, text, layerId), field);

	resolve = (flagId: string) => this.run((s) => s.resolveFlag(flagId));

	revert = (editId: string) => this.run((s) => s.revertEdit(this.borehole.id, editId));
}

/** A value of the edit history as text: coordinates, a layer snapshot or a plain value. */
export function formatValue(value: unknown): string {
	if (value === null || value === undefined || value === '') return '–';
	if (typeof value !== 'object') return String(value);
	const v = value as Record<string, unknown>;
	if ('x' in v && 'y' in v) return `${v.x}, ${v.y}${v.epsg ? ` (EPSG:${v.epsg})` : ''}`;
	if (Array.isArray(v.coordinates)) return v.coordinates.join(', ');
	if ('depth_from_m' in v) {
		return `${v.depth_from_m}–${v.depth_to_m} m${v.petrography ? `, ${v.petrography}` : ''}`;
	}
	return JSON.stringify(value);
}
