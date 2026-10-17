import { standard } from './standard.ts';
import type { DinColorKey, Language } from './types.ts';

/** Web key and English name for each colour of the standard file (`farben`, matched by German name). */
const colorNames: Record<DinColorKey, { de: string; en: string }> = {
	olive: { de: 'oliv', en: 'olive' },
	yellow: { de: 'gelb', en: 'yellow' },
	yellowishBrown: { de: 'gelblichbraun', en: 'yellowish brown' },
	pink: { de: 'rosa', en: 'pink' },
	orange: { de: 'orange', en: 'orange' },
	darkBrown: { de: 'dunkelbraun', en: 'dark brown' },
	red: { de: 'rot', en: 'red' },
	lilac: { de: 'lila', en: 'lilac' },
	violet: { de: 'violett', en: 'violet' },
	violetBlue: { de: 'violettblau', en: 'violet-blue' },
	darkBlue: { de: 'dunkelblau', en: 'dark blue' },
	lightBlue: { de: 'hellblau', en: 'light blue' },
	yellowGreen: { de: 'gelbgrün', en: 'yellow-green' },
	turquoise: { de: 'türkis', en: 'turquoise' },
	green: { de: 'grün', en: 'green' },
	grey: { de: 'grau', en: 'grey' },
	black: { de: 'schwarz', en: 'black' }
};

/** Colour key for a German colour name of the standard file. */
export const colorKeyByName = Object.fromEntries(
	Object.entries(colorNames).map(([key, name]) => [name.de, key])
) as Record<string, DinColorKey>;

/** DIN 4023:2023-02 Annex A colours, values from the standard file (hex is used for türkis, see ADR-0011). */
export const dinColors = Object.fromEntries(
	(Object.keys(colorNames) as DinColorKey[]).map((key) => {
		const entry = standard.farben.find((f) => f.name === colorNames[key].de);
		if (!entry) throw new Error(`Colour "${colorNames[key].de}" missing in din-4023.json`);
		return [key, { hex: entry.hex, ral: entry.ral, name: colorNames[key] }];
	})
) as Record<DinColorKey, { hex: string; ral: number; name: Record<Language, string> }>;
