import type { PipelineConfig } from '#lib/domain/documents.ts';
import type { JobDetail, Pipeline } from '#lib/domain/pipelines.ts';
import type { PipelineRepository, StartedPipeline } from '#lib/repositories/pipeline-repository.ts';

export class PipelineNotFoundError extends Error {
	constructor(readonly id: string) {
		super(`Pipeline ${id} not found`);
		this.name = 'PipelineNotFoundError';
	}
}

/** Use cases for extraction pipeline runs. */
export class JobNotFoundError extends Error {
	constructor(readonly id: string) {
		super(`Job ${id} not found`);
		this.name = 'JobNotFoundError';
	}
}

export class PipelineService {
	constructor(private readonly repository: PipelineRepository) {}

	list(): Promise<Pipeline[]> {
		return this.repository.list();
	}

	async get(id: string): Promise<Pipeline> {
		const pipeline = await this.repository.get(id);
		if (!pipeline) throw new PipelineNotFoundError(id);
		return pipeline;
	}

	async getJob(id: string): Promise<JobDetail> {
		const job = await this.repository.getJob(id);
		if (!job) throw new JobNotFoundError(id);
		return job;
	}

	/** Deletes a pipeline run, e.g. a stuck one. */
	delete(id: string): Promise<void> {
		return this.repository.delete(id);
	}

	/** Redoes one failed or stopped extract/transform job as a new job of the same run. */
	retryJob(execStageId: string): Promise<void> {
		return this.repository.retryJob(execStageId);
	}

	/** Submits an uploaded document to the pipeline with the chosen per step config. */
	start(documentId: string, config: PipelineConfig): Promise<StartedPipeline> {
		return this.repository.start(documentId, config);
	}
}
