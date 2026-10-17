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
	[/kalktuff|calcareous tufa/i, 'calcTufa'],
	[/tuff/i, 'tuff'],
	[/hard coal|steinkohle/i, 'hardCoal'],
	[/quartzite|quarzit/i, 'quartzite'],
	[/basalt|volcanic rock|vulkanit/i, 'volcanic'],
	[/granit|plutonit/i, 'plutonic'],
	[/massige? metamorphit|gneis/i, 'massiveMetamorphic'],
	[/bl(ä|ae)ttrige? metamorphit|schist|schiefer|phyllit/i, 'foliatedMetamorphic'],
	[/kreidestein|\bchalk\b/i, 'chalk'],
	[/wiesenkalk|lake marl/i, 'lakeMarl'],
	[/\bmudde\b|sapropel/i, 'mud'],
	[/\bklei\b|schlick|marsh clay/i, 'marshClay'],
	[/hanglehm|slope loam/i, 'weatheringLoam'],
	[/topsoil|mutterboden|oberboden/i, 'topsoil'],
	[/made ground|\bfill\b|auffüllung|anthropogen/i, 'anthropogenic'],
	[/varved clay|bänderton/i, 'bandedClay'],
	[/loess loam|lößlehm|lösslehm/i, 'loessLoam'],
	[/loess|löß|löss/i, 'loess'],
	[/slope debris|hangschutt/i, 'slopeDebris'],
	[/geschiebemergel/i, 'tillMarl'],
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
		noun: /\bgravel\b|\b(?:grob|mittel|fein)?kies\b/i,
		adjective: /gravelly|(?:grob|mittel|fein)?kiesig/i,
		base: 'gravel',
		variants: { coarse: 'coarseGravel', medium: 'mediumGravel', fine: 'fineGravel' }
	},
	{
		noun: /\bsand\b|\b(?:grob|mittel|fein)sand\b/i,
		adjective: /sandy|(?:grob|mittel|fein)?sandig/i,
		base: 'sand',
		variants: { coarse: 'coarseSand', medium: 'mediumSand', fine: 'fineSand' }
	},
	{
		noun: /\bsilt\b|\b(?:grob)?schluff\b/i,
		adjective: /silty|(?:grob)?schluffig/i,
		base: 'silt',
		variants: { coarse: 'coarseSilt' }
	},
	{ noun: /\bclay\b|\bton\b/i, adjective: /clayey|tonig/i, base: 'clay' },
	{ noun: /\bpeat\b|\btorf\b|humus/i, adjective: /peaty|humous|torfig|humos/i, base: 'peat' },
	{ noun: /\bcobbles?\b|\bsteine?\b/i, adjective: /cobbly|steinig/i, base: 'cobble' },
	{
		noun: /\bboulders?\b|\bbl(?:ö|oe)cke?\b|\bblock\b/i,
		adjective: /bouldery|mit bl(?:ö|oe)cken?/i,
		base: 'boulder'
	}
];

const grainWords: [string, RegExp][] = [
	['coarse', /coarse|grob/i],
	['medium', /medium|mittel/i],
	['fine', /\bfine\b|fein/i]
];

function variantOf(text: string, family: (typeof soilFamilies)[number]): MaterialKey {
	// German compounds carry the grain size in the word itself: "Mittelsand", "Grobkies".
	const word = text.match(family.noun)?.[0] ?? '';
	const compound = grainWords.filter(([, re]) => new RegExp(`^${re.source}`, 'i').test(word));
	if (compound.length === 1) return family.variants?.[compound[0][0]] ?? family.base;

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

/** "grobsandig" is the coarse sand as minor component, a plain "sandig" the sand. */
function secondaryVariantOf(text: string, family: (typeof soilFamilies)[number]): MaterialKey {
	const word = text.match(family.adjective)?.[0] ?? '';
	const compound = grainWords.filter(([, re]) => new RegExp(`^${re.source}`, 'i').test(word));
	return compound.length === 1 ? (family.variants?.[compound[0][0]] ?? family.base) : family.base;
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
			material: secondaryVariantOf(text, family),
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
