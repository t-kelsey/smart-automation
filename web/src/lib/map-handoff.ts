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
