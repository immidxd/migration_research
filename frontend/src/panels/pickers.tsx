import React, { useEffect, useMemo, useState } from "react";
import { Select, Spin } from "antd";

import {
  searchSources,
  searchTerritories,
  SourceRow,
  TerritorySearchRow,
} from "../api/flows";


type Option = { label: React.ReactNode; value: number };

export const TerritoryPicker: React.FC<{
  value: number | null;
  onChange: (id: number | null, t: TerritorySearchRow | null) => void;
  placeholder?: string;
  kinds?: string[];
}> = ({ value, onChange, placeholder = "пошук території…", kinds }) => {
  const [opts, setOpts] = useState<Map<number, TerritorySearchRow>>(new Map());
  const [loading, setLoading] = useState(false);

  // Resolve current value into a label by fetching it once
  useEffect(() => {
    if (value == null || opts.has(value)) return;
    (async () => {
      const all = await searchTerritories("", kinds);
      setOpts((m) => {
        const next = new Map(m);
        for (const r of all) next.set(r.id, r);
        return next;
      });
    })();
  }, [value, kinds, opts]);

  const search = async (q: string) => {
    setLoading(true);
    try {
      const rows = await searchTerritories(q, kinds);
      setOpts((m) => {
        const next = new Map(m);
        for (const r of rows) next.set(r.id, r);
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  const options: Option[] = useMemo(
    () =>
      Array.from(opts.values()).map((t) => ({
        value: t.id,
        label: (
          <span>
            <span className="opacity-50 text-[10px] uppercase mr-1">{t.kind}</span>
            {t.name_local ?? t.name}
            {t.code && <span className="opacity-40 text-[10px] ml-1">· {t.code}</span>}
          </span>
        ),
      })),
    [opts]
  );

  return (
    <Select
      showSearch
      placeholder={placeholder}
      value={value ?? undefined}
      onSearch={search}
      onChange={(v) => onChange(v ?? null, v != null ? opts.get(v) ?? null : null)}
      filterOption={false}
      notFoundContent={loading ? <Spin size="small" /> : null}
      options={options}
      style={{ width: "100%" }}
      allowClear
    />
  );
};


export const SourcePicker: React.FC<{
  value: number[];
  onChange: (ids: number[]) => void;
  onAddNew: () => void;
}> = ({ value, onChange, onAddNew }) => {
  const [opts, setOpts] = useState<Map<number, SourceRow>>(new Map());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      const initial = await searchSources("");
      setOpts((m) => {
        const next = new Map(m);
        for (const r of initial) next.set(r.id, r);
        return next;
      });
    })();
  }, []);

  const search = async (q: string) => {
    setLoading(true);
    try {
      const rows = await searchSources(q);
      setOpts((m) => {
        const next = new Map(m);
        for (const r of rows) next.set(r.id, r);
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  const options: Option[] = useMemo(
    () =>
      Array.from(opts.values()).map((s) => ({
        value: s.id,
        label: (
          <span>
            {s.short_title}
            {s.year && <span className="opacity-40 ml-1 text-[10px]">· {s.year}</span>}
          </span>
        ),
      })),
    [opts]
  );

  return (
    <div className="flex flex-col gap-1">
      <Select
        mode="multiple"
        showSearch
        placeholder="оберіть джерела…"
        value={value}
        onSearch={search}
        onChange={(v) => onChange(v as number[])}
        filterOption={false}
        notFoundContent={loading ? <Spin size="small" /> : null}
        options={options}
        style={{ width: "100%" }}
      />
      <button
        type="button"
        onClick={onAddNew}
        className="self-start text-xs text-accent hover:underline"
      >
        + нове джерело
      </button>
    </div>
  );
};
