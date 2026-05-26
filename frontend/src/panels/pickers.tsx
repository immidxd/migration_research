import React, { useEffect, useMemo, useState } from "react";
import { Select, Spin } from "antd";

import {
  searchSources,
  searchTerritories,
  SourceRow,
  TerritorySearchRow,
} from "../api/flows";


type Option = { label: React.ReactNode; value: number; raw: any };

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
}> = ({ value, onChange, placeholder = "пошук території…", kinds }) => {
  const [opts, setOpts] = useState<Map<number, TerritorySearchRow>>(new Map());
  const [loading, setLoading] = useState(false);

  const kindsKey = kinds?.join(",") ?? "";

  const fetch = async (q: string) => {
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

  // Preload initial list on mount / kind change so the dropdown isn't
  // empty when the user clicks before typing.
  useEffect(() => {
    fetch("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kindsKey]);

  const options: Option[] = useMemo(
    () =>
      Array.from(opts.values()).map((t) => ({
        value: t.id,
        raw: t,
        label: (
          <span>
            <span style={{ opacity: 0.5, textTransform: "uppercase", fontSize: 10, marginRight: 6 }}>
              {t.kind}
            </span>
            {t.name_local ?? t.name}
            {t.name_local && t.name && t.name_local !== t.name && (
              <span style={{ opacity: 0.4, fontSize: 11, marginLeft: 6 }}>· {t.name}</span>
            )}
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
      onSearch={fetch}
      onChange={(v) => onChange(v ?? null, v != null ? opts.get(v) ?? null : null)}
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
  const [opts, setOpts] = useState<Map<number, SourceRow>>(new Map());
  const [loading, setLoading] = useState(false);

  const fetch = async (q: string) => {
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

  useEffect(() => { fetch(""); }, []);

  const options = useMemo(
    () =>
      Array.from(opts.values()).map((s) => ({
        value: s.id,
        label: (
          <span>
            {s.short_title}
            {s.year && <span style={{ opacity: 0.4, marginLeft: 4, fontSize: 11 }}>· {s.year}</span>}
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
        onSearch={fetch}
        onChange={(v) => onChange(v as number[])}
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
