/**
 * Highlighting of layers on the borehole details and review pages.
 *
 * Two independent highlights: `hoveredId` follows the pointer, `selectedId` is set by a click and
 * kept in local storage per borehole, so it survives a switch between the details and review pages.
 */
export class LayerSelection {
	hoveredId = $state<string | null>(null);
	#selectedId = $state<string | null>(null);
	#boreholeId: string;

	constructor(boreholeId: string) {
		this.#boreholeId = boreholeId;
	}

	/** Loads the stored selection. Call on mount: during server rendering there is no storage. */
	restore = () => {
		this.#selectedId = read(this.#boreholeId);
	};

	get selectedId() {
		return this.#selectedId;
	}

	hover = (id: string | null) => {
		this.hoveredId = id;
	};

	/** Selects the layer, or clears the selection when it is already selected. */
	toggle = (id: string) => {
		this.#selectedId = this.#selectedId === id ? null : id;
		write(this.#boreholeId, this.#selectedId);
	};

	isHovered = (id: string) => this.hoveredId === id;
	isSelected = (id: string) => this.#selectedId === id;
}

const storageKey = (boreholeId: string) => `borehole:${boreholeId}:selected-layer`;

function read(boreholeId: string): string | null {
	try {
		return localStorage.getItem(storageKey(boreholeId));
	} catch {
		return null; // SSR, or storage blocked
	}
}

function write(boreholeId: string, layerId: string | null) {
	try {
		if (layerId) localStorage.setItem(storageKey(boreholeId), layerId);
		else localStorage.removeItem(storageKey(boreholeId));
	} catch {
		// storage blocked: the selection then only lives until the page is left
	}
}
