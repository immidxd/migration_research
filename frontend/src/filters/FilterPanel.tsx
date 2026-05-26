import React from "react";

import { useTerritoryList } from "../api/territories";
import { usePeriods } from "../api/periods";
import {
  Empire,
  MigrationVector,
  TerritoryKind,
  useFilters,
} from "../store";

const KIND_OPTIONS: { value: TerritoryKind; label: string }[] = [
  { value: "country", label: "Країни" },
  { value: "region", label: "Регіони (парасолькові)" },
  { value: "gubernia", label: "Губернії" },
  { value: "uezd", label: "Повіти" },
  { value: "settlement", label: "Поселення" },
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
  <div className="px-4 py-3 border-b border-black/30">
    <div className="text-xs uppercase tracking-wider text-white/50 mb-2">{title}</div>
    {children}
  </div>
);

const Check: React.FC<{ checked: boolean; onChange: () => void; label: string; hint?: string }> = (
  { checked, onChange, label, hint },
) => (
  <label className="flex items-start gap-2 py-1 cursor-pointer select-none hover:text-white">
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      className="mt-1 accent-accent"
    />
    <span className="text-sm leading-tight">
      <span>{label}</span>
      {hint && <div className="text-xs text-white/40">{hint}</div>}
    </span>
  </label>
);

const FilterPanel: React.FC = () => {
  const {
    kinds, empires, vectors,
    toggleKind, toggleEmpire, toggleVector,
    selectedTerritoryId, selectTerritory,
    selectedPeriodId, selectPeriod,
  } = useFilters();

  const regionsQ = useTerritoryList(["region"]);
  const portsQ = useTerritoryList(["port", "border_crossing"]);
  const periodsQ = usePeriods();

  return (
    <div className="text-white/85">
      <div className="px-4 py-4 border-b border-black/40">
        <div className="text-lg font-semibold">Migrations</div>
        <div className="text-xs text-white/50">Research workspace</div>
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
        <div className="text-[10px] text-white/30 mt-1">
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

      <Section title="Періоди">
        {periodsQ.isLoading && <div className="text-white/40 text-sm">завантаження…</div>}
        {periodsQ.data?.map((p) => (
          <label
            key={p.id}
            className="flex items-start gap-2 py-1 cursor-pointer hover:text-white"
          >
            <input
              type="radio"
              name="period"
              checked={selectedPeriodId === p.id}
              onChange={() => selectPeriod(p.id)}
              className="mt-1 accent-accent"
            />
            <span className="text-sm leading-tight">
              <span>{p.name}</span>
              <div className="text-xs text-white/40">
                {p.date_from} → {p.date_to}
              </div>
            </span>
          </label>
        ))}
        {selectedPeriodId != null && (
          <button
            className="text-xs text-white/40 hover:text-white mt-1"
            onClick={() => selectPeriod(null)}
          >
            скинути
          </button>
        )}
      </Section>

      <Section title={`Регіони (${regionsQ.data?.count ?? 0})`}>
        {regionsQ.data?.items.map((t) => (
          <button
            key={t.id}
            onClick={() => selectTerritory(t.id)}
            className={`block w-full text-left py-1 text-sm hover:text-white ${
              selectedTerritoryId === t.id ? "text-accent" : "text-white/70"
            }`}
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
            className={`block w-full text-left py-1 text-sm hover:text-white ${
              selectedTerritoryId === t.id ? "text-accent" : "text-white/70"
            }`}
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
