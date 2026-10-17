export type JobStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

/** A stage's or a whole pipeline's status, derived from its jobs. */
export type PipelineStatus = JobStatus;

export interface PipelineJob {
	id: string;
	name: string;
	status: JobStatus;
	/** Seconds; absent while the job has not finished. */
	durationSeconds?: number;
	model?: string;
	error?: string;
}

export interface PipelineStage {
	key: string;
	label: string;
	jobs: PipelineJob[];
}

/** One pipeline run: the extraction of a single uploaded document. */
export interface Pipeline {
	/** The id of the document the pipeline processes. */
	id: string;
	filename: string;
	createdAt: Date;
	/** Who uploaded the document. */
	createdBy: string;
	stages: PipelineStage[];
}

/** Stages of the extraction pipeline in processing order. */
export const PIPELINE_STAGES = [
	{ key: 'filter_pages', label: 'Filter pages' },
	{ key: 'split_boreholes', label: 'Split boreholes' },
	{ key: 'extract', label: 'Extract' },
	{ key: 'transform', label: 'Transform' },
	{ key: 'store', label: 'Store' }
] as const;

/** Failed beats running beats pending; all skipped counts as skipped, otherwise success. */
export function statusOf(jobs: Pick<PipelineJob, 'status'>[]): PipelineStatus {
	if (jobs.length === 0) return 'pending';
	if (jobs.some((j) => j.status === 'failed')) return 'failed';
	if (jobs.some((j) => j.status === 'running')) return 'running';
	if (jobs.every((j) => j.status === 'pending')) return 'pending';
	if (jobs.some((j) => j.status === 'pending')) return 'running';
	if (jobs.every((j) => j.status === 'skipped')) return 'skipped';
	return 'success';
}

export function stageStatus(stage: PipelineStage): PipelineStatus {
	return statusOf(stage.jobs);
}

export function pipelineStatus(pipeline: Pipeline): PipelineStatus {
	return statusOf(pipeline.stages.flatMap((s) => s.jobs));
}

/** Total job time in seconds (jobs of a stage may run in parallel, so stages are summed by their longest job). */
export function pipelineDuration(pipeline: Pipeline): number {
	return pipeline.stages.reduce(
		(sum, stage) => sum + Math.max(0, ...stage.jobs.map((j) => j.durationSeconds ?? 0)),
		0
	);
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

export function initials(name: string): string {
	const words = name.trim().split(/\s+/);
	return (
		words.length > 1 ? words[0][0] + words[words.length - 1][0] : name.slice(0, 2)
	).toUpperCase();
}
