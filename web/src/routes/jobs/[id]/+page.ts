import { error } from '@sveltejs/kit';
import { JobNotFoundError, PipelineNotFoundError, createServices } from '#lib/services/index.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { pipelines } = await createServices({ fetch });
	let job;
	try {
		job = await pipelines.getJob(params.id);
	} catch (e) {
		if (e instanceof JobNotFoundError) error(404, 'Job not found');
		throw e;
	}
	// The run is optional context; a job whose run is gone is still shown.
	const pipeline = await pipelines.get(job.runId).catch((e) => {
		if (e instanceof PipelineNotFoundError) return null;
		throw e;
	});
	return { job, pipeline };
};
