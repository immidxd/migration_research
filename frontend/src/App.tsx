import React from "react";
import FilterPanel from "./filters/FilterPanel";
import MapView from "./map/MapView";
import InspectorPanel from "./panels/InspectorPanel";
import { FlowEditor } from "./panels/FlowEditor";
import { FlowsDrawer } from "./panels/FlowsDrawer";
import { StatsReport } from "./panels/StatsReport";
import Timeline from "./timeline/Timeline";
import { useFilters } from "./store";

const App: React.FC = () => {
  const editorOpen = useFilters((s) => s.flowEditorOpen);
  const editingFlowId = useFilters((s) => s.editingFlowId);
  const openFlowEditor = useFilters((s) => s.openFlowEditor);
  const closeFlowEditor = useFilters((s) => s.closeFlowEditor);
  const statsReportOpen = useFilters((s) => s.statsReportOpen);
  const setStatsReportOpen = useFilters((s) => s.setStatsReportOpen);
  const flowsDrawerOpen = useFilters((s) => s.flowsDrawerOpen);
  const setFlowsDrawerOpen = useFilters((s) => s.setFlowsDrawerOpen);

  return (
    <div
      className="flex h-screen w-screen overflow-hidden"
      style={{ background: "var(--bg-base)", color: "var(--text-base)" }}
    >
      <aside
        className="w-[320px] shrink-0 overflow-y-auto"
        style={{ background: "var(--bg-sidebar)", borderRight: "1px solid var(--border)" }}
      >
        <FilterPanel />
      </aside>
      <main className="flex-1 flex flex-col">
        <div className="flex-1 relative" style={{ minHeight: 0 }}>
          <MapView />
          <InspectorPanel />
          <button
            onClick={() => openFlowEditor(null)}
            className="absolute top-3 right-3 w-11 h-11 rounded-full text-2xl font-bold shadow-lg transition flex items-center justify-center"
            title="Додати міграційний потік"
            style={{
              background: "var(--accent)",
              color: "var(--bg-base)",
              zIndex: 10,
            }}
          >
            +
          </button>
        </div>
        <div
          className="h-[110px]"
          style={{ background: "var(--bg-panel)", borderTop: "1px solid var(--border)" }}
        >
          <Timeline />
        </div>
      </main>
      <FlowEditor open={editorOpen} flowId={editingFlowId} onClose={closeFlowEditor} />
      <StatsReport open={statsReportOpen} onClose={() => setStatsReportOpen(false)} />
      <FlowsDrawer open={flowsDrawerOpen} onClose={() => setFlowsDrawerOpen(false)} />
    </div>
  );
};

export default App;
