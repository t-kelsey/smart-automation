import raw from '../../../../standards/din-4023/din-4023.json';

/** Typed view of `standards/din-4023/din-4023.json` (ADR-0011), the shared source of truth. */
export interface StandardFile {
	norm: { ausgabe_schraffuren: string; ausgabe_tabelle_1: string };
	farben: { name: string; rgb: number[]; hex: string; ral: number }[];
	schraffuren: {
		id: string;
		bezeichnung: string;
		kategorie: 'boden' | 'fels' | 'geologisch';
		kurzform: string;
		tabelle_din_4023_2023: number;
	}[];
	tabelle_1: {
		bodenarten: {
			id: string;
			benennung: { hauptanteil: string; nebenanteil: string | null };
			kurzform: { hauptanteil: string; nebenanteil: string | null };
			schraffur: string | null;
			farbe: string;
		}[];
	};
}

export const standard = raw as StandardFile;
