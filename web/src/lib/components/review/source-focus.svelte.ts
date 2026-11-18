import type { SourceRef } from '#lib/domain/borehole.ts';

/** Delay before a hovered value is shown, so that sweeping over the form does not jump around. */
const HOVER_DELAY = 150;
/** Delay before the document zooms back out once the pointer has left the data. */
const LEAVE_DELAY = 300;

const same = (a: SourceRef | null | undefined, b: SourceRef | null | undefined) =>
	a === b ||
	(!!a &&
		!!b &&
		a.documentId === b.documentId &&
		a.page === b.page &&
		String(a.box) === String(b.box));

/**
 * Which source the document viewer zooms to on the review page. The focused field pins its source;
 * hovering another value previews that one until the pointer leaves the data, then the pinned
 * source (or the whole page) is shown again.
 */
export class SourceFocus {
	/** `undefined` while nothing is hovered; `null` for a hovered value without a source. */
	#hovered = $state.raw<SourceRef | null | undefined>(undefined);
	#pinned = $state.raw<SourceRef | null>(null);
	#pending: SourceRef | null | undefined;
	#timer: ReturnType<typeof setTimeout> | undefined;

	get current(): SourceRef | null {
		return this.#hovered === undefined ? this.#pinned : this.#hovered;
	}

	#later(delay: number, value: SourceRef | null | undefined) {
		if (this.#timer !== undefined && same(this.#pending, value)) return;
		clearTimeout(this.#timer);
		this.#pending = value;
		this.#timer = setTimeout(() => {
			this.#timer = undefined;
			this.#hovered = value;
		}, delay);
	}

	/** The pointer is over a value. */
	hover = (source: SourceRef | null) => {
		if (this.#timer === undefined && same(this.#hovered, source)) return;
		this.#later(HOVER_DELAY, source);
	};

	/** The pointer left a value before its delay ran out: don't show it. */
	unhover = (source: SourceRef | null) => {
		if (this.#timer !== undefined && same(this.#pending, source)) {
			clearTimeout(this.#timer);
			this.#timer = undefined;
		}
	};

	/** The pointer has left the data. */
	leave = () => this.#later(LEAVE_DELAY, undefined);

	/** The pointer moved over to the document: keep what is shown, so it can be read there. */
	hold = () => {
		clearTimeout(this.#timer);
		this.#timer = undefined;
	};

	/**
	 * A field got (`source`) or lost (`null`) the focus. Focusing ends any hover preview, since the
	 * pointer may still rest on another value (e.g. after Tab).
	 */
	pin = (source: SourceRef | null) => {
		if (source) {
			clearTimeout(this.#timer);
			this.#timer = undefined;
			this.#hovered = undefined;
		}
		this.#pinned = source;
	};

	destroy = () => clearTimeout(this.#timer);
}
