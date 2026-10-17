import type { BoreholeDocument } from './borehole';

/** Splits a borehole's documents into its original document (if any) and the additional files. */
export function splitDocuments(documents: BoreholeDocument[]): {
	original: BoreholeDocument | null;
	additional: BoreholeDocument[];
} {
	return {
		original: documents.find((doc) => doc.role === 'original') ?? null,
		additional: documents.filter((doc) => doc.role !== 'original')
	};
}

/** A raw document accepted by the API; the extraction pipeline processes it in the background. */
export interface UploadedDocument {
	id: string;
	filename: string;
	/** `pending` (stored, no pipeline configured), `processing`, `extracted`, `failed`, `reviewed`. */
	status: string;
}
