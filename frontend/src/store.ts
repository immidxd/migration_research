import { create } from "zustand";

export type TerritoryKind =
  | "settlement" | "volost" | "uezd" | "gubernia" | "region"
  | "country" | "subdivision" | "port" | "station" | "border_crossing";

export type Empire = "russian_empire" | "austro_hungarian" | "other";

export type MigrationVector =
  | "transatlantic" | "european" | "intra_imperial_east"
  | "intra_imperial_other" | "internal";

export type TemporalLabelKind =
  | "year" | "decade" | "quarter_century" | "half_century"
  | "century" | "era_label" | "named_period";

export interface TemporalLabel {
  id: number;
  slug: string;
  label: string;
  kind: TemporalLabelKind;
  year_from: number;
  year_to: number;
  description: string | null;
}

/**
 * Temporal scope: how the user is currently narrowing in on time.
 * - none:  no temporal filter active
 * - year:  one specific year (always implies range [y, y])
 * - range: arbitrary year range chosen with the slider
 * - label: a named temporal label (decade / era / century / period)
 *          — yearFrom/yearTo are denormalised from the label for filtering
 *
 * All three active modes resolve to a canonical [yearFrom, yearTo] pair,
 * which is what map and (future) flow filters consume.
 */
export type TemporalScope =
  | { mode: "none" }
  | { mode: "year"; year: number }
  | { mode: "range"; yearFrom: number; yearTo: number }
  | { mode: "label"; labelId: number; label: TemporalLabel };

export function scopeRange(s: TemporalScope): [number, number] | null {
  if (s.mode === "none") return null;
  if (s.mode === "year") return [s.year, s.year];
  if (s.mode === "range") return [s.yearFrom, s.yearTo];
  return [s.label.year_from, s.label.year_to];
}

export function scopeDescribe(s: TemporalScope): string {
  if (s.mode === "none") return "усі періоди";
  if (s.mode === "year") return String(s.year);
  if (s.mode === "range") return `${s.yearFrom}–${s.yearTo}`;
  return s.label.label;
}

interface FilterState {
  kinds: Set<TerritoryKind>;
  empires: Set<Empire>;
  vectors: Set<MigrationVector>;
  selectedTerritoryId: number | null;
  scope: TemporalScope;

  toggleKind: (k: TerritoryKind) => void;
  toggleEmpire: (e: Empire) => void;
  toggleVector: (v: MigrationVector) => void;
  selectTerritory: (id: number | null) => void;
  setScope: (s: TemporalScope) => void;
}

const ALL_VECTORS: MigrationVector[] = [
  "transatlantic", "european", "intra_imperial_east",
  "intra_imperial_other", "internal",
];

export const useFilters = create<FilterState>((set) => ({
  kinds: new Set<TerritoryKind>(["country", "region", "port", "border_crossing"]),
  empires: new Set<Empire>(["russian_empire", "austro_hungarian", "other"]),
  vectors: new Set<MigrationVector>(ALL_VECTORS),
  selectedTerritoryId: null,
  scope: { mode: "none" },

  toggleKind: (k) => set((s) => {
    const next = new Set(s.kinds);
    next.has(k) ? next.delete(k) : next.add(k);
    return { kinds: next };
  }),
  toggleEmpire: (e) => set((s) => {
    const next = new Set(s.empires);
    next.has(e) ? next.delete(e) : next.add(e);
    return { empires: next };
  }),
  toggleVector: (v) => set((s) => {
    const next = new Set(s.vectors);
    next.has(v) ? next.delete(v) : next.add(v);
    return { vectors: next };
  }),
  selectTerritory: (id) => set({ selectedTerritoryId: id }),
  setScope: (s) => set({ scope: s }),
}));
