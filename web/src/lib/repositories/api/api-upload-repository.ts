import type { UploadedDocument } from '#lib/domain/documents.ts';
import { RepositoryError } from '../borehole-repository';
import type { UploadRepository } from '../upload-repository';
import type { ApiClientOptions } from './api-client';

interface ApiUploadedDocument {
	data: { id: string; original_filename: string; status: string };
}

/** `POST /documents` (multipart): stores the file and starts the extraction pipeline. */
export class ApiUploadRepository implements UploadRepository {
	constructor(private readonly options: ApiClientOptions) {}

	async upload(file: File): Promise<UploadedDocument> {
		const body = new FormData();
		body.append('file', file);
		let response: Response;
		try {
			response = await this.options.fetch(`${this.options.baseUrl}/documents`, {
				method: 'POST',
				headers: { accept: 'application/json' },
				body
			});
		} catch (cause) {
			throw new RepositoryError('API request failed: /documents', undefined, { cause });
		}
		if (!response.ok) {
			throw new RepositoryError(`API /documents returned ${response.status}`, response.status);
		}
		const { data } = (await response.json()) as ApiUploadedDocument;
		return { id: data.id, filename: data.original_filename, status: data.status };
	}
}
