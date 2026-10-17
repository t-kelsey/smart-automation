import type { Pipeline } from '#lib/domain/pipelines.ts';

/** Data access for extraction pipeline runs. */
export interface PipelineRepository {
	/** All pipelines, newest first. */
	list(): Promise<Pipeline[]>;
	/** Returns the pipeline of a document, or `null` if there is none. */
	get(id: string): Promise<Pipeline | null>;
}
