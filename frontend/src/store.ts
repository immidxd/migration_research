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

export type ThemeMode = "dark" | "light";

interface FilterState {
  kinds: Set<TerritoryKind>;
  empires: Set<Empire>;
  vectors: Set<MigrationVector>;
  selectedTerritoryId: number | null;
  scope: TemporalScope;
  theme: ThemeMode;

  // Flow editor: open + which flow is being edited (null = creating a new one).
  flowEditorOpen: boolean;
  editingFlowId: number | null;

  // Statistics report drawer.
  statsReportOpen: boolean;
  // Flows management drawer.
  flowsDrawerOpen: boolean;
  // Cross-pane flow highlight: any UI can set this and the map will light up
  // the matching flow (+ its sub-flows) without that UI knowing about layers.
  hoveredFlowId: number | null;

  toggleKind: (k: TerritoryKind) => void;
  toggleEmpire: (e: Empire) => void;
  toggleVector: (v: MigrationVector) => void;
  selectTerritory: (id: number | null) => void;
  setScope: (s: TemporalScope) => void;
  setTheme: (t: ThemeMode) => void;
  openFlowEditor: (flowId?: number | null) => void;
  closeFlowEditor: () => void;
  setStatsReportOpen: (open: boolean) => void;
  setFlowsDrawerOpen: (open: boolean) => void;
  setHoveredFlowId: (id: number | null) => void;
}

const initialTheme: ThemeMode = (() => {
  try {
    const saved = localStorage.getItem("migrations.theme");
    if (saved === "dark" || saved === "light") return saved;
  } catch {}
  return "dark";
})();

const ALL_VECTORS: MigrationVector[] = [
  "transatlantic", "european", "intra_imperial_east",
  "intra_imperial_other", "internal",
];

export const useFilters = create<FilterState>((set) => ({
  kinds: new Set<TerritoryKind>(["country", "region", "gubernia", "port", "border_crossing"]),
  empires: new Set<Empire>(["russian_empire", "austro_hungarian", "other"]),
  vectors: new Set<MigrationVector>(ALL_VECTORS),
  selectedTerritoryId: null,
  scope: { mode: "none" },
  theme: initialTheme,
  flowEditorOpen: false,
  editingFlowId: null,
  statsReportOpen: false,
  flowsDrawerOpen: false,
  hoveredFlowId: null,

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
  setTheme: (t) => {
    try { localStorage.setItem("migrations.theme", t); } catch {}
    document.documentElement.setAttribute("data-theme", t);
    set({ theme: t });
  },
  openFlowEditor: (flowId = null) => set({ flowEditorOpen: true, editingFlowId: flowId }),
  closeFlowEditor: () => set({ flowEditorOpen: false, editingFlowId: null }),
  setStatsReportOpen: (open) => set({ statsReportOpen: open }),
  setFlowsDrawerOpen: (open) => set({ flowsDrawerOpen: open }),
  setHoveredFlowId: (id) => set({ hoveredFlowId: id }),
}));

// Apply initial theme attribute synchronously so first paint matches.
if (typeof document !== "undefined") {
  document.documentElement.setAttribute("data-theme", initialTheme);
}
