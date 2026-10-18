import { goto, invalidateAll } from '$app/navigation';
import { resolve } from '$app/paths';
import { notify } from '#lib/components/toast/index.ts';
import { createDefaultPipelineConfig } from '#lib/domain/documents.ts';
import type { Pipeline } from '#lib/domain/pipelines.ts';
import type { PipelineService } from '#lib/services/index.ts';

/** Redoes one failed or stopped job inside its run; the run goes back to `running`. */
export async function retryJob(service: PipelineService, job: { execStageId?: string }) {
	if (!job.execStageId) return;
	try {
		await service.retryJob(job.execStageId);
		notify.success('Job restarted.');
		await invalidateAll();
	} catch (e) {
		notify.fromError(e, 'Could not retry the job');
	}
}

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
