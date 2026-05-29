import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export type StatKind = "diaspora_stock" | "total_population" | "immigrant_arrivals" | "other";

export interface Stat {
  id: number;
  territory_id: number;
  territory_name: string | null;
  stat_kind: StatKind;
  group_label: string | null;
  as_of_year: number | null;
  temporal_label_id: number | null;
  temporal_label: string | null;
  count: number | null;
  count_lower: number | null;
  count_upper: number | null;
  count_method: "exact" | "estimate" | "range" | "unknown";
  provisional: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface StatCreatePayload {
  territory_id: number;
  stat_kind: StatKind;
  group_label?: string | null;
  as_of_year?: number | null;
  temporal_label_id?: number | null;
  count?: number | null;
  count_lower?: number | null;
  count_upper?: number | null;
  count_method?: string;
  notes?: string | null;
  sources?: { source_id: number; note?: string | null }[];
}

export function useTerritoryStats(territoryId: number | null) {
  return useQuery<Stat[]>({
    queryKey: ["territory-stats", territoryId],
    enabled: territoryId != null,
    queryFn: async () =>
      (await api.get(`/territory-stats?territory_id=${territoryId}`)).data,
  });
}

export function useCreateStat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: StatCreatePayload): Promise<Stat> =>
      (await api.post("/territory-stats", payload)).data,
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: ["territory-stats"] });
      qc.invalidateQueries({ queryKey: ["territories", s.territory_id] });
    },
  });
}

export function useDeleteStat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => api.delete(`/territory-stats/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["territory-stats"] }),
  });
}
