import type { LithologyKey } from '#lib/domain/borehole.ts';

/** Label and SVG pattern id (see LithologyDefs.svelte) per lithology. */
export const lithologies: Record<LithologyKey, { label: string; patternId: string }> = {
	topsoil: { label: 'Topsoil', patternId: 'lith-topsoil' },
	fill: { label: 'Fill / made ground', patternId: 'lith-fill' },
	clay: { label: 'Clay', patternId: 'lith-clay' },
	silt: { label: 'Silt', patternId: 'lith-silt' },
	sand: { label: 'Sand', patternId: 'lith-sand' },
	gravel: { label: 'Gravel', patternId: 'lith-gravel' },
	sandstone: { label: 'Sandstone', patternId: 'lith-sandstone' },
	claystone: { label: 'Claystone', patternId: 'lith-claystone' },
	limestone: { label: 'Limestone', patternId: 'lith-limestone' },
	marl: { label: 'Marl', patternId: 'lith-marl' },
	unknown: { label: 'Unknown', patternId: 'lith-unknown' }
};
