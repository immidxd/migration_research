import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export type RelationKind = "contains" | "equals" | "disjoint" | "overlaps_unknown";

export interface Relation {
  id: number;
  from_flow_id: number;
  from_label: string | null;
  to_flow_id: number;
  to_label: string | null;
  kind: RelationKind;
  note: string | null;
  created_at: string;
}

export interface RelationCandidate {
  other_flow_id: number;
  other_label: string;
  other_count: number | null;
  other_period: string | null;
  from_flow_id: number;
  to_flow_id: number;
  kind: RelationKind;
  reason: string;
}

export interface RelationCreatePayload {
  from_flow_id: number;
  to_flow_id: number;
  kind: RelationKind;
  note?: string | null;
}

export function useFlowRelations(flowId: number | null) {
  return useQuery<Relation[]>({
    queryKey: ["flow-relations", flowId],
    enabled: flowId != null,
    queryFn: async () => (await api.get(`/flow-relations?flow_id=${flowId}`)).data,
  });
}

export function useRelationCandidates(flowId: number | null) {
  return useQuery<RelationCandidate[]>({
    queryKey: ["flow-relation-candidates", flowId],
    enabled: flowId != null,
    queryFn: async () => (await api.get(`/flow-relations/candidates?flow_id=${flowId}`)).data,
  });
}

export function useCreateRelation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RelationCreatePayload): Promise<Relation> =>
      (await api.post("/flow-relations", payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["flow-relations"] });
      qc.invalidateQueries({ queryKey: ["flow-relation-candidates"] });
    },
  });
}

export function useDeleteRelation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => api.delete(`/flow-relations/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["flow-relations"] });
      qc.invalidateQueries({ queryKey: ["flow-relation-candidates"] });
    },
  });
}
