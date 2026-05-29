import React, { useState } from "react";
import { InputNumber, Input, Select, Popconfirm, message } from "antd";

import { useTerritory } from "../api/territories";
import { StatKind, useCreateStat, useDeleteStat } from "../api/stats";
import { SourcePicker } from "./pickers";
import { useFilters } from "../store";

const STAT_KIND_LABEL: Record<string, string> = {
  diaspora_stock: "діаспора (сток)",
  total_population: "усе населення",
  immigrant_arrivals: "прибуття за рік",
  other: "інше",
};

const InspectorPanel: React.FC = () => {
  const selectedId = useFilters((s) => s.selectedTerritoryId);
  const selectTerritory = useFilters((s) => s.selectTerritory);
  const { data, isLoading } = useTerritory(selectedId);
  const delStat = useDeleteStat();

  if (selectedId == null) return null;

  const cardStyle: React.CSSProperties = {
    background: "var(--bg-panel-soft)",
    color: "var(--text-base)",
    border: "1px solid var(--border)",
    boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
  };
  const divider = { borderBottom: "1px solid var(--border-soft)" } as React.CSSProperties;
  const muted = { color: "var(--text-muted)" } as React.CSSProperties;
  const faint = { color: "var(--text-faint)" } as React.CSSProperties;

  return (
    <div
      className="absolute top-3 right-16 w-[340px] max-h-[70vh] overflow-y-auto rounded-md"
      style={cardStyle}
    >
      <div className="flex items-start justify-between px-4 py-3" style={divider}>
        <div>
          <div className="text-xs uppercase tracking-wider" style={muted}>
            {data?.kind}
          </div>
          <div className="text-base font-semibold">
            {isLoading ? "…" : (data?.name_local ?? data?.name)}
          </div>
          {data?.name && data?.name_local && data.name !== data.name_local && (
            <div className="text-xs" style={muted}>{data.name}</div>
          )}
          {data?.code && (
            <div className="text-[10px] mt-0.5" style={faint}>{data.code}</div>
          )}
        </div>
        <button
          onClick={() => selectTerritory(null)}
          className="text-lg leading-none px-1"
          style={muted}
        >
          ×
        </button>
      </div>

      {data?.empire && (
        <div className="px-4 py-2 text-xs" style={{ ...divider, ...muted }}>
          <span style={faint}>імперія:</span>{" "}
          {data.empire === "russian_empire" ? "Російська" :
            data.empire === "austro_hungarian" ? "Австро-Угорщина" : data.empire}
        </div>
      )}

      {data?.transit_profile && (
        <div className="px-4 py-2 text-xs" style={divider}>
          <div className="uppercase tracking-wider mb-1" style={faint}>Транзит</div>
          {data.transit_profile.operator && (
            <div><span style={faint}>оператор:</span> {data.transit_profile.operator}</div>
          )}
          {(data.transit_profile.active_from || data.transit_profile.active_to) && (
            <div>
              <span style={faint}>активний:</span>{" "}
              {data.transit_profile.active_from ?? "?"} → {data.transit_profile.active_to ?? "тепер"}
            </div>
          )}
        </div>
      )}

      {data?.notes && (
        <div className="px-4 py-2 text-xs" style={{ ...divider, color: "var(--text-base)" }}>
          {data.notes}
        </div>
      )}

      {data?.periods && data.periods.length > 0 && (
        <div className="px-4 py-2 text-xs" style={divider}>
          <div className="uppercase tracking-wider mb-1" style={faint}>Періоди / статус</div>
          {data.periods.map((p) => (
            <div key={p.id} className="mb-1 leading-snug">
              <span style={muted}>{p.year_from}–{p.year_to}:</span>{" "}
              {p.name_local ?? p.name ?? data.name_local ?? data.name}
              {p.status && <span style={faint}> · {p.status}</span>}
            </div>
          ))}
        </div>
      )}

      <div className="px-4 py-2 text-xs" style={divider}>
        <div className="flex items-center justify-between mb-1">
          <span className="uppercase tracking-wider" style={faint}>
            Статичні факти {data?.stats?.length ? `(${data.stats.length})` : ""}
          </span>
        </div>
        {!data?.stats?.length && (
          <div className="italic mb-1" style={faint}>немає</div>
        )}
        {data?.stats?.map((s) => (
          <div key={s.id} className="mb-1 flex items-start justify-between gap-2 leading-snug">
            <div>
              <span style={muted}>{STAT_KIND_LABEL[s.stat_kind] ?? s.stat_kind}</span>
              {s.group_label && <span> · {s.group_label}</span>}
              {": "}
              {s.count != null
                ? s.count.toLocaleString("uk")
                : s.count_lower != null
                ? `${s.count_lower.toLocaleString("uk")}–${s.count_upper?.toLocaleString("uk")}`
                : "?"}
              {s.as_of_year != null && <span style={faint}> · станом на {s.as_of_year}</span>}
              {s.provisional && <span style={{ color: "#e07b3a" }}> · provisional</span>}
            </div>
            <Popconfirm
              title="Видалити факт?"
              onConfirm={() => delStat.mutate(s.id)}
              okText="Так" cancelText="Ні"
            >
              <button style={faint}>×</button>
            </Popconfirm>
          </div>
        ))}
        <AddStatForm territoryId={selectedId} />
      </div>

      <div className="px-4 py-2">
        <div className="uppercase tracking-wider text-[10px] mb-1" style={faint}>
          Джерела {data?.sources?.length ? `(${data.sources.length})` : ""}
        </div>
        {!data?.sources?.length && (
          <div className="text-xs italic" style={faint}>не задано</div>
        )}
        {data?.sources?.map((s) => (
          <div key={s.id} className="mb-2 text-xs">
            <div className="font-medium">{s.short_title}</div>
            <div className="leading-snug" style={muted}>{s.citation}</div>
            {s.note && <div className="italic mt-0.5" style={faint}>{s.note}</div>}
            {s.url && (
              <a href={s.url} target="_blank" rel="noreferrer"
                 className="text-[10px] hover:underline"
                 style={{ color: "var(--accent)" }}>
                {s.url}
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const AddStatForm: React.FC<{ territoryId: number }> = ({ territoryId }) => {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<StatKind>("diaspora_stock");
  const [group, setGroup] = useState("");
  const [year, setYear] = useState<number | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const [method, setMethod] = useState<"exact" | "estimate" | "range" | "unknown">("estimate");
  const [sourceIds, setSourceIds] = useState<number[]>([]);
  const createStat = useCreateStat();

  const faint = { color: "var(--text-faint)" } as React.CSSProperties;

  const reset = () => {
    setKind("diaspora_stock"); setGroup(""); setYear(null);
    setCount(null); setMethod("estimate"); setSourceIds([]);
  };

  const submit = async () => {
    if (year == null) { message.error("Вкажіть рік (станом на)"); return; }
    if ((method === "exact" || method === "estimate") && count == null) {
      message.error("Вкажіть кількість"); return;
    }
    try {
      await createStat.mutateAsync({
        territory_id: territoryId,
        stat_kind: kind,
        group_label: group || null,
        as_of_year: year,
        count: method === "exact" || method === "estimate" ? count : null,
        count_method: method,
        sources: sourceIds.map((id) => ({ source_id: id })),
      });
      message.success(sourceIds.length ? "Факт додано" : "Факт додано (provisional)");
      reset(); setOpen(false);
    } catch (e: any) {
      message.error(e?.response?.data?.detail?.[0]?.msg ?? "Помилка");
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs hover:underline mt-1"
        style={{ color: "var(--accent)" }}
      >
        + додати факт
      </button>
    );
  }

  return (
    <div className="mt-2 flex flex-col gap-1.5">
      <Select<StatKind>
        size="small" value={kind} onChange={setKind}
        options={Object.entries(STAT_KIND_LABEL).map(([value, label]) => ({ value: value as StatKind, label }))}
      />
      {kind === "diaspora_stock" && (
        <Input size="small" placeholder="група (напр. українці)" value={group}
               onChange={(e) => setGroup(e.target.value)} />
      )}
      <div className="flex gap-1.5">
        <InputNumber size="small" placeholder="рік" min={1500} max={2100} style={{ flex: 1 }}
                     value={year ?? undefined} onChange={(v) => setYear(v != null ? Number(v) : null)} />
        <Select size="small" value={method} onChange={setMethod} style={{ width: 110 }}
                options={[
                  { value: "exact", label: "точно" },
                  { value: "estimate", label: "оцінка" },
                  { value: "unknown", label: "невідомо" },
                ]} />
      </div>
      {(method === "exact" || method === "estimate") && (
        <InputNumber size="small" placeholder="кількість осіб" min={0} style={{ width: "100%" }}
                     value={count ?? undefined} onChange={(v) => setCount(v != null ? Number(v) : null)} />
      )}
      <SourcePicker value={sourceIds} onChange={setSourceIds} onAddNew={() => {}} />
      <span style={{ ...faint, fontSize: 10 }}>
        {sourceIds.length === 0 ? "без джерела → provisional" : `${sourceIds.length} джерело(а)`}
      </span>
      <div className="flex gap-2">
        <button type="button" onClick={submit} className="text-xs px-2 py-0.5 rounded"
                style={{ background: "var(--accent-soft)", color: "var(--text-strong)", border: "1px solid var(--accent)" }}>
          зберегти
        </button>
        <button type="button" onClick={() => { reset(); setOpen(false); }} className="text-xs" style={faint}>
          скасувати
        </button>
      </div>
    </div>
  );
};

export default InspectorPanel;
