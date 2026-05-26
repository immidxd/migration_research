import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export interface FlowSourceRef {
  source_id: number;
  short_title: string;
  note: string | null;
}

export interface Flow {
  id: number;
  origin_territory_id: number;
  origin_name: string;
  destination_territory_id: number;
  destination_name: string;
  temporal_label_id: number | null;
  temporal_label: string | null;
  date_from: string | null;
  date_to: string | null;
  date_precision: string;
  count: number | null;
  count_lower: number | null;
  count_upper: number | null;
  count_method: "exact" | "estimate" | "range" | "unknown";
  vector: string;
  transport_mode: string;
  origin_precision: string;
  destination_precision: string;
  provisional: boolean;
  notes: string | null;
  sources: FlowSourceRef[];
  created_at: string;
  updated_at: string;
}

export interface FlowCreatePayload {
  origin_territory_id: number;
  destination_territory_id: number;
  temporal_label_id?: number | null;
  date_from?: string | null;
  date_to?: string | null;
  date_precision?: string;
  count?: number | null;
  count_lower?: number | null;
  count_upper?: number | null;
  count_method?: string;
  vector: string;
  transport_mode?: string;
  origin_precision: string;
  destination_precision?: string;
  notes?: string | null;
  sources?: { source_id: number; note?: string | null }[];
}

export function useFlows(params?: { covering_year?: number; vector?: string[] }) {
  const qs = new URLSearchParams();
  if (params?.covering_year != null) qs.set("covering_year", String(params.covering_year));
  if (params?.vector) for (const v of params.vector) qs.append("vector", v);
  const s = qs.toString();
  return useQuery<Flow[]>({
    queryKey: ["flows", s],
    queryFn: async () => (await api.get(`/migration-flows${s ? `?${s}` : ""}`)).data,
  });
}

export function useCreateFlow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: FlowCreatePayload): Promise<Flow> =>
      (await api.post("/migration-flows", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["flows"] }),
  });
}

export interface FlowFeature
  extends GeoJSON.Feature<GeoJSON.LineString, {
    id: number;
    vector: string;
    transport_mode: string;
    count: number | null;
    count_lower: number | null;
    count_upper: number | null;
    count_method: string;
    origin_name: string;
    destination_name: string;
    temporal_label: string | null;
    date_from: string | null;
    date_to: string | null;
    date_precision: string;
    provisional: boolean;
    source_count: number;
  }> {}

export interface FlowFeatureCollection
  extends GeoJSON.FeatureCollection<GeoJSON.LineString, FlowFeature["properties"]> {}

export function useFlowsGeoJSON(params?: { covering_year?: number; vector?: string[] }) {
  const qs = new URLSearchParams();
  if (params?.covering_year != null) qs.set("covering_year", String(params.covering_year));
  if (params?.vector) for (const v of params.vector) qs.append("vector", v);
  const s = qs.toString();
  return useQuery<FlowFeatureCollection>({
    queryKey: ["flows-geo", s],
    queryFn: async () => (await api.get(`/migration-flows.geojson${s ? `?${s}` : ""}`)).data,
  });
}

export function useDeleteFlow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => api.delete(`/migration-flows/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["flows"] }),
  });
}

// --- Source helpers ---

export interface SourceRow {
  id: number;
  short_title: string;
  citation: string;
  kind: string | null;
  year: number | null;
}

export async function searchSources(q: string): Promise<SourceRow[]> {
  return (await api.get(`/sources/search?q=${encodeURIComponent(q)}`)).data;
}

export interface SourceCreatePayload {
  short_title: string;
  citation: string;
  kind?: string;
  author?: string;
  year?: number;
  url?: string;
  notes?: string;
}

export function useCreateSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SourceCreatePayload): Promise<SourceRow> =>
      (await api.post("/sources", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });
}

// --- Territory typeahead ---

export interface TerritorySearchRow {
  id: number;
  kind: string;
  name: string;
  name_local: string | null;
  code: string | null;
  empire: string | null;
}

export async function searchTerritories(q: string, kinds?: string[]): Promise<TerritorySearchRow[]> {
  const qs = new URLSearchParams();
  if (q) qs.set("q", q);
  if (kinds) for (const k of kinds) qs.append("kind", k);
  return (await api.get(`/territories/search?${qs.toString()}`)).data;
}
