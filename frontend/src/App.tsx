import React from "react";
import FilterPanel from "./filters/FilterPanel";
import MapView from "./map/MapView";
import Timeline from "./timeline/Timeline";

const App: React.FC = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <aside className="w-[320px] shrink-0 bg-sidebar border-r border-black/40 overflow-y-auto">
        <FilterPanel />
      </aside>
      <main className="flex-1 flex flex-col">
        <div className="flex-1 relative">
          <MapView />
        </div>
        <div className="h-[140px] border-t border-black/40 bg-panel">
          <Timeline />
        </div>
      </main>
    </div>
  );
};

export default App;
