import type {
	BaseComposition,
	Composition,
	MaterialKey,
	Proportion,
	SecondaryComponent
} from './types.ts';

/**
 * Best-effort mapping of free-text petrography (English and German) to a DIN 4023 composition.
 * Used for data that has no structured composition yet; returns `undefined` when nothing matches.
 */

const rockAndGeology: [RegExp, MaterialKey][] = [
	[/claystone|tonstein/i, 'claystone'],
	[/siltstone|schluffstein/i, 'siltstone'],
	[/sandstone|sandstein/i, 'sandstone'],
	[/conglomerate|konglomerat/i, 'conglomerate'],
	[/breccia|brekzie/i, 'breccia'],
	[/marl ?stone|mergelstein|\bmarl\b|\bmergel\b/i, 'marlstone'],
	[/limestone|kalkstein/i, 'limestone'],
	[/dolomit/i, 'dolomite'],
	[/anhydrit/i, 'anhydrite'],
	[/gypsum|\bgips\b/i, 'gypsum'],
	[/rock salt|salzgestein/i, 'rockSalt'],
	[/tuff/i, 'tuff'],
	[/hard coal|steinkohle/i, 'hardCoal'],
	[/quartzite|quarzit/i, 'quartzite'],
	[/basalt|volcanic rock|vulkanit/i, 'volcanic'],
	[/granit|plutonit/i, 'plutonic'],
	[/gneis/i, 'massiveMetamorphic'],
	[/schist|schiefer|phyllit/i, 'foliatedMetamorphic'],
	[/topsoil|mutterboden|oberboden/i, 'topsoil'],
	[/made ground|\bfill\b|auffüllung|anthropogen/i, 'anthropogenic'],
	[/varved clay|bänderton/i, 'bandedClay'],
	[/loess loam|lößlehm|lösslehm/i, 'loessLoam'],
	[/loess|löß|löss/i, 'loess'],
	[/slope debris|hangschutt/i, 'slopeDebris'],
	[/till|geschiebe/i, 'tillLoam'],
	[/lignite|braunkohle/i, 'lignite'],
	[/volcanic ash|vulkanische asche/i, 'volcanicAsh']
];

/** Nouns (main component) and adjectives (minor component) per soil family. */
const soilFamilies: {
	noun: RegExp;
	adjective: RegExp;
	base: MaterialKey;
	variants?: Record<string, MaterialKey>;
}[] = [
	{
		noun: /\bgravel\b|\bkies\b/i,
		adjective: /gravelly|kiesig/i,
		base: 'gravel',
		variants: { coarse: 'coarseGravel', medium: 'mediumGravel', fine: 'fineGravel' }
	},
	{
		noun: /\bsand\b/i,
		adjective: /sandy|sandig/i,
		base: 'sand',
		variants: { coarse: 'coarseSand', medium: 'mediumSand', fine: 'fineSand' }
	},
	{
		noun: /\bsilt\b|\bschluff\b/i,
		adjective: /silty|schluffig/i,
		base: 'silt',
		variants: { coarse: 'coarseSilt' }
	},
	{ noun: /\bclay\b|\bton\b/i, adjective: /clayey|tonig/i, base: 'clay' },
	{ noun: /\bpeat\b|\btorf\b|humus/i, adjective: /peaty|humous|torfig|humos/i, base: 'peat' }
];

const grainWords: [string, RegExp][] = [
	['coarse', /coarse|grob/i],
	['medium', /medium|mittel/i],
	['fine', /\bfine\b|fein/i]
];

function variantOf(text: string, family: (typeof soilFamilies)[number]): MaterialKey {
	// Only grain words right in front of the noun count; "medium dense" describes the density.
	const index = text.search(family.noun);
	const before =
		text
			.slice(Math.max(0, index - 20), index)
			.split(/[,;.]/)
			.pop() ?? '';
	const found = grainWords.filter(([, re]) => re.test(before));
	// "fine to medium sand" has no single grain size, keep the plain soil.
	return found.length === 1 ? (family.variants?.[found[0][0]] ?? family.base) : family.base;
}

function proportionBefore(text: string, index: number): Proportion {
	const before = text.slice(Math.max(0, index - 12), index);
	if (/slightly|weakly|schwach/i.test(before)) return 'weak';
	if (/very |strongly |highly |stark /i.test(before)) return 'strong';
	return 'normal';
}

function parseSoil(text: string): BaseComposition | undefined {
	const nouns = soilFamilies
		.map((family) => ({ family, index: text.search(family.noun) }))
		.filter((match) => match.index >= 0)
		.sort((a, b) => a.index - b.index);
	if (!nouns.length) return undefined;

	const main = nouns[0].family;
	const secondary: SecondaryComponent[] = soilFamilies
		.filter((family) => family !== main)
		.map((family) => ({ family, index: text.search(family.adjective) }))
		.filter((match) => match.index >= 0)
		.sort((a, b) => a.index - b.index)
		.map(({ family, index }) => ({
			material: family.base,
			proportion: proportionBefore(text, index)
		}));

	return { main: variantOf(text, main), ...(secondary.length ? { secondary } : {}) };
}

export function parseComposition(text: string | null | undefined): Composition | undefined {
	if (!text) return undefined;

	const special = rockAndGeology.find(([re]) => re.test(text));
	if (special?.[1] === 'anthropogenic') {
		const breakdown = parseSoil(text);
		return { main: 'anthropogenic', ...(breakdown ? { breakdown } : {}) };
	}
	if (special) return { main: special[1] };
	return parseSoil(text);
}
