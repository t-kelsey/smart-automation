import { colorKeyByName } from './colors.ts';
import { standard } from './standard.ts';
import type { DinColorKey, Language, Material, MaterialGroup, MaterialKey } from './types.ts';

const n = (de: string, en: string): Record<Language, string> => ({ de, en });

/**
 * Web material key → id in the standard file and English names (the file is German only, ADR-0011).
 * Soils use the ids of `tabelle_1.bodenarten`, rocks and geological terms those of `schraffuren`.
 * Colours of rocks and geological terms (Tables 2 and 3) are not in the file and are kept here.
 */
const english: Record<
	MaterialKey,
	{ id: string; en: string; enSecondary?: string; color?: DinColorKey }
> = {
	largeBoulder: { id: 'grosser_block', en: 'Large boulder', enSecondary: 'with large boulders' },
	boulder: { id: 'block', en: 'Boulder', enSecondary: 'with boulders' },
	cobble: { id: 'stein', en: 'Cobble', enSecondary: 'cobbly' },
	gravel: { id: 'kies', en: 'Gravel', enSecondary: 'gravelly' },
	coarseGravel: { id: 'grobkies', en: 'Coarse gravel', enSecondary: 'coarse gravelly' },
	mediumGravel: { id: 'mittelkies', en: 'Medium gravel', enSecondary: 'medium gravelly' },
	fineGravel: { id: 'feinkies', en: 'Fine gravel', enSecondary: 'fine gravelly' },
	sand: { id: 'sand', en: 'Sand', enSecondary: 'sandy' },
	coarseSand: { id: 'grobsand', en: 'Coarse sand', enSecondary: 'coarse sandy' },
	mediumSand: { id: 'mittelsand', en: 'Medium sand', enSecondary: 'medium sandy' },
	fineSand: { id: 'feinsand', en: 'Fine sand', enSecondary: 'fine sandy' },
	silt: { id: 'schluff', en: 'Silt', enSecondary: 'silty' },
	coarseSilt: { id: 'grobschluff', en: 'Coarse silt', enSecondary: 'coarse silty' },
	clay: { id: 'ton', en: 'Clay', enSecondary: 'clayey' },
	peat: { id: 'torf_humus', en: 'Peat, humus', enSecondary: 'peaty, humous' },
	volcanicAsh: { id: 'vulkanische_aschen', en: 'Volcanic ash' },
	lignite: { id: 'braunkohle', en: 'Lignite' },
	conglomerate: { id: 'konglomerat', en: 'Conglomerate', color: 'yellow' },
	breccia: { id: 'brekzie', en: 'Breccia', color: 'yellow' },
	sandstone: { id: 'sandstein', en: 'Sandstone', color: 'orange' },
	siltstone: { id: 'schluffstein', en: 'Siltstone', color: 'olive' },
	claystone: { id: 'tonstein', en: 'Claystone', color: 'violet' },
	marlstone: { id: 'mergelstein', en: 'Marlstone', color: 'violetBlue' },
	limestone: { id: 'kalkstein', en: 'Limestone', color: 'darkBlue' },
	dolomite: { id: 'dolomitstein', en: 'Dolomite', color: 'darkBlue' },
	anhydrite: { id: 'anhydrit', en: 'Anhydrite', color: 'yellowGreen' },
	gypsum: { id: 'gips', en: 'Gypsum', color: 'yellowGreen' },
	rockSalt: { id: 'salzgestein', en: 'Rock salt', color: 'yellowGreen' },
	tuff: { id: 'tuffstein', en: 'Tuff (consolidated volcanic ash)', color: 'grey' },
	hardCoal: { id: 'steinkohle', en: 'Hard coal', color: 'black' },
	quartzite: { id: 'quarzit', en: 'Quartzite', color: 'pink' },
	volcanic: { id: 'vulkanite', en: 'Volcanic rock', color: 'red' },
	plutonic: { id: 'plutonite', en: 'Plutonic rock', color: 'red' },
	massiveMetamorphic: { id: 'massige_metamorphite', en: 'Massive metamorphic rock', color: 'red' },
	foliatedMetamorphic: {
		id: 'blaettrige_metamorphite',
		en: 'Foliated metamorphic rock',
		color: 'violet'
	},
	topsoil: { id: 'mutterboden', en: 'Topsoil', color: 'yellowishBrown' },
	weatheringLoam: { id: 'hanglehm', en: 'Slope loam', color: 'grey' },
	slopeDebris: { id: 'hangschutt', en: 'Slope debris', color: 'grey' },
	tillLoam: { id: 'geschiebelehm', en: 'Glacial till (loam)', color: 'grey' },
	tillMarl: { id: 'geschiebemergel', en: 'Glacial till (marl)', color: 'violetBlue' },
	loess: { id: 'loess', en: 'Loess', color: 'olive' },
	loessLoam: { id: 'loesslehm', en: 'Loess loam', color: 'olive' },
	marshClay: { id: 'klei_schlick', en: 'Marsh clay, tidal mud', color: 'lilac' },
	lakeMarl: { id: 'wiesenkalk', en: 'Meadow lime, lake marl', color: 'lightBlue' },
	bandedClay: { id: 'baenderton', en: 'Varved clay', color: 'violet' },
	mud: { id: 'mudde', en: 'Mud (sapropel)', color: 'lilac' },
	anthropogenic: { id: 'auffuellung', en: 'Anthropogenic soil (made ground)' },
	chalk: { id: 'kreidestein', en: 'Chalk', color: 'lightBlue' },
	calcTufa: { id: 'kalktuff', en: 'Calcareous tufa', color: 'lightBlue' }
};

