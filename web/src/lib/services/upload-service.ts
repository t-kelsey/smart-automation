import type { UploadedDocument } from '#lib/domain/documents.ts';
import type { UploadRepository } from '#lib/repositories/upload-repository.ts';

/** File types the extraction pipeline can read. */
export const SUPPORTED_UPLOAD_EXTENSIONS = [
	'.pdf',
	'.png',
	'.jpg',
	'.jpeg',
	'.tif',
	'.tiff',
	'.docx'
];

export class UnsupportedFileError extends Error {
	constructor(readonly filename: string) {
		super(`${filename}: unsupported file type, expected ${SUPPORTED_UPLOAD_EXTENSIONS.join(', ')}`);
		this.name = 'UnsupportedFileError';
	}
}

/** Upload use case: validates the file type before it is sent. */
export class UploadService {
	readonly accept = SUPPORTED_UPLOAD_EXTENSIONS.join(',');

	constructor(private readonly repository: UploadRepository) {}

	isSupported(file: File): boolean {
		const name = file.name.toLowerCase();
		return SUPPORTED_UPLOAD_EXTENSIONS.some((extension) => name.endsWith(extension));
	}

	async upload(file: File): Promise<UploadedDocument> {
		if (!this.isSupported(file)) throw new UnsupportedFileError(file.name);
		return this.repository.upload(file);
	}
}
