import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { notify } from '#lib/components/toast/index.ts';
import { createDefaultPipelineConfig } from '#lib/domain/documents.ts';
import type { Pipeline } from '#lib/domain/pipelines.ts';
import type { PipelineService } from '#lib/services/index.ts';

/** Submits the pipeline's document again with the same config, which creates a new run. */
export async function retryPipeline(service: PipelineService, pipeline: Pipeline) {
	try {
		const run = await service.start(pipeline.documentId, {
			...createDefaultPipelineConfig(),
			...pipeline.config
		});
		if (run.status === 'running') {
			notify.success('Pipeline restarted.');
			await goto(resolve('/pipeline/[id]', { id: run.id }));
		} else if (run.status === 'failed') {
			notify.error('The pipeline refused the document.');
		} else {
			notify.error('No pipeline is configured, so the run did not start.');
		}
	} catch (e) {
		notify.fromError(e, 'Could not restart the pipeline');
	}
}
