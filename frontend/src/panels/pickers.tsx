import React, { useEffect, useMemo, useRef, useState } from "react";
import { Select, Spin } from "antd";

import {
  searchSources,
  searchTerritories,
  SourceRow,
  TerritorySearchRow,
} from "../api/flows";


/** Debounce a value by `ms`. Used so each keystroke doesn't fire a request. */
function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** Walk up the DOM looking for the antd Drawer body. Returning it as the
 *  popup container guarantees dropdown items are clickable — anchoring to
 *  `parentElement` was unreliable because Form.Item / Form wrappers have
 *  `overflow:hidden` that clipped the popup. */
export function drawerBodyOrSelf(trigger: HTMLElement): HTMLElement {
  let el: HTMLElement | null = trigger;
  while (el) {
    if (el.classList?.contains("ant-drawer-body")) return el;
    el = el.parentElement;
  }
  return trigger.parentElement ?? document.body;
}


export const TerritoryPicker: React.FC<{
  value: number | null;
  onChange: (id: number | null, t: TerritorySearchRow | null) => void;
  placeholder?: string;
  kinds?: string[];
  /** Seed the selected-row cache so a preselected value (e.g. when editing
   *  an existing flow) renders its label without waiting for a search hit. */
  initialRow?: TerritorySearchRow | null;
}> = ({ value, onChange, placeholder = "пошук території…", kinds, initialRow }) => {
  // Results of the CURRENT query only — not accumulated. Accumulating was the
  // bug: with filterOption=false the dropdown showed every row ever fetched,
  // so typing never narrowed the list.
  const [results, setResults] = useState<TerritorySearchRow[]>([]);
  const [loading, setLoading] = useState(false);
  // Cache of the currently selected row so its label still renders even when
  // it's not part of the latest query results.
  const [selectedRow, setSelectedRow] = useState<TerritorySearchRow | null>(initialRow ?? null);
  const [query, setQuery] = useState("");

  // Keep the cached label in sync when the parent seeds/changes the preselected
  // value (e.g. opening the editor on a different flow).
  useEffect(() => {
    if (initialRow && initialRow.id === value) setSelectedRow(initialRow);
  }, [initialRow, value]);

  const kindsKey = kinds?.join(",") ?? "";
  const debouncedQuery = useDebounced(query, 250);
  // Guard against out-of-order responses clobbering newer results.
  const reqSeq = useRef(0);

  useEffect(() => {
    const seq = ++reqSeq.current;
    setLoading(true);
    searchTerritories(debouncedQuery, kinds)
      .then((rows) => {
        if (seq === reqSeq.current) setResults(rows);
      })
      .finally(() => {
        if (seq === reqSeq.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, kindsKey]);

  const renderRow = (t: TerritorySearchRow): React.ReactNode => (
    <span>
      <span style={{ opacity: 0.5, textTransform: "uppercase", fontSize: 10, marginRight: 6 }}>
        {t.kind}
      </span>
      {t.name_local ?? t.name}
      {t.name_local && t.name && t.name_local !== t.name && (
        <span style={{ opacity: 0.4, fontSize: 11, marginLeft: 6 }}>· {t.name}</span>
      )}
    </span>
  );

  const options = useMemo(() => {
    const rows = [...results];
    // Keep the selected row visible even if it's not in the current results.
    if (selectedRow && !rows.some((r) => r.id === selectedRow.id)) {
      rows.unshift(selectedRow);
    }
    return rows.map((t) => ({ value: t.id, label: renderRow(t) }));
  }, [results, selectedRow]);

  return (
    <Select
      showSearch
      placeholder={placeholder}
      value={value ?? undefined}
      onSearch={setQuery}
      onChange={(v) => {
        const row = v != null ? results.find((r) => r.id === v) ?? selectedRow : null;
        setSelectedRow(row ?? null);
        onChange((v as number) ?? null, row ?? null);
      }}
      filterOption={false}
      notFoundContent={loading ? <Spin size="small" /> : "нічого не знайдено"}
      options={options}
      style={{ width: "100%" }}
      allowClear
      defaultActiveFirstOption={false}
      // Render the popup inside the Drawer's DOM, not at document.body —
      // otherwise the Drawer's overlay can intercept clicks on dropdown items.
      getPopupContainer={drawerBodyOrSelf}
    />
  );
};


export const SourcePicker: React.FC<{
  value: number[];
  onChange: (ids: number[]) => void;
  onAddNew: () => void;
}> = ({ value, onChange, onAddNew }) => {
  const [results, setResults] = useState<SourceRow[]>([]);
  const [loading, setLoading] = useState(false);
  // Cache of chosen rows so multi-select tags keep their labels across queries.
  const [chosen, setChosen] = useState<Map<number, SourceRow>>(new Map());
  const [query, setQuery] = useState("");

  const debouncedQuery = useDebounced(query, 250);
  const reqSeq = useRef(0);

  useEffect(() => {
    const seq = ++reqSeq.current;
    setLoading(true);
    searchSources(debouncedQuery)
      .then((rows) => {
        if (seq === reqSeq.current) setResults(rows);
      })
      .finally(() => {
        if (seq === reqSeq.current) setLoading(false);
      });
  }, [debouncedQuery]);

  const renderRow = (s: SourceRow): React.ReactNode => (
    <span>
      {s.short_title}
      {s.year && <span style={{ opacity: 0.4, marginLeft: 4, fontSize: 11 }}>· {s.year}</span>}
    </span>
  );

  const options = useMemo(() => {
    const byId = new Map<number, SourceRow>();
    for (const id of value) {
      const c = chosen.get(id);
      if (c) byId.set(id, c);
    }
    for (const r of results) byId.set(r.id, r);
    return Array.from(byId.values()).map((s) => ({ value: s.id, label: renderRow(s) }));
  }, [results, chosen, value]);

  return (
    <div className="flex flex-col gap-1">
      <Select
        mode="multiple"
        showSearch
        placeholder="оберіть джерела…"
        value={value}
        onSearch={setQuery}
        onChange={(v) => {
          const ids = v as number[];
          setChosen((prev) => {
            const next = new Map(prev);
            for (const id of ids) {
              const r = results.find((x) => x.id === id);
              if (r) next.set(id, r);
            }
            return next;
          });
          onChange(ids);
        }}
        filterOption={false}
        notFoundContent={loading ? <Spin size="small" /> : "нічого не знайдено"}
        options={options}
        style={{ width: "100%" }}
        getPopupContainer={drawerBodyOrSelf}
      />
      <button
        type="button"
        onClick={onAddNew}
        className="self-start text-xs hover:underline"
        style={{ color: "var(--accent)" }}
      >
        + нове джерело
      </button>
    </div>
  );
};
