import React from "react";

// Placeholder sidebar matching the BMS filter layout. Sections will be
// wired up as backend endpoints land: vectors, period, territory cascade,
// destination, ports/stations, sources, precision, ethnicity, reason.
const Section: React.FC<{ title: string; children?: React.ReactNode }> = ({ title, children }) => (
  <div className="px-4 py-3 border-b border-black/30">
    <div className="text-xs uppercase tracking-wider text-white/50 mb-2">{title}</div>
    {children ?? <div className="text-white/30 text-sm italic">to be wired</div>}
  </div>
);

const FilterPanel: React.FC = () => {
  return (
    <div className="text-white">
      <div className="px-4 py-4 border-b border-black/40">
        <div className="text-lg font-semibold">Migrations</div>
        <div className="text-xs text-white/50">Research workspace</div>
      </div>
      <Section title="Vectors" />
      <Section title="Period" />
      <Section title="Territory of origin" />
      <Section title="Destination" />
      <Section title="Ports / stations" />
      <Section title="Sources" />
      <Section title="Precision" />
      <Section title="Ethnicity / confession" />
      <Section title="Reason" />
    </div>
  );
};

export default FilterPanel;
