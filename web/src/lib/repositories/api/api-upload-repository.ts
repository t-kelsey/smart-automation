import type { ProcessedDocument, UploadedDocument } from '#lib/domain/documents.ts';
import { RepositoryError } from '../borehole-repository';
import type { UploadRepository } from '../upload-repository';
import { ApiClient, type ApiClientOptions } from './api-client';

interface ApiUploadedDocument {
	data: { id: string; original_filename: string; status: string };
}

/** `GET /documents?sha256=` */
interface ApiProcessedDocuments {
	data: {
		id: string;
		original_filename: string;
		inserted_at: string;
		borehole_count: number;
		pipeline_runs: { id: string; status: string; inserted_at: string }[];
	}[];
}

/** `POST /documents` (multipart): stores the file and starts the extraction pipeline. */
export class ApiUploadRepository implements UploadRepository {
	constructor(private readonly options: ApiClientOptions) {}

	async findBySha256(sha256: string): Promise<ProcessedDocument[]> {
		const body = await new ApiClient(this.options).getJson<ApiProcessedDocuments>(
			`/documents?sha256=${encodeURIComponent(sha256)}`
		);
		return (body?.data ?? []).map((doc) => {
			const latest = doc.pipeline_runs.reduce<(typeof doc.pipeline_runs)[number] | null>(
				(newest, run) => (!newest || run.inserted_at > newest.inserted_at ? run : newest),
				null
			);
			return {
				id: doc.id,
				filename: doc.original_filename,
				uploadedAt: doc.inserted_at,
				boreholeCount: doc.borehole_count,
				latestRun: latest
					? { id: latest.id, status: latest.status, startedAt: latest.inserted_at }
					: null
			};
		});
	}

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
