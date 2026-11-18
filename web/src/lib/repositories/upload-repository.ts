import type { ProcessedDocument, UploadedDocument } from '#lib/domain/documents.ts';

/** Sends raw documents to the extraction pipeline. */
export interface UploadRepository {
	/** Uploads the document, which the API hands to the extraction pipeline. Throws a `RepositoryError` if it is not accepted. */
	upload(file: File): Promise<UploadedDocument>;
	/** Stored documents whose content has this SHA-256 (hex). */
	findBySha256(sha256: string): Promise<ProcessedDocument[]>;
}
