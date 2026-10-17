import type { UploadedDocument } from '#lib/domain/documents.ts';

/** Sends raw documents to the extraction pipeline. */
export interface UploadRepository {
	/** Throws a `RepositoryError` if the document is not accepted. */
	upload(file: File): Promise<UploadedDocument>;
}
