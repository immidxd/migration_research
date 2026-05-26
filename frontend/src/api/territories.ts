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
