import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import { TemporalLabel } from "../store";

export function useTemporalLabels(kinds?: string[]) {
  const key = kinds?.sort().join(",") ?? "all";
  return useQuery<TemporalLabel[]>({
    queryKey: ["temporal-labels", key],
    queryFn: async () => {
      const qs = kinds && kinds.length
        ? kinds.map((k) => `kind=${encodeURIComponent(k)}`).join("&")
        : "";
      const { data } = await api.get(`/temporal-labels${qs ? `?${qs}` : ""}`);
      return data;
    },
    staleTime: 5 * 60_000,
  });
}

export function useLabelsCoveringYear(year: number | null) {
  return useQuery<TemporalLabel[]>({
    queryKey: ["temporal-labels", "covering", year],
    queryFn: async () => {
      const { data } = await api.get(`/temporal-labels?covering_year=${year}`);
      return data;
    },
    enabled: year != null,
  });
}
