import React, { useMemo, useState } from "react";
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

  const apply = () => {
    if (mode === "year") setScope({ mode: "year", year });
    else if (mode === "range") setScope({ mode: "range", yearFrom: range[0], yearTo: range[1] });
    else if (mode === "label" && labelId != null) {
      const lbl = labelsQ.data?.find((l) => l.id === labelId);
      if (lbl) setScope({ mode: "label", labelId, label: lbl });
    }
  };

  const reset = () => setScope({ mode: "none" });

  return (
    <div className="h-full flex items-stretch text-white/85">
      {/* Mode selector + scope readout */}
      <div className="flex flex-col justify-between px-4 py-2 border-r border-black/30 w-[200px] shrink-0">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-white/40 mb-1">Час</div>
          <div className="flex gap-1 mb-2">
            {(["year", "range", "label"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-2 py-1 text-xs rounded ${
                  mode === m
                    ? "bg-accent/30 text-white"
                    : "bg-white/5 text-white/60 hover:bg-white/10"
                }`}
              >
                {m === "year" ? "рік" : m === "range" ? "діапазон" : "мітка"}
              </button>
            ))}
          </div>
          <div className="text-[10px] text-white/40">обрано:</div>
          <div className="text-sm font-medium leading-tight">{scopeDescribe(scope)}</div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={apply}
            className="flex-1 px-2 py-1 text-xs bg-accent/30 hover:bg-accent/50 rounded"
          >
            застосувати
          </button>
          <button
            onClick={reset}
            className="px-2 py-1 text-xs bg-white/5 hover:bg-white/10 rounded"
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
              className="bg-black/30 border border-white/15 rounded px-2 py-1 w-24 text-base text-white focus:border-accent outline-none"
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
              className="bg-black/30 border border-white/15 rounded px-2 py-1 w-24 text-base text-white focus:border-accent outline-none"
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
              className="bg-black/30 border border-white/15 rounded px-2 py-1 w-24 text-base text-white focus:border-accent outline-none"
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
