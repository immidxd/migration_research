import { create } from "zustand";

export type TerritoryKind =
  | "settlement" | "volost" | "uezd" | "gubernia" | "region"
  | "country" | "subdivision" | "port" | "station" | "border_crossing";

export type Empire = "russian_empire" | "austro_hungarian" | "other";

export type MigrationVector =
  | "transatlantic" | "european" | "intra_imperial_east"
  | "intra_imperial_other" | "internal";

interface FilterState {
  // Which layers are visible on the map.
  kinds: Set<TerritoryKind>;
  empires: Set<Empire>;
  vectors: Set<MigrationVector>;  // for future flow layers
  selectedTerritoryId: number | null;
  selectedPeriodId: number | null;

  toggleKind: (k: TerritoryKind) => void;
  toggleEmpire: (e: Empire) => void;
  toggleVector: (v: MigrationVector) => void;
  selectTerritory: (id: number | null) => void;
  selectPeriod: (id: number | null) => void;
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
  selectedPeriodId: null,

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
  selectPeriod: (id) => set({ selectedPeriodId: id }),
}));
