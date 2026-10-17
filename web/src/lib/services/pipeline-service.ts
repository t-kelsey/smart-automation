import type { Pipeline } from '#lib/domain/pipelines.ts';
import type { PipelineRepository } from '#lib/repositories/pipeline-repository.ts';

export class PipelineNotFoundError extends Error {
	constructor(readonly id: string) {
		super(`Pipeline ${id} not found`);
		this.name = 'PipelineNotFoundError';
	}
}

/** Use cases for extraction pipeline runs. */
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
}
