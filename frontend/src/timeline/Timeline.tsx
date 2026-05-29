import React, { useEffect, useMemo, useRef, useState } from "react";
import { Slider, Select } from "antd";

import { useTemporalLabels } from "../api/temporal";
import {
  scopeDescribe,
  TemporalLabel,
  TemporalLabelKind,
  useFilters,
} from "../store";


const YEAR_MIN = 1800;
const YEAR_MAX = 1960;

const KIND_GROUPS: { kind: TemporalLabelKind; label: string }[] = [
  { kind: "named_period", label: "Іменовані періоди" },
  { kind: "era_label", label: "Епохи (Поч./Сер./Кін.)" },
  { kind: "century", label: "Століття" },
  { kind: "half_century", label: "Півстоліття" },
  { kind: "quarter_century", label: "Чверть століття" },
  { kind: "decade", label: "Десятиліття" },
];

/** Mark every 20th year on the slider rail. */
function buildMarks() {
  const marks: Record<number, { label: string; style?: React.CSSProperties }> = {};
  for (let y = YEAR_MIN; y <= YEAR_MAX; y += 20) {
    marks[y] = {
      label: String(y),
      style: { color: "rgba(255,255,255,0.55)", fontSize: 10 },
    };
  }
  return marks;
}

const Timeline: React.FC = () => {
  const scope = useFilters((s) => s.scope);
  const setScope = useFilters((s) => s.setScope);
  const labelsQ = useTemporalLabels();

  // Mode toggle: year | range | label
  const [mode, setMode] = useState<"year" | "range" | "label">(
    scope.mode === "none" ? "year" : (scope.mode as any)
  );

  // Local working state mirrors the store but lets us edit without thrashing
  const [year, setYear] = useState<number>(
    scope.mode === "year" ? scope.year : 1900
  );
  const [range, setRange] = useState<[number, number]>(
    scope.mode === "range" ? [scope.yearFrom, scope.yearTo] : [1880, 1914]
  );
  const [labelId, setLabelId] = useState<number | null>(
    scope.mode === "label" ? scope.labelId : null
  );

  const grouped = useMemo(() => {
    if (!labelsQ.data) return [];
    const byKind = new Map<TemporalLabelKind, TemporalLabel[]>();
    for (const l of labelsQ.data) {
      if (!byKind.has(l.kind)) byKind.set(l.kind, []);
      byKind.get(l.kind)!.push(l);
    }
    return KIND_GROUPS
      .filter((g) => byKind.has(g.kind))
      .map((g) => ({ ...g, items: byKind.get(g.kind)! }));
  }, [labelsQ.data]);

  // Live-apply: any slider/input/mode change updates the store immediately, no
  // "apply" button. Skip the first render so the default "усі періоди" scope
  // isn't replaced just by mounting the component.
  const firstRun = useRef(true);
  useEffect(() => {
    if (firstRun.current) { firstRun.current = false; return; }
    if (mode === "year") setScope({ mode: "year", year });
    else if (mode === "range") setScope({ mode: "range", yearFrom: range[0], yearTo: range[1] });
    else if (mode === "label" && labelId != null) {
      const lbl = labelsQ.data?.find((l) => l.id === labelId);
      if (lbl) setScope({ mode: "label", labelId, label: lbl });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, year, range[0], range[1], labelId]);

  const reset = () => setScope({ mode: "none" });

  const inputStyle: React.CSSProperties = {
    background: "var(--bg-base)",
    color: "var(--text-base)",
    border: "1px solid var(--border)",
    borderRadius: 4,
    padding: "4px 8px",
    width: 96,
    fontSize: 14,
    outline: "none",
  };

  return (
    <div className="h-full flex items-stretch" style={{ color: "var(--text-base)" }}>
      {/* Mode selector + scope readout */}
      <div
        className="flex flex-col justify-between px-4 py-2 w-[200px] shrink-0"
        style={{ borderRight: "1px solid var(--border)" }}
      >
        <div>
          <div
            className="text-[10px] uppercase tracking-wider mb-1"
            style={{ color: "var(--text-muted)" }}
          >
            Час
          </div>
          <div className="flex gap-1 mb-2">
            {(["year", "range", "label"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className="px-2 py-1 text-xs rounded"
                style={{
                  background: mode === m ? "var(--accent-soft)" : "transparent",
                  color: mode === m ? "var(--text-strong)" : "var(--text-muted)",
                  border: "1px solid var(--border-soft)",
                }}
              >
                {m === "year" ? "рік" : m === "range" ? "діапазон" : "мітка"}
              </button>
            ))}
          </div>
          <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>обрано:</div>
          <div className="text-sm font-medium leading-tight">{scopeDescribe(scope)}</div>
        </div>
        <div className="flex">
          <button
            onClick={reset}
            className="px-2 py-1 text-xs rounded"
            style={{
              background: "transparent",
              color: "var(--text-muted)",
              border: "1px solid var(--border-soft)",
            }}
          >
            скинути
          </button>
        </div>
      </div>

      {/* Mode-specific control */}
      <div className="flex-1 px-6 py-2 flex flex-col justify-center min-w-0">
        {mode === "year" && (
          <div className="flex items-center gap-4">
            <input
              type="number"
              min={YEAR_MIN}
              max={YEAR_MAX}
              value={year}
              onChange={(e) => setYear(Math.max(YEAR_MIN, Math.min(YEAR_MAX, Number(e.target.value))))}
              style={inputStyle}
            />
            <div className="flex-1 px-2">
              <Slider
                min={YEAR_MIN}
                max={YEAR_MAX}
                value={year}
                onChange={(v) => setYear(v as number)}
                marks={buildMarks()}
                step={1}
                tooltip={{ open: false }}
              />
            </div>
          </div>
        )}

        {mode === "range" && (
          <div className="flex items-center gap-4">
            <input
              type="number" min={YEAR_MIN} max={range[1]} value={range[0]}
              onChange={(e) => setRange([Number(e.target.value), range[1]])}
              style={inputStyle}
            />
            <div className="flex-1 px-2">
              <Slider
                range
                min={YEAR_MIN} max={YEAR_MAX}
                value={range}
                onChange={(v) => setRange(v as [number, number])}
                marks={buildMarks()}
                step={1}
                tooltip={{ open: false }}
              />
            </div>
            <input
              type="number" min={range[0]} max={YEAR_MAX} value={range[1]}
              onChange={(e) => setRange([range[0], Number(e.target.value)])}
              style={inputStyle}
            />
          </div>
        )}

        {mode === "label" && (
          <Select
            placeholder="оберіть мітку (період / епоху / століття / декаду)…"
            value={labelId ?? undefined}
            onChange={(v) => setLabelId(v)}
            showSearch
            optionFilterProp="label"
            style={{ width: "100%" }}
            options={grouped.map((g) => ({
              label: g.label,
              options: g.items.map((l) => ({
                label: `${l.label} · ${l.year_from}–${l.year_to}`,
                value: l.id,
              })),
            }))}
          />
        )}
      </div>
    </div>
  );
};

export default Timeline;