const categoryGroup = { boden: 'soil', fels: 'rock', geologisch: 'geology' } as const;

function build(key: MaterialKey): Material {
	const e = english[key];
	const soilRow = standard.tabelle_1.bodenarten.find((s) => s.id === e.id);
	if (soilRow) {
		const hasSecondary = soilRow.kurzform.nebenanteil !== null;
		return {
			key,
			group: 'soil',
			short: soilRow.kurzform.hauptanteil,
			secondaryShort: soilRow.kurzform.nebenanteil ?? undefined,
			name: { de: soilRow.benennung.hauptanteil, en: e.en },
			secondaryName: hasSecondary
				? { de: soilRow.benennung.nebenanteil ?? '', en: e.enSecondary ?? '' }
				: undefined,
			color: colorKeyByName[soilRow.farbe]
		};
	}
	const hatch = standard.schraffuren.find((s) => s.id === e.id);
	if (!hatch) throw new Error(`"${e.id}" (${key}) missing in din-4023.json`);
	return {
		key,
		group: categoryGroup[hatch.kategorie],
		short: hatch.kurzform,
		name: { de: hatch.bezeichnung, en: e.en },
		color: e.color
	};
}

/** All materials of DIN 4023, in the order of the table: soils (Table 1), rocks (2), geological terms (3). */
export const materialList: Material[] = (Object.keys(english) as MaterialKey[]).map(build);

export const materials = Object.fromEntries(materialList.map((m) => [m.key, m])) as Record<
	MaterialKey,
	Material
>;

export const materialGroups: {
	group: MaterialGroup;
	title: Record<Language, string>;
	table: number;
}[] = [
	{ group: 'soil', title: n('Bodenarten', 'Soils'), table: 1 },
	{ group: 'rock', title: n('Felsarten', 'Rocks'), table: 2 },
	{ group: 'geology', title: n('Geologische Benennungen', 'Geological terms'), table: 3 }
];

export const materialsByGroup = (group: MaterialGroup): Material[] =>
	materialList.filter((m) => m.group === group);

/** Materials that can be named as minor component. */
export const canBeSecondary = (key: MaterialKey): boolean => !!materials[key].secondaryShort;
