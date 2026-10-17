import type { BoreholeDocument } from './borehole';

/** Splits a borehole's documents into its original document (if any) and the additional files. */
export function splitDocuments(documents: BoreholeDocument[]): {
	original: BoreholeDocument | null;
	additional: BoreholeDocument[];
} {
	return {
		original: documents.find((doc) => doc.role === 'original') ?? null,
		additional: documents.filter((doc) => doc.role !== 'original')
	};
}

/** A raw document accepted by the API; the extraction pipeline processes it in the background. */
export interface UploadedDocument {
	id: string;
	filename: string;
	/** `pending` (stored, no pipeline configured), `processing`, `extracted`, `failed`, `reviewed`. */
	status: string;
}

/** Pipeline steps whose AI model and effort can be chosen, in processing order. */
export const PIPELINE_STEPS = [
	{ key: 'filter', label: 'Filter pages', hint: 'Finds the borehole log pages' },
	{ key: 'split', label: 'Split boreholes', hint: 'Separates the logs on those pages' },
	{ key: 'extract', label: 'Extract', hint: 'Reads depths, lithology and stratigraphy' },
	{ key: 'transform', label: 'Transform', hint: 'Standardises the result for the database' }
] as const;

export type PipelineStep = (typeof PIPELINE_STEPS)[number]['key'];

export const PIPELINE_MODELS = ['haiku', 'sonnet', 'opus'] as const;
export type PipelineModel = (typeof PIPELINE_MODELS)[number];

export const PIPELINE_EFFORTS = ['low', 'medium', 'high'] as const;
export type PipelineEffort = (typeof PIPELINE_EFFORTS)[number];

/** Per step model and effort, in the shape of the `config` of the pipeline's `POST /execute`. */
export type PipelineConfig = Record<PipelineStep, { model: PipelineModel; effort: PipelineEffort }>;

/** The pipeline's own defaults (`bem/pipeline/config.py`). */
export function createDefaultPipelineConfig(): PipelineConfig {
	return {
		filter: { model: 'haiku', effort: 'high' },
		split: { model: 'haiku', effort: 'medium' },
		extract: { model: 'sonnet', effort: 'high' },
		transform: { model: 'haiku', effort: 'high' }
	};
}
