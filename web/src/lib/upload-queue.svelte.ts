/** A file chosen for upload; it only exists in the browser until the extraction is started. */
export interface QueuedFile {
	id: string;
	file: File;
	/** Set once the file is uploaded, so a failed pipeline start does not upload it twice. */
	documentId?: string;
}

/** Files waiting for the pipeline to be configured. Lost on a page reload, since nothing is stored yet. */
let files = $state<QueuedFile[]>([]);

export function getQueuedFiles(): QueuedFile[] {
	return files;
}

export function queueFiles(added: File[]) {
	files = [...added.map((file) => ({ id: crypto.randomUUID(), file })), ...files];
}

export function markUploaded(id: string, documentId: string) {
	const queued = files.find((f) => f.id === id);
	if (queued) queued.documentId = documentId;
}

export function unqueueFile(id: string) {
	files = files.filter((f) => f.id !== id);
}

export function clearQueue() {
	files = [];
}
