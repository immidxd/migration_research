import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export interface AggregateContributor {
  flow_id: number;
  label: string;
  count: number | null;
  count_method: string;
  magnitude: number | null;
}

export interface AggregateExcluded {
  flow_id: number;
  label: string;
  reason: string;
}

export interface FlowAggregate {
  query: {
    origin_id: number;
    origin_name: string | null;
    from_year: number | null;
    to_year: number | null;
    vector: string[] | null;
  };
  matched: number;
  resolved: {
    point: number;
    low: number;
    high: number;
    has_overlap_uncertainty: boolean;
    some_counts_unknown: boolean;
  } | null;
  naive_sum: number;
  contributors: AggregateContributor[];
  excluded: AggregateExcluded[];
  overlaps_unknown_pairs: [number, number][];
}

export interface AggregateParams {
  origin_id: number | null;
  from_year?: number | null;
  to_year?: number | null;
  vector?: string[];
}

export function useFlowAggregate(params: AggregateParams) {
  const qs = new URLSearchParams();
  if (params.origin_id != null) qs.set("origin_id", String(params.origin_id));
  if (params.from_year != null) qs.set("from_year", String(params.from_year));
  if (params.to_year != null) qs.set("to_year", String(params.to_year));
  if (params.vector) for (const v of params.vector) qs.append("vector", v);
  return useQuery<FlowAggregate>({
    queryKey: ["flow-aggregate", qs.toString()],
    enabled: params.origin_id != null,
    queryFn: async () => (await api.get(`/analytics/flow-aggregate?${qs.toString()}`)).data,
  });
}
