import React from "react";
import { Popconfirm } from "antd";

import { useDeleteFlow, useFlows } from "../api/flows";
import { scopeRange, useFilters } from "../store";

export const FlowsList: React.FC = () => {
  const scope = useFilters((s) => s.scope);
  const openFlowEditor = useFilters((s) => s.openFlowEditor);
  // Narrow the flows list by the active temporal scope's year range
  // (year / range / label all resolve to a [from, to] pair).
  const r = scopeRange(scope);
  const flowsQ = useFlows({ from_year: r?.[0], to_year: r?.[1] });
  const delFlow = useDeleteFlow();

  const muted: React.CSSProperties = { color: "var(--text-muted)" };
  const faint: React.CSSProperties = { color: "var(--text-faint)" };

  if (flowsQ.isLoading) return <div className="text-sm px-4 py-3" style={muted}>завантаження…</div>;
  const items = flowsQ.data ?? [];
  if (!items.length) {
    return (
      <div className="px-4 py-3 text-xs italic" style={faint}>
        Поки немає введених потоків. Натисни «+» на мапі, щоб додати.
      </div>
    );
  }
  return (
    <div style={{ color: "var(--text-base)" }}>
      {items.map((f) => (
        <div
          key={f.id}
          className="px-4 py-2 text-xs"
          style={{ borderBottom: "1px solid var(--border-soft)" }}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="leading-tight">
              <div>{f.origin_name} → {f.destination_name}</div>
              <div className="mt-0.5" style={muted}>
                {f.count != null && <span>{f.count.toLocaleString("uk")} осіб · </span>}
                {f.count_lower != null && (
                  <span>
                    {f.count_lower.toLocaleString("uk")}–{f.count_upper?.toLocaleString("uk")} осіб ·{" "}
                  </span>
                )}
                {f.count_method === "share" && f.share_pct != null && (
                  <span>
                    {f.share_pct}% {f.share_base_kind === "population" ? "населення" : `потоку #${f.share_base_flow_id}`} ·{" "}
                  </span>
                )}
                {f.count == null && f.count_lower == null && f.count_method !== "share" && (
                  <span>кількість невідома · </span>
                )}
                <span>{f.vector}</span>
              </div>
              <div className="text-[10px] mt-0.5" style={faint}>
                {f.temporal_label ?? (f.date_from ? `${f.date_from} → ${f.date_to}` : "час невідомо")}
              </div>
              {f.provisional && (
                <span
                  className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded"
                  style={{ color: "#e07b3a", background: "rgba(224,123,58,0.15)" }}
                >
                  provisional (без джерела)
                </span>
              )}
              {f.sources.length > 0 && (
                <div className="text-[10px] mt-1" style={faint}>
                  {f.sources.length} джерело(а):{" "}
                  {f.sources.map((s) => s.short_title).join(" · ")}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                className="text-xs"
                style={faint}
                title="Редагувати потік"
                onClick={() => openFlowEditor(f.id)}
              >
                ✎
              </button>
              <Popconfirm
                title="Видалити потік?"
                onConfirm={() => delFlow.mutate(f.id)}
                okText="Так"
                cancelText="Ні"
              >
                <button className="text-xs" style={faint}>×</button>
              </Popconfirm>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
