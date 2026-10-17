import {
	PIPELINE_STAGES,
	type JobStatus,
	type Pipeline,
	type PipelineJob
} from '#lib/domain/pipelines.ts';
import type { PipelineRepository } from '../pipeline-repository';

/**
 * Placeholder until the API exposes pipeline runs: deterministic fake pipelines that cover every
 * status. `progress` is how many stages are done; `failedAt` marks the stage that failed.
 */
interface Scenario {
	id: string;
	filename: string;
	minutesAgo: number;
	pages: number;
	boreholes: number;
	/** Stages fully done; the next one is running unless `failedAt` is set. */
	done: number;
	failedAt?: number;
}

const SCENARIOS: Scenario[] = [
	{
		id: '6f1c2a9e-0b1d-4c55-9a53-1a2b3c4d5e01',
		filename: 'SB_Tunnel_Nord_Bohrprofile.pdf',
		minutesAgo: 3,
		pages: 42,
		boreholes: 6,
		done: 2
	},
	{
		id: '6f1c2a9e-0b1d-4c55-9a53-1a2b3c4d5e02',
		filename: 'Sondages_Lot_3_2011.pdf',
		minutesAgo: 25,
		pages: 18,
		boreholes: 4,
		done: 5
	},
	{
		id: '6f1c2a9e-0b1d-4c55-9a53-1a2b3c4d5e03',
		filename: 'Geotecnia_Linea_9_scan.tif',
		minutesAgo: 70,
		pages: 31,
		boreholes: 5,
		done: 2,
		failedAt: 2
	},
	{
		id: '6f1c2a9e-0b1d-4c55-9a53-1a2b3c4d5e04',
		filename: 'BH-2041.png',
		minutesAgo: 180,
		pages: 1,
		boreholes: 1,
		done: 5
	},
	{
		id: '6f1c2a9e-0b1d-4c55-9a53-1a2b3c4d5e05',
		filename: 'Baugrundgutachten_Stuttgart21.docx',
		minutesAgo: 600,
		pages: 64,
		boreholes: 9,
		done: 5
	},
	{
		id: '6f1c2a9e-0b1d-4c55-9a53-1a2b3c4d5e06',
		filename: 'Bohrung_KB3_Altdaten.pdf',
		minutesAgo: 1500,
		pages: 7,
		boreholes: 0,
		done: 1,
		failedAt: 1
	},
	{
		id: '6f1c2a9e-0b1d-4c55-9a53-1a2b3c4d5e07',
		filename: 'Report_Sector_B.pdf',
		minutesAgo: 0.2,
		pages: 25,
		boreholes: 3,
		done: 0
	}
];

function stageStatus(stageIndex: number, s: Scenario): JobStatus {
	if (stageIndex < s.done) return 'success';
	if (stageIndex === s.failedAt) return 'failed';
	if (s.failedAt !== undefined && stageIndex > s.failedAt) return 'pending';
	return stageIndex === s.done ? 'running' : 'pending';
}

function jobs(stageIndex: number, s: Scenario): PipelineJob[] {
	const stage = PIPELINE_STAGES[stageIndex];
	const status = stageStatus(stageIndex, s);
	const names: { name: string; model: string }[] = [];
	if (stage.key === 'filter_pages') {
		for (let from = 1; from <= s.pages; from += 10) {
			names.push({ name: `Pages ${from}–${Math.min(from + 9, s.pages)}`, model: 'haiku' });
		}
	} else if (stage.key === 'split_boreholes') {
		names.push({ name: 'Split into boreholes', model: 'haiku' });
	} else {
		const model = stage.key === 'extract' ? 'sonnet' : stage.key === 'transform' ? 'haiku' : '';
		const verb =
			stage.key === 'extract' ? 'Extract' : stage.key === 'transform' ? 'Transform' : 'Store';
		// A failed pipeline never got as far as knowing its boreholes for later stages.
		const count = Math.max(s.boreholes, status === 'failed' ? 1 : 0);
		for (let i = 1; i <= count; i++) names.push({ name: `${verb} borehole ${i}`, model });
	}

	return names.map(({ name, model }, i) => {
		let jobStatus = status;
		// While a stage runs, its first jobs are done and the rest are queued.
		if (status === 'running') {
			const finished = Math.floor(names.length / 2);
			jobStatus = i < finished ? 'success' : i === finished ? 'running' : 'pending';
		}
		// In a failed stage, the last job fails and the others went through.
		if (status === 'failed') jobStatus = i === names.length - 1 ? 'failed' : 'success';
		const finished = jobStatus === 'success' || jobStatus === 'failed';
		return {
			id: `${stage.key}-${i + 1}`,
			name,
			status: jobStatus,
			durationSeconds: finished ? 8 + ((i * 7 + stageIndex * 13) % 40) : undefined,
			model: model || undefined,
			error: jobStatus === 'failed' ? 'claude CLI returned no structured output' : undefined
		};
	});
}

function build(s: Scenario): Pipeline {
	return {
		id: s.id,
		filename: s.filename,
		createdAt: new Date(Date.now() - s.minutesAgo * 60_000),
		createdBy: 'Jane Doe',
		stages: PIPELINE_STAGES.map((stage, i) => ({
			key: stage.key,
			label: stage.label,
			jobs: jobs(i, s)
		}))
	};
}

export class MockPipelineRepository implements PipelineRepository {
	async list(): Promise<Pipeline[]> {
		return SCENARIOS.map(build).sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
	}

	async get(id: string): Promise<Pipeline | null> {
		const scenario = SCENARIOS.find((s) => s.id === id);
		return scenario ? build(scenario) : null;
	}
}
