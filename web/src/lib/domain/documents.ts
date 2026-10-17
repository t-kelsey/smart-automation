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
