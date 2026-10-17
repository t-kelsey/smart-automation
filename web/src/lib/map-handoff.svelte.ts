let snapshot: string | undefined;

/** Remember a picture of the dashboard map so the big map page can cover its first, still empty frames. */
export function setMapSnapshot(dataUrl: string | undefined) {
	snapshot = dataUrl;
}

/** Returns the remembered picture once; later calls get nothing. */
export function takeMapSnapshot(): string | undefined {
	const taken = snapshot;
	snapshot = undefined;
	return taken;
}

export interface MapView {
	lat: number;
	lon: number;
	zoom: number;
}

// Reactive: the sidebar's Map link follows it.
let lastView = $state<MapView>();

/** Remember where the user left a map, so the other map (dashboard or /map) continues from there. */
export function setLastMapView(view: MapView) {
	lastView = view;
}

export function getLastMapView(): MapView | undefined {
	return lastView;
}
