import type { Attachment } from 'svelte/attachments';
import { notify } from '#lib/components/toast/index.ts';
import type { Borehole, FieldEdit, FieldFlag, SourceRef } from '#lib/domain/borehole.ts';
import { ValidationError, type BoreholeService } from '#lib/services/index.ts';

/**
 * Review state of one borehole (ADR-0006): flags, edits and sources per field, and the writes. A
 * field is addressed by its API name and, for layer fields, the layer id. Every write hands the
 * borehole as stored afterwards to `onupdate`; recreate the review with it.
 */
export class Review {
	constructor(
		readonly borehole: Borehole,
		readonly service: BoreholeService,
		private readonly onupdate: (borehole: Borehole) => void
	) {}

	openFlags = (field: string, layerId: string | null = null): FieldFlag[] =>
		this.borehole.flags.filter((f) => !f.resolvedAt && f.field === field && f.layerId === layerId);

	/** Newest first. */
	edits = (field: string, layerId: string | null = null): FieldEdit[] =>
		this.borehole.edits.filter((e) => e.field === field && e.layerId === layerId);

	source = (field: string, layerId: string | null = null): SourceRef | null =>
		layerId ? this.#layerSource(field, layerId) : (this.borehole.sources[field] ?? null);

	#layerSource(field: string, layerId: string) {
		const layer = this.borehole.layers.find((l) => l.id === layerId);
		return layer?.sources[field as keyof typeof layer.sources] ?? layer?.source ?? null;
	}

	/** Flags created for this borehole, and how many of them are resolved. */
	get progress() {
		const flags = this.borehole.flags;
		return { done: flags.filter((f) => f.resolvedAt).length, total: flags.length };
	}

	/** The document most values are written in: the borehole's own (split-out) log. */
	get mainDocumentId(): string | null {
		const counts = new Map<string, number>();
		for (const source of [
			...Object.values(this.borehole.sources),
			...this.borehole.layers.map((l) => l.source)
		]) {
			if (source) counts.set(source.documentId, (counts.get(source.documentId) ?? 0) + 1);
		}
		return [...counts].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
	}

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
	 * Runs a write and passes the stored borehole on. Returns `null` on success, else the message for
	 * `field` (shown next to it); without a field the error is shown as a toast.
	 */
	run = async (write: (service: BoreholeService) => Promise<Borehole>, field?: string) => {
		try {
			this.onupdate(await write(this.service));
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

	/** Saves the flag's suggested value, which resolves the flag. */
	apply = (flag: FieldFlag) =>
		flag.field === 'location'
			? this.run(
					(s) =>
						s.setLocation(
							this.borehole.id,
							flag.suggestion as { x: number; y: number; epsg: number }
						),
					'location'
				)
			: this.run(
					(s) => s.setValue(this.borehole.id, flag.field, flag.suggestion, flag.layerId),
					flag.field
				);

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

/** Moves the focus to the next field of the review form (Enter does what Tab does). */
export function focusNext(from: HTMLElement) {
	const fields = [...document.querySelectorAll<HTMLElement>('[data-review-input]')];
	const next = fields[fields.indexOf(from) + 1];
	if (next) next.focus();
	else from.blur();
}

/** Lets a text area grow with its content; re-attach with the value to refit after a save. */
export const autosize =
	(value: unknown): Attachment<HTMLTextAreaElement> =>
	(element) => {
		void value;
		const fit = () => {
			element.style.height = 'auto';
			element.style.height = `${element.scrollHeight + element.offsetHeight - element.clientHeight}px`;
		};
		let width = 0;
		const observer = new ResizeObserver(([entry]) => {
			if (entry.contentRect.width === width) return;
			width = entry.contentRect.width;
			fit();
		});
		observer.observe(element);
		element.addEventListener('input', fit);
		return () => {
			observer.disconnect();
			element.removeEventListener('input', fit);
		};
	};
