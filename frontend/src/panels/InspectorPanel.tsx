import React from "react";

import { useTerritory } from "../api/territories";
import { useFilters } from "../store";

const InspectorPanel: React.FC = () => {
  const selectedId = useFilters((s) => s.selectedTerritoryId);
  const selectTerritory = useFilters((s) => s.selectTerritory);
  const { data, isLoading } = useTerritory(selectedId);

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

export default InspectorPanel;
