import React, { useState } from "react";
import { Drawer, InputNumber, Select } from "antd";

import { useFlowAggregate } from "../api/analytics";
import { TerritorySearchRow } from "../api/flows";
import { TerritoryPicker } from "./pickers";

const VECTOR_OPTS = [
  { value: "transatlantic", label: "Трансатлантичний" },
  { value: "european", label: "Європейський" },
  { value: "intra_imperial_east", label: "Сх. внутрішньоімперський" },
  { value: "intra_imperial_other", label: "Інший внутрішньоімперський" },
  { value: "internal", label: "Внутрішній" },
];

const fmt = (n: number | null | undefined) =>
  n == null ? "—" : Math.round(n).toLocaleString("uk");

export const StatsReport: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const [origin, setOrigin] = useState<number | null>(null);
  const [originRow, setOriginRow] = useState<TerritorySearchRow | null>(null);
  const [yearFrom, setYearFrom] = useState<number | null>(null);
  const [yearTo, setYearTo] = useState<number | null>(null);
  const [vectors, setVectors] = useState<string[]>([]);

  const aggQ = useFlowAggregate({
    origin_id: origin,
    from_year: yearFrom,
    to_year: yearTo,
    vector: vectors.length ? vectors : undefined,
  });

  const data = aggQ.data;
  const muted: React.CSSProperties = { color: "var(--text-muted)" };
  const faint: React.CSSProperties = { color: "var(--text-faint)" };
  const label: React.CSSProperties = { ...faint, fontSize: 10, textTransform: "uppercase", letterSpacing: ".05em" };

  const resolved = data?.resolved;
  const gap = data ? data.naive_sum - (resolved?.point ?? 0) : 0;

  return (
    <Drawer title="Статистика напряму (без подвійного обліку)" open={open} onClose={onClose} width={460}>
      <div className="flex flex-col gap-3">
        <div>
          <div style={label} className="mb-1">Походження (або регіон/імперія — врахуються всі вкладені)</div>
          <TerritoryPicker
            value={origin}
            initialRow={originRow}
            onChange={(id, row) => { setOrigin(id); setOriginRow(row); }}
            placeholder="оберіть місце…"
          />
        </div>

        <div className="flex gap-2">
          <div className="flex-1">
            <div style={label} className="mb-1">з (рік)</div>
            <InputNumber min={1500} max={2100} style={{ width: "100%" }}
              value={yearFrom ?? undefined} onChange={(v) => setYearFrom(v != null ? Number(v) : null)} />
          </div>
          <div className="flex-1">
            <div style={label} className="mb-1">по (рік)</div>
            <InputNumber min={1500} max={2100} style={{ width: "100%" }}
              value={yearTo ?? undefined} onChange={(v) => setYearTo(v != null ? Number(v) : null)} />
          </div>
        </div>

        <div>
          <div style={label} className="mb-1">Вектор (необовʼязково)</div>
          <Select mode="multiple" allowClear placeholder="усі вектори"
            value={vectors} onChange={setVectors} options={VECTOR_OPTS} style={{ width: "100%" }} />
        </div>

        {origin == null && (
          <div className="text-xs italic" style={faint}>Оберіть місце, щоб порахувати.</div>
        )}

        {aggQ.isLoading && <div className="text-xs" style={muted}>рахую…</div>}

        {data && origin != null && (
          <div className="mt-1 flex flex-col gap-3">
            <div className="rounded-md p-3" style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border)" }}>
              <div style={label}>Чесна оцінка (resolved)</div>
              <div className="text-2xl font-semibold" style={{ color: "var(--text-strong)" }}>
                {resolved ? fmt(resolved.point) : "—"}
                <span className="text-sm font-normal" style={muted}> осіб</span>
              </div>
              {resolved?.has_overlap_uncertainty && (
                <div className="text-xs mt-0.5" style={{ color: "#e07b3a" }}>
                  діапазон {fmt(resolved.low)}–{fmt(resolved.high)} (є невизначені перетини)
                </div>
              )}
              {resolved?.some_counts_unknown && (
                <div className="text-xs mt-0.5" style={faint}>деякі потоки без кількості — не враховані в сумі</div>
              )}
              <div className="text-xs mt-1" style={muted}>
                наївна сума: {fmt(data.naive_sum)}
                {gap > 0 && <span style={{ color: "#e07b3a" }}> · усунено подвійного обліку {fmt(gap)}</span>}
              </div>
              <div className="text-[10px] mt-0.5" style={faint}>збігів-потоків: {data.matched}</div>
            </div>

            <div>
              <div style={label} className="mb-1">Враховано ({data.contributors.length})</div>
              {data.contributors.map((c) => (
                <div key={c.flow_id} className="text-xs flex justify-between gap-2 py-0.5" style={{ borderBottom: "1px solid var(--border-soft)" }}>
                  <span>{c.label}</span>
                  <span style={muted}>{c.magnitude != null ? fmt(c.magnitude) : "?"}</span>
                </div>
              ))}
            </div>

            {data.excluded.length > 0 && (
              <div>
                <div style={label} className="mb-1">Відсіяно ({data.excluded.length})</div>
                {data.excluded.map((e) => (
                  <div key={e.flow_id} className="text-xs py-0.5" style={faint}>
                    {e.label} — {e.reason}
                  </div>
                ))}
              </div>
            )}

            {data.overlaps_unknown_pairs.length > 0 && (
              <div className="text-xs" style={{ color: "#e07b3a" }}>
                ⚠ невизначені перетини між потоками: {data.overlaps_unknown_pairs.map((p) => `#${p[0]}↔#${p[1]}`).join(", ")}
              </div>
            )}
          </div>
        )}
      </div>
    </Drawer>
  );
};
