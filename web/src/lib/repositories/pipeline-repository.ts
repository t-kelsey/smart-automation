import type { PipelineConfig } from '#lib/domain/documents.ts';
import type { JobDetail, Pipeline, PipelineStatus } from '#lib/domain/pipelines.ts';

/** What the API answers when a run is submitted. */
export interface StartedPipeline {
	/** The id of the new pipeline run. */
	id: string;
	/** `running` if the pipeline accepted it, `pending` if no pipeline is configured, `failed` if it refused. */
	status: PipelineStatus;
}

/** Data access for extraction pipeline runs. */
export interface PipelineRepository {
	/** All pipelines, newest first. */
	list(): Promise<Pipeline[]>;
	/** Returns the pipeline run, or `null` if there is none. */
	get(id: string): Promise<Pipeline | null>;
	/** Returns the executed job (`exec_stages` row), or `null` if there is none. */
	getJob(id: string): Promise<JobDetail | null>;
	/** Submits an uploaded document to the pipeline with the given per step config. */
	start(documentId: string, config: PipelineConfig): Promise<StartedPipeline>;
}
