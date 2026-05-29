import React, { useMemo, useState } from "react";
import { Drawer, InputNumber, Input, Select, Collapse, Popconfirm } from "antd";

import { Flow, useDeleteFlow, useFlows } from "../api/flows";
import { useFilters } from "../store";
import { FlowsList } from "./FlowsList";


const VECTOR_OPTS = [
  { value: "transatlantic", label: "Трансатлантичний" },
  { value: "european", label: "Європейський" },
  { value: "intra_imperial_east", label: "Сх. внутрішньоімперський" },
  { value: "intra_imperial_other", label: "Інший внутрішньоімперський" },
  { value: "internal", label: "Внутрішній" },
];
const VECTOR_LABEL: Record<string, string> = Object.fromEntries(
  VECTOR_OPTS.map((v) => [v.value, v.label])
);


/** Flows management drawer with two view modes:
 *  - "Список" — the existing scope-filtered flat list (FlowsList);
 *  - "Класифіковано" — independent filter bar (year range / vector / search)
 *    with results grouped by vector for easy browsing & editing. */
export const FlowsDrawer: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const [view, setView] = useState<"list" | "classified">("list");
  return (
    <Drawer
      title="Введені потоки"
      placement="left"
      open={open}
      onClose={onClose}
      width={440}
      styles={{ body: { padding: 0 } }}
      extra={
        <div className="flex gap-1">
          {(["list", "classified"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className="px-2 py-1 text-xs rounded"
              style={{
                background: view === v ? "var(--accent-soft)" : "transparent",
                color: view === v ? "var(--text-strong)" : "var(--text-muted)",
                border: "1px solid var(--border-soft)",
              }}
            >
              {v === "list" ? "Список" : "Класифіковано"}
            </button>
          ))}
        </div>
      }
    >
      {view === "list" ? <FlowsList /> : <ClassifiedView />}
    </Drawer>
  );
};


const ClassifiedView: React.FC = () => {
  const [yearFrom, setYearFrom] = useState<number | null>(null);
  const [yearTo, setYearTo] = useState<number | null>(null);
  const [vectors, setVectors] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const openFlowEditor = useFilters((s) => s.openFlowEditor);
  const del = useDeleteFlow();

  // Server-side narrow by year/vector; client-side refine by free-text search.
  const q = useFlows({
    from_year: yearFrom ?? undefined,
    to_year: yearTo ?? undefined,
    vector: vectors.length ? vectors : undefined,
  });
  const filtered = useMemo(() => {
    const all = q.data ?? [];
    if (!search.trim()) return all;
    const s = search.trim().toLowerCase();
    return all.filter(
      (f) =>
        f.origin_name.toLowerCase().includes(s) ||
        f.destination_name.toLowerCase().includes(s)
    );
  }, [q.data, search]);

  const groups = useMemo(() => {
    const m = new Map<string, Flow[]>();
    for (const f of filtered) {
      if (!m.has(f.vector)) m.set(f.vector, []);
      m.get(f.vector)!.push(f);
    }
    return Array.from(m.entries()).sort(
      (a, b) => b[1].length - a[1].length
    );
  }, [filtered]);

  const muted: React.CSSProperties = { color: "var(--text-muted)" };
  const faint: React.CSSProperties = { color: "var(--text-faint)" };

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="px-3 py-3 flex flex-col gap-2" style={{ borderBottom: "1px solid var(--border-soft)" }}>
        <div className="flex gap-2">
          <InputNumber
            placeholder="з (рік)"
            min={1500} max={2100} style={{ flex: 1 }}
            value={yearFrom ?? undefined}
            onChange={(v) => setYearFrom(v != null ? Number(v) : null)}
          />
          <InputNumber
            placeholder="по (рік)"
            min={1500} max={2100} style={{ flex: 1 }}
            value={yearTo ?? undefined}
            onChange={(v) => setYearTo(v != null ? Number(v) : null)}
          />
        </div>
        <Select
          mode="multiple" allowClear placeholder="вектори (усі)"
          value={vectors} onChange={setVectors}
          options={VECTOR_OPTS}
          style={{ width: "100%" }}
        />
        <Input
          allowClear placeholder="пошук за походженням / прибуттям…"
          value={search} onChange={(e) => setSearch(e.target.value)}
        />
        <div className="text-[10px]" style={faint}>
          знайдено: {filtered.length}{q.data ? ` / ${q.data.length}` : ""}
        </div>
      </div>

      {/* Grouped list */}
      <div className="flex-1 overflow-auto">
        {q.isLoading && <div className="text-xs px-4 py-3" style={muted}>завантаження…</div>}
        {!q.isLoading && filtered.length === 0 && (
          <div className="text-xs italic px-4 py-3" style={faint}>
            нічого не знайдено за поточними фільтрами
          </div>
        )}
        <Collapse
          ghost
          bordered={false}
          defaultActiveKey={groups.map(([k]) => k)}
          items={groups.map(([vec, list]) => ({
            key: vec,
            label: (
              <span style={{ color: "var(--text-base)" }}>
                {VECTOR_LABEL[vec] ?? vec}{" "}
                <span style={faint}>· {list.length}</span>
              </span>
            ),
            children: (
              <div className="flex flex-col">
                {list.map((f) => (
                  <div
                    key={f.id}
                    className="px-3 py-2 text-xs flex items-start justify-between gap-2"
                    style={{ borderTop: "1px solid var(--border-soft)" }}
                  >
                    <div className="leading-tight">
                      <div style={{ color: "var(--text-base)" }}>
                        {f.origin_name} → {f.destination_name}
                      </div>
                      <div className="mt-0.5" style={muted}>
                        {f.count != null && <span>{f.count.toLocaleString("uk")} осіб · </span>}
                        {f.count_lower != null && (
                          <span>
                            {f.count_lower.toLocaleString("uk")}–{f.count_upper?.toLocaleString("uk")} осіб ·{" "}
                          </span>
                        )}
                        {f.count_method === "share" && f.share_pct != null && (
                          <span>{f.share_pct}% {f.share_base_kind === "population" ? "населення" : `потоку #${f.share_base_flow_id}`} · </span>
                        )}
                        <span>{f.temporal_label ?? (f.date_from ? `${f.date_from?.slice(0,4)}–${f.date_to?.slice(0,4)}` : "час невідомо")}</span>
                      </div>
                      {f.provisional && (
                        <span
                          className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded"
                          style={{ color: "#e07b3a", background: "rgba(224,123,58,0.15)" }}
                        >
                          provisional
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        className="text-xs"
                        style={faint}
                        title="Редагувати"
                        onClick={() => openFlowEditor(f.id)}
                      >
                        ✎
                      </button>
                      <Popconfirm
                        title="Видалити потік?"
                        onConfirm={() => del.mutate(f.id)}
                        okText="Так" cancelText="Ні"
                      >
                        <button className="text-xs" style={faint}>×</button>
                      </Popconfirm>
                    </div>
                  </div>
                ))}
              </div>
            ),
          }))}
        />
      </div>
    </div>
  );
};
