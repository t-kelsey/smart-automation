import { PDFDocument } from 'pdf-lib';
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

/** Image types that can be embedded in a PDF as they are, without re-encoding. */
const MERGEABLE_IMAGE = /\.(png|jpe?g)$/i;

const byNaturalName = (a: File, b: File) =>
	a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' });

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

	/** Whether the file is an image that `combineImages` can turn into a PDF page. */
	isMergeableImage(file: File): boolean {
		return MERGEABLE_IMAGE.test(file.name);
	}

	/**
	 * Merges images that belong together (e.g. the scanned pages of one log, one file each) into a
	 * single multi-page PDF, ordered by file name ("page2" before "page10"), so the pipeline sees them
	 * as one document. Each page has the image's own pixel size.
	 */
	async combineImages(images: File[], name: string): Promise<File> {
		const pdf = await PDFDocument.create();
		for (const image of [...images].sort(byNaturalName)) {
			const bytes = new Uint8Array(await image.arrayBuffer());
			const embedded = /\.png$/i.test(image.name)
				? await pdf.embedPng(bytes)
				: await pdf.embedJpg(bytes);
			pdf.addPage([embedded.width, embedded.height]).drawImage(embedded, {
				x: 0,
				y: 0,
				width: embedded.width,
				height: embedded.height
			});
		}
		const saved = await pdf.save();
		return new File([saved as BlobPart], `${name.replace(/\.pdf$/i, '')}.pdf`, {
			type: 'application/pdf'
		});
	}
}
