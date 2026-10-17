import { materials } from './materials.ts';
import type { BaseComposition, Composition, Language, MaterialKey, Proportion } from './types.ts';

const marker: Record<Proportion, string> = { weak: "'", normal: '', strong: '*' };

function baseShortForm(c: BaseComposition): string {
	let result = materials[c.main].short;
	if (c.coMain) result += `/${materials[c.coMain].short}`;
	for (const s of c.secondary ?? []) {
		const m = materials[s.material];
		result += `, ${m.secondaryShort ?? m.short}${marker[s.proportion ?? 'normal']}`;
	}
	return result;
}

/**
 * Short form after DIN 4023 4.2: "G/S, u'", "mS, u, h", "Pl (S, g)".
 * A strong minor component is marked with `*` (the standard allows it instead of an overbar),
 * a weak one with an apostrophe.
 */
export function shortForm(c: Composition): string {
	return c.breakdown ? `${baseShortForm(c)} (${baseShortForm(c.breakdown)})` : baseShortForm(c);
}

const proportionWord: Record<Language, Record<Proportion, string>> = {
	de: { weak: 'schwach ', normal: '', strong: 'stark ' },
	en: { weak: 'slightly ', normal: '', strong: 'strongly ' }
};

function baseName(c: BaseComposition, lang: Language): string {
	let result = materials[c.main].name[lang];
	if (c.coMain) result += `/${materials[c.coMain].name[lang]}`;
	for (const s of c.secondary ?? []) {
		const m = materials[s.material];
		result += `, ${proportionWord[lang][s.proportion ?? 'normal']}${m.secondaryName?.[lang] ?? m.name[lang]}`;
	}
	return result;
}

/** Full name, e.g. "Gravel/Sand, slightly silty" or "Plutonic rock (e.g. granite) (Sand, gravelly)". */
export function describe(c: Composition, lang: Language = 'en'): string {
	return c.breakdown ? `${baseName(c, lang)} (${baseName(c.breakdown, lang)})` : baseName(c, lang);
}

/** What is drawn where in the column (DIN 4023 4.2.5 to 4.2.10, 4.3.2). */
export interface ColumnFill {
	/** `split`: main component over the full width, second one in the right half only.
	 * `both`: two equal components, both patterns over the full width, one colour per half. */
	mode: 'split' | 'both';
	main: MaterialKey;
	/** Component of the right half: first minor component, breakdown or second main component. */
	second?: MaterialKey;
}

export function columnFill(c: Composition): ColumnFill {
	if (c.coMain) return { mode: 'both', main: c.main, second: c.coMain };
	return { mode: 'split', main: c.main, second: c.breakdown?.main ?? c.secondary?.[0]?.material };
}

/** All materials used by a composition, e.g. for a legend. */
export function usedMaterials(c: Composition): MaterialKey[] {
	return [
		c.main,
		c.coMain,
		...(c.secondary ?? []).map((s) => s.material),
		c.breakdown?.main,
		c.breakdown?.coMain,
		...(c.breakdown?.secondary ?? []).map((s) => s.material)
	].filter((key): key is MaterialKey => key !== undefined);
}
