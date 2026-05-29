import React from "react";

import { useTerritoryList } from "../api/territories";
import { useFlows } from "../api/flows";
import {
  Empire,
  MigrationVector,
  TerritoryKind,
  useFilters,
} from "../store";

const ThemeToggle: React.FC = () => {
  const theme = useFilters((s) => s.theme);
  const setTheme = useFilters((s) => s.setTheme);
  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      title={theme === "dark" ? "Перемкнути на світлу тему" : "Перемкнути на темну"}
      className="rounded-md px-2 py-1 text-sm transition"
      style={{
        background: "var(--bg-panel)",
        color: "var(--text-base)",
        border: "1px solid var(--border-soft)",
      }}
    >
      {theme === "dark" ? "☀︎" : "☾"}
    </button>
  );
};

const KIND_OPTIONS: { value: TerritoryKind; label: string }[] = [
  { value: "country", label: "Країни" },
  { value: "region", label: "Регіони (парасолькові)" },
  { value: "gubernia", label: "Губернії" },
  { value: "uezd", label: "Повіти" },
  { value: "subdivision", label: "Штати / провінції" },
  { value: "settlement", label: "Поселення / міста" },
  { value: "port", label: "Порти" },
  { value: "border_crossing", label: "Переходи / станції" },
];

const EMPIRE_OPTIONS: { value: Empire; label: string }[] = [
  { value: "russian_empire", label: "Російська імперія" },
  { value: "austro_hungarian", label: "Австро-Угорщина" },
  { value: "other", label: "Інше" },
];

const VECTOR_OPTIONS: { value: MigrationVector; label: string; hint: string }[] = [
  { value: "transatlantic", label: "Трансатлантичний", hint: "США, Канада, Бразилія, Аргентина" },
  { value: "european", label: "Європейський", hint: "Франція, Чехія, Балкани…" },
  { value: "intra_imperial_east", label: "Сх. внутрішньоімперський", hint: "Поволжя, Урал, Сибір, ДС" },
  { value: "intra_imperial_other", label: "Інший внутрішньоімперський", hint: "Кавказ, Туркестан…" },
  { value: "internal", label: "Внутрішній", hint: "У межах укр. земель" },
];

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border-soft)" }}>
    <div
      className="text-xs uppercase tracking-wider mb-2"
      style={{ color: "var(--text-muted)" }}
    >
      {title}
    </div>
    {children}
  </div>
);

const Check: React.FC<{ checked: boolean; onChange: () => void; label: string; hint?: string }> = (
  { checked, onChange, label, hint },
) => (
  <label
    className="flex items-start gap-2 py-1 cursor-pointer select-none"
    style={{ color: "var(--text-base)" }}
  >
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      className="mt-1"
      style={{ accentColor: "var(--accent)" }}
    />
    <span className="text-sm leading-tight">
      <span>{label}</span>
      {hint && <div className="text-xs" style={{ color: "var(--text-faint)" }}>{hint}</div>}
    </span>
  </label>
);

const FilterPanel: React.FC = () => {
  const {
    kinds, empires, vectors,
    toggleKind, toggleEmpire, toggleVector,
    selectedTerritoryId, selectTerritory,
  } = useFilters();

  const setStatsReportOpen = useFilters((s) => s.setStatsReportOpen);
  const setFlowsDrawerOpen = useFilters((s) => s.setFlowsDrawerOpen);
  const flowsQ = useFlows();
  const flowsCount = flowsQ.data?.length ?? 0;
  const regionsQ = useTerritoryList(["region"]);
  const portsQ = useTerritoryList(["port", "border_crossing"]);

  return (
    <div style={{ color: "var(--text-base)" }}>
      <div
        className="px-4 py-4 flex items-start justify-between gap-2"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div>
          <div className="text-lg font-semibold">Migrations</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>
            Research workspace
          </div>
        </div>
        <ThemeToggle />
      </div>

      <Section title="Вектори">
        {VECTOR_OPTIONS.map((v) => (
          <Check
            key={v.value}
            checked={vectors.has(v.value)}
            onChange={() => toggleVector(v.value)}
            label={v.label}
            hint={v.hint}
          />
        ))}
        <div className="text-[10px] mt-1" style={{ color: "var(--text-faint)" }}>
          Поки немає завантажених потоків — тумблери впливатимуть на флоу-шар, коли він з'явиться.
        </div>
      </Section>

      <Section title="Імперія / юрисдикція">
        {EMPIRE_OPTIONS.map((e) => (
          <Check
            key={e.value}
            checked={empires.has(e.value)}
            onChange={() => toggleEmpire(e.value)}
            label={e.label}
          />
        ))}
      </Section>

      <Section title="Типи територій">
        {KIND_OPTIONS.map((k) => (
          <Check
            key={k.value}
            checked={kinds.has(k.value)}
            onChange={() => toggleKind(k.value)}
            label={k.label}
          />
        ))}
      </Section>

      <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border-soft)" }}>
        <button
          onClick={() => setStatsReportOpen(true)}
          className="w-full px-2 py-1.5 text-sm rounded"
          style={{
            background: "var(--accent-soft)",
            color: "var(--text-strong)",
            border: "1px solid var(--accent)",
          }}
        >
          📊 Статистика напряму
        </button>
      </div>

      <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border-soft)" }}>
        <button
          onClick={() => setFlowsDrawerOpen(true)}
          className="w-full flex items-center justify-between px-2 py-1.5 text-sm rounded"
          style={{
            background: "var(--bg-panel)",
            color: "var(--text-base)",
            border: "1px solid var(--border-soft)",
          }}
        >
          <span>Введені потоки</span>
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{ background: "var(--accent-soft)", color: "var(--text-strong)" }}
          >
            {flowsCount}
          </span>
        </button>
      </div>

      <Section title={`Регіони (${regionsQ.data?.count ?? 0})`}>
        {regionsQ.data?.items.map((t) => (
          <button
            key={t.id}
            onClick={() => selectTerritory(t.id)}
            className="block w-full text-left py-1 text-sm"
            style={{
              color: selectedTerritoryId === t.id ? "var(--accent)" : "var(--text-base)",
            }}
            title={t.code ?? undefined}
          >
            {t.name_local ?? t.name}
          </button>
        ))}
      </Section>

      <Section title={`Транзитні точки (${portsQ.data?.count ?? 0})`}>
        {portsQ.data?.items.map((t) => (
          <button
            key={t.id}
            onClick={() => selectTerritory(t.id)}
            className="block w-full text-left py-1 text-sm"
            style={{
              color: selectedTerritoryId === t.id ? "var(--accent)" : "var(--text-base)",
            }}
            title={t.code ?? undefined}
          >
            {t.name}
          </button>
        ))}
      </Section>
    </div>
  );
};

export default FilterPanel;
