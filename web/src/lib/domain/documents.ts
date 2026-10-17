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

/** Where the models run: the Claude CLI, or a local vision model (Ollama, data stays on the machine). */
export const PIPELINE_PROVIDERS = ['claude', 'local'] as const;
export type PipelineProvider = (typeof PIPELINE_PROVIDERS)[number];

/** Selectable models per provider (`bem/pipeline/config.py`). */
export const PIPELINE_MODELS = {
	claude: ['haiku', 'sonnet', 'opus'],
	local: ['qwen3-vl:2b', 'qwen3-vl:4b']
} as const satisfies Record<PipelineProvider, readonly string[]>;
export type PipelineModel = string;

export const PIPELINE_EFFORTS = ['low', 'medium', 'high'] as const;
export type PipelineEffort = (typeof PIPELINE_EFFORTS)[number];

/**
 * The `config` of the pipeline's `POST /execute`: the provider plus per step model and effort.
 * The local provider ignores the effort.
 */
export type PipelineConfig = { provider: PipelineProvider } & Record<
	PipelineStep,
	{ model: PipelineModel; effort: PipelineEffort }
>;

/** The pipeline's own defaults (`bem/pipeline/config.py`). */
export function createDefaultPipelineConfig(provider: PipelineProvider = 'claude'): PipelineConfig {
	if (provider === 'local') {
		return {
			provider,
			filter: { model: 'qwen3-vl:2b', effort: 'high' },
			split: { model: 'qwen3-vl:2b', effort: 'medium' },
			extract: { model: 'qwen3-vl:4b', effort: 'high' },
			transform: { model: 'qwen3-vl:4b', effort: 'high' }
		};
	}
	return {
		provider,
		filter: { model: 'haiku', effort: 'high' },
		split: { model: 'haiku', effort: 'medium' },
		extract: { model: 'sonnet', effort: 'high' },
		transform: { model: 'haiku', effort: 'high' }
	};
}
