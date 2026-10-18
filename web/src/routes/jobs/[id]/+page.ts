import { error } from '@sveltejs/kit';
import {
	DocumentNotFoundError,
	JobNotFoundError,
	PipelineNotFoundError,
	createServices
} from '#lib/services/index.ts';
import type { DocumentDetail } from '#lib/domain/borehole.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { pipelines, boreholes } = await createServices({ fetch });
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

	// A transform that succeeded leads to a borehole. It is the only borehole of the split-out
	// document of this job's borehole, i.e. the linked document with the fewest boreholes.
	let borehole: { id: string; name: string } | null = null;
	const failed = (job.data as { status?: unknown } | null)?.status === 'failed';
	if (job.type === 'transform' && !failed) {
		const documents = await Promise.all(
			job.documentIds.map((id) =>
				boreholes.getDocument(id).catch((e) => {
					if (e instanceof DocumentNotFoundError) return null;
					throw e;
				})
			)
		);
		const linked = documents
			.filter((d): d is DocumentDetail => d !== null && d.boreholes.length > 0)
			.sort((a, b) => a.boreholes.length - b.boreholes.length)[0];
		if (linked?.boreholes.length === 1) borehole = linked.boreholes[0];
	}
	return { job, pipeline, borehole, service: pipelines };
};
