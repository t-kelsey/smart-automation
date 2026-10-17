/** Types of the DIN 4023:2023-02 drawing model (soil/rock symbols, composition, layer properties). */

export type MaterialGroup = 'soil' | 'rock' | 'geology';

/** Table 1: pure soil types (DIN EN ISO 14688-1). */
export type SoilKey =
	| 'largeBoulder'
	| 'boulder'
	| 'cobble'
	| 'gravel'
	| 'coarseGravel'
	| 'mediumGravel'
	| 'fineGravel'
	| 'sand'
	| 'coarseSand'
	| 'mediumSand'
	| 'fineSand'
	| 'silt'
	| 'coarseSilt'
	| 'clay'
	| 'peat'
	| 'volcanicAsh'
	| 'lignite';

/** Table 2: rock types (DIN EN ISO 14689). */
export type RockKey =
	| 'conglomerate'
	| 'breccia'
	| 'sandstone'
	| 'siltstone'
	| 'claystone'
	| 'marlstone'
	| 'limestone'
	| 'dolomite'
	| 'anhydrite'
	| 'gypsum'
	| 'rockSalt'
	| 'tuff'
	| 'hardCoal'
	| 'quartzite'
	| 'volcanic'
	| 'plutonic'
	| 'massiveMetamorphic'
	| 'foliatedMetamorphic';

/** Table 3: common geological terms for soil and rock. */
export type GeologyKey =
	| 'topsoil'
	| 'weatheringLoam'
	| 'slopeDebris'
	| 'tillLoam'
	| 'tillMarl'
	| 'loess'
	| 'loessLoam'
	| 'marshClay'
	| 'lakeMarl'
	| 'bandedClay'
	| 'mud'
	| 'anthropogenic'
	| 'chalk'
	| 'calcTufa';

export type MaterialKey = SoilKey | RockKey | GeologyKey;

/** Annex A, Table A.1: example colour codes. */
export type DinColorKey =
	| 'olive'
	| 'yellow'
	| 'yellowishBrown'
	| 'pink'
	| 'orange'
	| 'darkBrown'
	| 'red'
	| 'lilac'
	| 'violet'
	| 'violetBlue'
	| 'darkBlue'
	| 'lightBlue'
	| 'yellowGreen'
	| 'turquoise'
	| 'green'
	| 'grey'
	| 'black';

/** Share of a secondary component: "schwach" (u'), normal (u) or "stark" (u*). */
export type Proportion = 'weak' | 'normal' | 'strong';

export interface SecondaryComponent {
	material: MaterialKey;
	proportion?: Proportion;
}

export interface BaseComposition {
	main: MaterialKey;
	/** Second grain-size range with about the same mass share: "S/G". */
	coMain?: MaterialKey;
	/** Secondary components in the order of the short form. */
	secondary?: SecondaryComponent[];
}

/**
 * Composition of a layer, e.g. "G/S, u'" or "Pl (S, g)".
 * `breakdown` is the soil a rock decomposed to (4.3.2) or the soil of an anthropogenic layer (4.2.8).
 */
export interface Composition extends BaseComposition {
	breakdown?: BaseComposition;
}

export type Language = 'de' | 'en';

export interface Material {
	key: MaterialKey;
	group: MaterialGroup;
	/** Short form as main component (Hauptanteil), e.g. "G" or "Sst". */
	short: string;
	/** Short form as secondary component (Nebenanteil), e.g. "g". Only soils have one. */
	secondaryShort?: string;
	name: Record<Language, string>;
	/** Adjective used as secondary component, e.g. "kiesig" / "gravelly". */
	secondaryName?: Record<Language, string>;
	/** DIN colour; anthropogenic soil has none. */
	color?: DinColorKey;
}

export type Shape =
	| { type: 'circle'; cx: number; cy: number; r: number; filled?: boolean }
	| { type: 'path'; d: string; filled?: boolean; strokeWidth?: number }
	| { type: 'rect'; x: number; y: number; width: number; height: number; filled?: boolean }
	| { type: 'text'; x: number; y: number; text: string; size: number };

/** A tiling hatch pattern in column units (the column is 60 units wide). */
export interface PatternDef {
	width: number;
	height: number;
	shapes: Shape[];
}
