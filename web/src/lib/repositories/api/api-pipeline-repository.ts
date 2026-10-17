import type { PipelineConfig } from '#lib/domain/documents.ts';
import type { Pipeline } from '#lib/domain/pipelines.ts';
import { RepositoryError } from '../borehole-repository';
import type { PipelineRepository, StartedPipeline } from '../pipeline-repository';
import { ApiClient, type ApiClientOptions } from './api-client';
import { mapPipeline, toPipelineStatus, type ApiPipelineRun } from './pipeline-mapper';

/** One entry of `GET /pipeline_runs`: no stages or report, but the document's filename. */
interface ApiPipelineRunListItem {
	id: string;
	document_filename: string;
}

/**
 * Pipeline runs from the API (ADR-0035 `pipeline_runs`): `GET /pipeline_runs` lists them,
 * `GET /pipeline_runs/:id` returns one with its `exec_stages` and report, `POST /pipeline_runs`
 * submits a document.
 */
export class ApiPipelineRepository implements PipelineRepository {
	private readonly client: ApiClient;

	constructor(private readonly options: ApiClientOptions) {
		this.client = new ApiClient(options);
	}

	async list(): Promise<Pipeline[]> {
		const body = await this.client.getJson<{ data: ApiPipelineRunListItem[] }>('/pipeline_runs');
		// The list has no stages, so every run is loaded in full for the stage overview.
		const pipelines = await Promise.all(
			(body?.data ?? []).map((run) => this.load(run.id, run.document_filename))
		);
		return pipelines
			.filter((p): p is Pipeline => p !== null)
			.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
	}

	async get(id: string): Promise<Pipeline | null> {
		return this.load(id);
	}

	/** The run in full; `filename` saves loading the document when the caller already knows it. */
	private async load(id: string, filename?: string): Promise<Pipeline | null> {
		const body = await this.client.getJson<{ data: ApiPipelineRun }>(
			`/pipeline_runs/${encodeURIComponent(id)}`,
			[404]
		);
		if (!body) return null;
		if (filename === undefined) {
			const document = await this.client.getJson<{ data: { original_filename: string } }>(
				`/documents/${encodeURIComponent(body.data.document_id)}`,
				[404]
			);
			filename = document?.data.original_filename ?? 'Deleted document';
		}
		return mapPipeline(body.data, filename);
	}

	async start(documentId: string, config: PipelineConfig): Promise<StartedPipeline> {
		const path = '/pipeline_runs';
		let response: Response;
		try {
			response = await this.options.fetch(`${this.options.baseUrl}${path}`, {
				method: 'POST',
				headers: { accept: 'application/json', 'content-type': 'application/json' },
				body: JSON.stringify({ document_id: documentId, config })
			});
		} catch (cause) {
			throw new RepositoryError(`API request failed: ${path}`, undefined, { cause });
		}
		if (!response.ok) {
			throw new RepositoryError(`API ${path} returned ${response.status}`, response.status);
		}
		const { data } = (await response.json()) as { data: ApiPipelineRun };
		return { id: data.id, status: toPipelineStatus(data.status) };
	}
}
