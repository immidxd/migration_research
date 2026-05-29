import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export interface TerritoryRow {
  id: number;
  kind: string;
  name: string;
  name_local: string | null;
  code: string | null;
  empire: string | null;
  is_umbrella_region: boolean;
  is_container?: boolean;
}

export interface TerritoryDetail extends TerritoryRow {
  notes: string | null;
  valid_from: string | null;
  valid_to: string | null;
  geometry: GeoJSON.Geometry | null;
  sources: Array<{
    id: number;
    short_title: string;
    citation: string;
    kind: string | null;
    year: number | null;
    url: string | null;
    note: string | null;
  }> | null;
  transit_profile: {
    active_from: string | null;
    active_to: string | null;
    operator: string | null;
    notes: string | null;
  } | null;
  periods: Array<{
    id: number;
    year_from: number;
    year_to: number;
    status: string | null;
    name: string | null;
    name_local: string | null;
    sovereign_id: number | null;
    notes: string | null;
  }> | null;
  stats: Array<{
    id: number;
    stat_kind: string;
    group_label: string | null;
    as_of_year: number | null;
    temporal_label_id: number | null;
    count: number | null;
    count_lower: number | null;
    count_upper: number | null;
    count_method: string;
    provisional: boolean;
    notes: string | null;
  }> | null;
}

export type FeatureCollection = GeoJSON.FeatureCollection<
  GeoJSON.Geometry,
  TerritoryRow
>;

function kindsToParams(kinds: string[]): string {
  return kinds.map((k) => `kind=${encodeURIComponent(k)}`).join("&");
}

export function useTerritoryLayer(kinds: string[]) {
  return useQuery<FeatureCollection>({
    queryKey: ["territories", "geojson", kinds.sort().join(",")],
    queryFn: async () => {
      if (kinds.length === 0) return { type: "FeatureCollection", features: [] };
      const { data } = await api.get(`/territories?${kindsToParams(kinds)}`);
      return data;
    },
  });
}

// One-point-per-feature label source. Used by the map's symbol layer so
// large multipart polygons (Сибір, Європейська Росія, …) get ONE label
// instead of one per island.
export function useTerritoryLabels(kinds: string[], year?: number) {
  return useQuery<GeoJSON.FeatureCollection<GeoJSON.Point, TerritoryRow & { period_status: string | null }>>({
    queryKey: ["territory-labels", kinds.sort().join(","), year ?? null],
    queryFn: async () => {
      if (kinds.length === 0) return { type: "FeatureCollection", features: [] };
      const yq = year != null ? `&year=${year}` : "";
      const { data } = await api.get(
        `/territories.labels?${kindsToParams(kinds)}${yq}`
      );
      return data;
    },
  });
}

export function useTerritoryList(kinds: string[]) {
  return useQuery<{ items: TerritoryRow[]; count: number }>({
    queryKey: ["territories", "table", kinds.sort().join(",")],
    queryFn: async () => {
      const { data } = await api.get(
        `/territories?format=table&${kindsToParams(kinds)}`
      );
      return data;
    },
  });
}

export function useTerritory(id: number | null) {
  return useQuery<TerritoryDetail>({
    queryKey: ["territories", id],
    queryFn: async () => {
      const { data } = await api.get(`/territories/${id}`);
      return data;
    },
    enabled: id != null,
  });
}
