/** A file chosen for upload; it only exists in the browser until the extraction is started. */
export interface QueuedFile {
	id: string;
	file: File;
}

/** Files waiting for the pipeline to be configured. Lost on a page reload, since nothing is stored yet. */
let files = $state.raw<QueuedFile[]>([]);

export function getQueuedFiles(): QueuedFile[] {
	return files;
}

export function queueFiles(added: File[]) {
	files = [...added.map((file) => ({ id: crypto.randomUUID(), file })), ...files];
}

export function unqueueFile(id: string) {
	files = files.filter((f) => f.id !== id);
}

export function clearQueue() {
	files = [];
}
