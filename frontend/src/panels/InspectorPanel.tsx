import React from "react";

import { useTerritory } from "../api/territories";
import { useFilters } from "../store";

const InspectorPanel: React.FC = () => {
  const selectedId = useFilters((s) => s.selectedTerritoryId);
  const selectTerritory = useFilters((s) => s.selectTerritory);
  const { data, isLoading } = useTerritory(selectedId);

  if (selectedId == null) return null;

  return (
    <div className="absolute top-3 right-3 w-[340px] max-h-[70vh] overflow-y-auto bg-panel/95 border border-black/40 rounded-md shadow-xl text-white/90">
      <div className="flex items-start justify-between px-4 py-3 border-b border-black/30">
        <div>
          <div className="text-xs uppercase tracking-wider text-white/40">
            {data?.kind}
          </div>
          <div className="text-base font-semibold">
            {isLoading ? "…" : (data?.name_local ?? data?.name)}
          </div>
          {data?.name && data?.name_local && data.name !== data.name_local && (
            <div className="text-xs text-white/50">{data.name}</div>
          )}
          {data?.code && (
            <div className="text-[10px] text-white/30 mt-0.5">{data.code}</div>
          )}
        </div>
        <button
          onClick={() => selectTerritory(null)}
          className="text-white/40 hover:text-white text-lg leading-none px-1"
        >
          ×
        </button>
      </div>

      {data?.empire && (
        <div className="px-4 py-2 border-b border-black/30 text-xs text-white/60">
          <span className="text-white/40">імперія:</span>{" "}
          {data.empire === "russian_empire" ? "Російська" :
            data.empire === "austro_hungarian" ? "Австро-Угорщина" : data.empire}
        </div>
      )}

      {data?.transit_profile && (
        <div className="px-4 py-2 border-b border-black/30 text-xs">
          <div className="text-white/40 uppercase tracking-wider mb-1">Транзит</div>
          {data.transit_profile.operator && (
            <div><span className="text-white/40">оператор:</span> {data.transit_profile.operator}</div>
          )}
          {(data.transit_profile.active_from || data.transit_profile.active_to) && (
            <div>
              <span className="text-white/40">активний:</span>{" "}
              {data.transit_profile.active_from ?? "?"} → {data.transit_profile.active_to ?? "тепер"}
            </div>
          )}
        </div>
      )}

      {data?.notes && (
        <div className="px-4 py-2 border-b border-black/30 text-xs text-white/70">
          {data.notes}
        </div>
      )}

      <div className="px-4 py-2">
        <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">
          Джерела {data?.sources?.length ? `(${data.sources.length})` : ""}
        </div>
        {!data?.sources?.length && (
          <div className="text-xs italic text-white/30">не задано</div>
        )}
        {data?.sources?.map((s) => (
          <div key={s.id} className="mb-2 text-xs">
            <div className="text-white/85 font-medium">{s.short_title}</div>
            <div className="text-white/50 leading-snug">{s.citation}</div>
            {s.note && <div className="text-white/40 italic mt-0.5">{s.note}</div>}
            {s.url && (
              <a href={s.url} target="_blank" rel="noreferrer"
                 className="text-accent text-[10px] hover:underline">
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
