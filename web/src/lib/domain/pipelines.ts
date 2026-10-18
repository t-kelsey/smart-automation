import type { PipelineConfig } from './documents';

export type JobStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

/** A stage's or a whole pipeline's status; `partial` means some jobs failed while others passed. */
export type PipelineStatus = JobStatus | 'partial';

export interface PipelineJob {
	id: string;
	/** The `exec_stages` row with the job's result; unset while the job has none. */
	execStageId?: string;
	name: string;
	status: JobStatus;
	/** Seconds; only known for jobs that are a whole stage on their own. */
	durationSeconds?: number;
	model?: string;
	error?: string;
	/** The borehole a transform job produced, once it has finished. */
	boreholeId?: string;
	/** 1-based borehole index of an extract/transform job; unset for whole-document jobs. */
	position?: number;
}

export interface PipelineStage {
	key: string;
	label: string;
	jobs: PipelineJob[];
	/** Model and effort the stage runs with (from the report once it exists, else from the config). */
	model?: string;
	effort?: string;
	/** Wall time of the whole stage in seconds, from the report. */
	durationSeconds?: number;
}

/** One pipeline run: the extraction of a single uploaded document. */
export interface Pipeline {
	/** The id of the run (`pipeline_runs.id`). */
	id: string;
	documentId: string;
	filename: string;
	status: PipelineStatus;
	createdAt: Date;
	/** Last status change; the end of the run once it has finished. */
	updatedAt: Date;
	config: Partial<PipelineConfig>;
	stages: PipelineStage[];
	/** Per-step usage the pipeline reports once the run has ended; unset until then. */
	report?: PipelineReportStep[];
}

/** One step of a run's report: wall time plus the summed usage of its model calls. */
export interface PipelineReportStep {
	/** Stage key (`filter`, `split`, …) when the step name could be matched to one. */
	key?: string;
	label: string;
	model?: string;
	effort?: string;
	wallSeconds?: number;
	apiSeconds?: number;
	calls?: number;
	inputTokens?: number;
	outputTokens?: number;
	cacheReadTokens?: number;
	cacheCreateTokens?: number;
	totalTokens?: number;
	costUsd?: number;
}

/** Stages of the extraction pipeline in processing order (the `type` of `exec_stages`). */
export const PIPELINE_STAGES = [
	{ key: 'filter', label: 'Filter pages' },
	{ key: 'split', label: 'Split boreholes' },
	{ key: 'extract', label: 'Extract' },
	{ key: 'transform', label: 'Transform' }
] as const;

/**
 * Failed (or partial, when other jobs passed) beats running beats pending; all skipped counts as
 * skipped, otherwise success.
 */
export function statusOf(jobs: Pick<PipelineJob, 'status'>[]): PipelineStatus {
	if (jobs.length === 0) return 'pending';
	if (jobs.some((j) => j.status === 'failed')) {
		return jobs.some((j) => j.status === 'success') ? 'partial' : 'failed';
	}
	if (jobs.some((j) => j.status === 'running')) return 'running';
	if (jobs.every((j) => j.status === 'pending')) return 'pending';
	if (jobs.some((j) => j.status === 'pending')) return 'running';
	if (jobs.every((j) => j.status === 'skipped')) return 'skipped';
	return 'success';
}

export function stageStatus(stage: PipelineStage): PipelineStatus {
	return statusOf(stage.jobs);
}

/**
 * Whether the job can be redone on its own: a failed or stopped extract/transform job of a
 * finished run whose input exists (the split result, or the borehole's extraction). Failed
 * filter/split jobs are retried by retrying the whole pipeline.
 */
export function canRetryJob(pipeline: Pipeline, stage: PipelineStage, job: PipelineJob): boolean {
	if (isActive(pipeline) || !job.execStageId || job.position === undefined) return false;
	if (job.status !== 'failed' && job.status !== 'skipped') return false;
	const jobsOf = (key: string) => pipeline.stages.find((s) => s.key === key)?.jobs ?? [];
	if (stage.key === 'extract') return jobsOf('split').every((j) => j.status === 'success');
	if (stage.key === 'transform') {
		return jobsOf('extract').some((j) => j.position === job.position && j.status === 'success');
	}
	return false;
}

export function pipelineStatus(pipeline: Pipeline): PipelineStatus {
	return pipeline.status;
}

/** True while the pipeline can still change, so the UI keeps polling. */
export function isActive(pipeline: Pipeline): boolean {
	return pipeline.status === 'pending' || pipeline.status === 'running';
}

/** Seconds from the start to the end of the run, or to `now` while it is still going. */
export function pipelineDuration(pipeline: Pipeline, now = new Date()): number {
	const end = isActive(pipeline) ? now : pipeline.updatedAt;
	return Math.max(0, (end.getTime() - pipeline.createdAt.getTime()) / 1000);
}

export function countByStatus(jobs: Pick<PipelineJob, 'status'>[]): Record<JobStatus, number> {
	const counts: Record<JobStatus, number> = {
		pending: 0,
		running: 0,
		success: 0,
		failed: 0,
		skipped: 0
	};
	for (const job of jobs) counts[job.status]++;
	return counts;
}

export function formatDuration(seconds: number): string {
	const total = Math.round(seconds);
	if (total < 60) return `${total}s`;
	const minutes = Math.floor(total / 60);
	return `${minutes}m ${String(total % 60).padStart(2, '0')}s`;
}

/** `00:09:37`, as GitLab shows pipeline durations. */
export function formatClock(seconds: number): string {
	const total = Math.round(seconds);
	const part = (n: number) => String(n).padStart(2, '0');
	return `${part(Math.floor(total / 3600))}:${part(Math.floor((total % 3600) / 60))}:${part(total % 60)}`;
}

/** "17 hours ago". */
export function formatRelative(date: Date, now = new Date()): string {
	const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
	const seconds = Math.round((date.getTime() - now.getTime()) / 1000);
	const units: [Intl.RelativeTimeFormatUnit, number][] = [
		['day', 86400],
		['hour', 3600],
		['minute', 60]
	];
	for (const [unit, size] of units) {
		if (Math.abs(seconds) >= size) return formatter.format(Math.trunc(seconds / size), unit);
	}
	return formatter.format(seconds, 'second');
}

/** One executed job (`exec_stages` row of the API): the step's result with its metadata. */
export interface JobDetail {
	id: string;
	/** Stage key: `filter`, `split`, `extract` or `transform`. */
	type: string;
	/** Borehole index within the run for `extract`/`transform`; unset for whole-document steps. */
	position?: number;
	/** The pipeline run this job belongs to (`pipeline_runs.id`). */
	runId: string;
	documentIds: string[];
	createdAt: Date;
	status: JobStatus;
	/** Why the job failed or was stopped. */
	error?: string;
	model?: string;
	effort?: string;
	startedAt?: Date;
	finishedAt?: Date;
	durationSeconds?: number;
	/** Tokens, cost and calls of the job's model requests, as the pipeline reported them. */
	usage?: Record<string, unknown>;
	/** The step's JSON output as stored; `null` until the job has one. */
	data: unknown;
}
