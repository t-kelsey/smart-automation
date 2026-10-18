import type { PipelineConfig } from '#lib/domain/documents.ts';
import {
	PIPELINE_STAGES,
	type JobStatus,
	type Pipeline,
	type PipelineJob,
	type PipelineReportStep,
	type PipelineStage,
	type PipelineStatus
} from '#lib/domain/pipelines.ts';

/** `pipeline_runs.status` as the API sends it. */
export type ApiRunStatus = 'new' | 'running' | 'completed' | 'failed' | 'stopped';

/** `exec_stages.status` as the API sends it (ADR-0040). */
export type ApiStageStatus = 'new' | 'running' | 'success' | 'failed' | 'stopped';

export interface ApiExecStage {
	id: string;
	type: string;
	position: number | null;
	/** Absent only on rows recorded before stages had a status. */
	status?: ApiStageStatus;
	data: Record<string, unknown> | null;
	error?: string | null;
	model?: string | null;
	duration_ms?: number | null;
}

export interface ApiReportStep {
	/** e.g. `1 filter pages`; the leading number is the stage's position. */
	step: string;
	model_requested?: string;
	effort?: string;
	wall_seconds?: number;
	api_seconds?: number;
	calls?: number;
	input_tokens?: number;
	output_tokens?: number;
	cache_read_tokens?: number;
	cache_create_tokens?: number;
	total_tokens?: number;
	cost_usd?: number;
}

/** `GET /api/pipeline_runs/:id`. */
export interface ApiPipelineRun {
	id: string;
	document_id: string;
	status: ApiRunStatus;
	config: Partial<PipelineConfig> | null;
	current_stage?: string | null;
	error?: string | null;
	started_at?: string | null;
	finished_at?: string | null;
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
		case 'stopped':
			return 'skipped';
		default:
			return 'pending';
	}
}

export function toJobStatus(status: ApiStageStatus): JobStatus {
	switch (status) {
		case 'new':
			return 'pending';
		case 'stopped':
			return 'skipped';
		default:
			return status;
	}
}

/**
 * Builds the stages and jobs of a run. A job with an `exec_stages` row takes the row's status
 * (ADR-0040). Jobs without one (extract/transform before the split result, rows from before
 * stages had a status) are derived from the run's status: while the run is going, everything of
 * the first unfinished stage is running and the rest is pending; once it has failed, the
 * unfinished jobs of that stage failed and the later stages never ran.
 */
export function mapPipeline(run: ApiPipelineRun, filename: string): Pipeline {
	const rows = run.exec_stages ?? [];
	const steps = run.report?.data?.steps ?? [];
	const config = run.config ?? {};

	const boreholes = (rows.find((r) => r.type === 'split')?.data?.boreholes ?? []) as {
		label?: string;
	}[];
	const rowOf = (type: string, position: number | null) =>
		rows.find((r) => r.type === type && (r.position ?? null) === position);
	/** A row without a status was only recorded once its stage had finished. */
	const finished = (type: string, position: number | null) =>
		rows.some(
			(r) =>
				r.type === type &&
				(r.position ?? null) === position &&
				(r.status === undefined || r.status === 'success')
		);

	/** The borehole id the pipeline recorded in the stage's result, if it did. */
	function boreholeIdOf(type: string, position: number): string | undefined {
		const data = rows.find((r) => r.type === type && r.position === position)?.data;
		const id = data?.borehole_id;
		return typeof id === 'string' ? id : undefined;
	}

	/** The jobs of a stage with `done` telling which of them have a result. */
	function jobsOf(
		type: string
	): { name: string; done: boolean; position: number | null; boreholeId?: string }[] {
		if (type === 'filter')
			return [{ name: 'Filter pages', done: finished('filter', null), position: null }];
		if (type === 'split')
			return [{ name: 'Split boreholes', done: finished('split', null), position: null }];
		const verb = type === 'extract' ? 'Extract' : 'Transform';
		// Until the split result is there, the number of boreholes is unknown.
		if (!finished('split', null)) return [{ name: verb, done: false, position: null }];
		return boreholes.map((b, i) => ({
			name: `${verb} ${b.label ?? `borehole ${i + 1}`}`,
			done: finished(type, i + 1),
			position: i + 1,
			boreholeId: type === 'transform' ? boreholeIdOf(type, i + 1) : undefined
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
				const row = rowOf(stage.key, job.position);
				let status: JobStatus;
				if (row?.status) status = toJobStatus(row.status);
				else if (job.done) status = 'success';
				else if (run.status === 'new') status = 'pending';
				else if (run.status === 'completed') status = 'skipped';
				else if (active === -1 || index < active) status = 'skipped';
				else if (index > active) status = run.status === 'failed' ? 'skipped' : 'pending';
				else status = run.status === 'failed' ? 'failed' : 'running';
				return {
					id: `${stage.key}-${i + 1}`,
					execStageId: row?.id,
					name: job.name,
					status,
					model: row?.model ?? report?.model_requested ?? configured?.model,
					error: row?.error ?? undefined,
					boreholeId: job.done ? job.boreholeId : undefined,
					position: job.position ?? undefined,
					durationSeconds:
						row?.duration_ms != null
							? row.duration_ms / 1000
							: single
								? report?.wall_seconds
								: undefined
				};
			})
		};
	});

	// A failed run is only partially failed when some borehole still made it through the transform.
	const transformJobs = stages.find((s) => s.key === 'transform')?.jobs ?? [];
	const status =
		run.status === 'failed' && transformJobs.some((j) => j.status === 'success')
			? 'partial'
			: toPipelineStatus(run.status);

	return {
		id: run.id,
		documentId: run.document_id,
		filename,
		status,
		createdAt: new Date(run.inserted_at),
		updatedAt: new Date(run.updated_at),
		config,
		stages,
		report: steps.length > 0 ? steps.map(toReportStep) : undefined
	};
}

/** `1 filter pages` → the `filter` stage; unknown names keep their text as the label. */
function toReportStep(step: ApiReportStep): PipelineReportStep {
	const stage = PIPELINE_STAGES[Number.parseInt(step.step, 10) - 1];
	return {
		key: stage?.key,
		label: stage?.label ?? step.step,
		model: step.model_requested,
		effort: step.effort,
		wallSeconds: step.wall_seconds,
		apiSeconds: step.api_seconds,
		calls: step.calls,
		inputTokens: step.input_tokens,
		outputTokens: step.output_tokens,
		cacheReadTokens: step.cache_read_tokens,
		cacheCreateTokens: step.cache_create_tokens,
		totalTokens:
			step.total_tokens ??
			sumDefined([
				step.input_tokens,
				step.output_tokens,
				step.cache_read_tokens,
				step.cache_create_tokens
			]),
		costUsd: step.cost_usd
	};
}

function sumDefined(values: (number | undefined)[]): number | undefined {
	const defined = values.filter((v): v is number => v !== undefined);
	return defined.length > 0 ? defined.reduce((a, b) => a + b, 0) : undefined;
}
