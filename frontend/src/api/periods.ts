import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export interface Period {
  id: number;
  slug: string;
  name: string;
  date_from: string;
  date_to: string;
  description: string | null;
}

export function usePeriods() {
  return useQuery<Period[]>({
    queryKey: ["periods"],
    queryFn: async () => (await api.get("/periods")).data,
  });
}
