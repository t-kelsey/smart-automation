import type { PipelineConfig } from '#lib/domain/documents.ts';
import {
	PIPELINE_STAGES,
	type JobStatus,
	type Pipeline,
	type PipelineJob,
	type PipelineStage,
	type PipelineStatus
} from '#lib/domain/pipelines.ts';

/** `pipeline_runs.status` as the API sends it. */
export type ApiRunStatus = 'new' | 'running' | 'completed' | 'failed';

export interface ApiExecStage {
	type: string;
	position: number | null;
	data: Record<string, unknown> | null;
}

export interface ApiReportStep {
	/** e.g. `1 filter pages`; the leading number is the stage's position. */
	step: string;
	model_requested?: string;
	effort?: string;
	wall_seconds?: number;
}

/** `GET /api/pipeline_runs/:id`. */
export interface ApiPipelineRun {
	id: string;
	document_id: string;
	status: ApiRunStatus;
	config: Partial<PipelineConfig> | null;
	inserted_at: string;
	updated_at: string;
	exec_stages?: ApiExecStage[];
	report?: { data?: { steps?: ApiReportStep[] } } | null;
}

export function toPipelineStatus(status: ApiRunStatus): PipelineStatus {
	switch (status) {
		case 'running':
			return 'running';
		case 'completed':
			return 'success';
		case 'failed':
			return 'failed';
		default:
			return 'pending';
	}
}

/**
 * Builds the stages and jobs of a run. The pipeline only reports a stage once it has finished
 * (`exec_stages`), so what is still missing is derived from the run's status: while the run is
 * going, everything of the first unfinished stage is running and the rest is pending; once it has
 * failed, the unfinished jobs of that stage failed and the later stages never ran.
 */
export function mapPipeline(run: ApiPipelineRun, filename: string): Pipeline {
	const rows = run.exec_stages ?? [];
	const steps = run.report?.data?.steps ?? [];
	const config = run.config ?? {};

	const boreholes = (rows.find((r) => r.type === 'split')?.data?.boreholes ?? []) as {
		label?: string;
	}[];
	const finished = (type: string, position: number | null) =>
		rows.some((r) => r.type === type && (r.position ?? null) === position);

	/** The jobs of a stage with `done` telling which of them have a result. */
	function jobsOf(type: string): { name: string; done: boolean }[] {
		if (type === 'filter') return [{ name: 'Filter pages', done: finished('filter', null) }];
		if (type === 'split') return [{ name: 'Split boreholes', done: finished('split', null) }];
		const verb = type === 'extract' ? 'Extract' : 'Transform';
		// Until the split result is there, the number of boreholes is unknown.
		if (!rows.some((r) => r.type === 'split')) return [{ name: verb, done: false }];
		return boreholes.map((b, i) => ({
			name: `${verb} ${b.label ?? `borehole ${i + 1}`}`,
			done: finished(type, i + 1)
		}));
	}

	let active = -1; // index of the first stage that is not finished
	const stages: PipelineStage[] = PIPELINE_STAGES.map((stage, index) => {
		const jobs = jobsOf(stage.key);
		if (active === -1 && jobs.some((j) => !j.done)) active = index;
		const report = steps.find((s) => Number.parseInt(s.step, 10) === index + 1);
		const configured = config[stage.key];
		const single = jobs.length === 1;
		return {
			key: stage.key,
			label: stage.label,
			model: report?.model_requested ?? configured?.model,
			effort: report?.effort ?? configured?.effort,
			durationSeconds: report?.wall_seconds,
			jobs: jobs.map((job, i): PipelineJob => {
				let status: JobStatus;
				if (job.done) status = 'success';
				else if (run.status === 'new') status = 'pending';
				else if (run.status === 'completed') status = 'skipped';
				else if (active === -1 || index < active) status = 'skipped';
				else if (index > active) status = run.status === 'failed' ? 'skipped' : 'pending';
				else status = run.status === 'failed' ? 'failed' : 'running';
				return {
					id: `${stage.key}-${i + 1}`,
					name: job.name,
					status,
					model: report?.model_requested ?? configured?.model,
					durationSeconds: single ? report?.wall_seconds : undefined
				};
			})
		};
	});

	return {
		id: run.id,
		documentId: run.document_id,
		filename,
		status: toPipelineStatus(run.status),
		createdAt: new Date(run.inserted_at),
		updatedAt: new Date(run.updated_at),
		config,
		stages
	};
}
