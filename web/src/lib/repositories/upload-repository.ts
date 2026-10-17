import type { UploadedDocument } from '#lib/domain/documents.ts';

/** Sends raw documents to the extraction pipeline. */
export interface UploadRepository {
	/** Uploads the document, which the API hands to the extraction pipeline. Throws a `RepositoryError` if it is not accepted. */
	upload(file: File): Promise<UploadedDocument>;
}
