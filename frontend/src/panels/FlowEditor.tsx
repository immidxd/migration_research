import React, { useEffect, useState } from "react";
import { Drawer, Form, Input, InputNumber, Radio, Select, Button, Modal, message } from "antd";

type TimeMode = "label" | "year" | "range";

import { useCreateFlow, useCreateSource, useFlow, useFlows, useUpdateFlow } from "../api/flows";
import {
  RelationKind,
  useCreateRelation,
  useDeleteRelation,
  useFlowRelations,
  useRelationCandidates,
} from "../api/relations";
import { drawerBodyOrSelf, SourcePicker, TerritoryPicker } from "./pickers";
import { useTemporalLabels } from "../api/temporal";

const REL_KIND_LABEL: Record<RelationKind, string> = {
  contains: "⊃ містить / є частиною",
  equals: "= тотожні",
  disjoint: "∥ розділені",
  overlaps_unknown: "≈ перетин невідомий",
};

const VECTOR_OPTS = [
  { value: "transatlantic", label: "Трансатлантичний" },
  { value: "european", label: "Європейський" },
  { value: "intra_imperial_east", label: "Сх. внутрішньоімперський" },
  { value: "intra_imperial_other", label: "Інший внутрішньоімперський" },
  { value: "internal", label: "Внутрішній (у межах укр. земель)" },
];

const TRANSPORT_OPTS = [
  { value: "sea", label: "Морський" },
  { value: "rail", label: "Залізничний" },
  { value: "land", label: "Суходільний" },
  { value: "river", label: "Річковий" },
  { value: "mixed", label: "Змішаний" },
  { value: "unknown", label: "Невідомо" },
];

const PRECISION_OPTS = [
  { value: "point", label: "Точка" },
  { value: "settlement", label: "Поселення" },
  { value: "volost", label: "Волость" },
  { value: "uezd", label: "Повіт" },
  { value: "gubernia", label: "Губернія" },
  { value: "region", label: "Регіон (парасольковий)" },
  { value: "country", label: "Країна" },
  { value: "vague", label: "Нечітко" },
];


import { TerritorySearchRow } from "../api/flows";

/** Map a picked territory's `kind` to the matching precision level, so the
 *  precision selects default sensibly (gubernia → gubernia, port → point…).
 *  The user can still override afterwards. */
const KIND_TO_PRECISION: Record<string, string> = {
  settlement: "settlement",
  volost: "volost",
  uezd: "uezd",
  gubernia: "gubernia",
  region: "region",
  country: "country",
  subdivision: "region",      // states / provinces — closest sub-national level
  port: "point",
  station: "point",
  border_crossing: "point",
};

const ConfirmChip: React.FC<{ row: TerritorySearchRow | null }> = ({ row }) => {
  if (!row) return null;
  return (
    <div
      className="mt-1 text-xs px-2 py-1 rounded"
      style={{
        background: "var(--accent-soft)",
        border: "1px solid var(--accent)",
        color: "var(--text-base)",
        display: "inline-block",
      }}
    >
      <span style={{ opacity: 0.6, textTransform: "uppercase", marginRight: 6 }}>
        {row.kind}
      </span>
      {row.name_local ?? row.name}
      {row.name_local && row.name && row.name_local !== row.name && (
        <span style={{ opacity: 0.6, marginLeft: 6 }}>· {row.name}</span>
      )}
    </div>
  );
};


export const FlowEditor: React.FC<{
  open: boolean;
  onClose: () => void;
  flowId?: number | null;
}> = ({ open, onClose, flowId = null }) => {
  const isEditing = flowId != null;
  const [origin, setOrigin] = useState<number | null>(null);
  const [destination, setDestination] = useState<number | null>(null);
  const [originRow, setOriginRow] = useState<TerritorySearchRow | null>(null);
  const [destRow, setDestRow] = useState<TerritorySearchRow | null>(null);

  // Time entry — three exclusive modes that all resolve to the canonical
  // date_from/date_to/date_precision triple on save.
  const [timeMode, setTimeMode] = useState<TimeMode>("range");
  const [labelId, setLabelId] = useState<number | null>(null);
  const [year, setYear] = useState<number | null>(null);
  const [yearFrom, setYearFrom] = useState<number | null>(null);
  const [yearTo, setYearTo] = useState<number | null>(null);

  const [vector, setVector] = useState<string>("intra_imperial_east");
  const [transport, setTransport] = useState<string>("rail");
  const [originPrec, setOriginPrec] = useState<string>("gubernia");
  const [destPrec, setDestPrec] = useState<string>("region");

  const [countMethod, setCountMethod] = useState<"exact" | "estimate" | "range" | "share" | "unknown">("exact");
  const [count, setCount] = useState<number | null>(null);
  const [countLower, setCountLower] = useState<number | null>(null);
  const [countUpper, setCountUpper] = useState<number | null>(null);
  // SHARE quantity
  const [sharePct, setSharePct] = useState<number | null>(null);
  const [shareBaseKind, setShareBaseKind] = useState<"flow" | "population">("flow");
  const [shareBaseFlowId, setShareBaseFlowId] = useState<number | null>(null);
  const [shareBaseTerrId, setShareBaseTerrId] = useState<number | null>(null);
  const [shareBaseTerrRow, setShareBaseTerrRow] = useState<TerritorySearchRow | null>(null);

  const [notes, setNotes] = useState<string>("");
  const [sourceIds, setSourceIds] = useState<number[]>([]);
  const [newSourceOpen, setNewSourceOpen] = useState(false);

  const labelsQ = useTemporalLabels();
  const createFlow = useCreateFlow();
  const updateFlow = useUpdateFlow();
  const flowQ = useFlow(open ? flowId : null);
  const flowsForBaseQ = useFlows();

  // Prefill from the loaded flow when editing; clear back to defaults when
  // opening for a new flow. Keyed on the editor opening / target changing.
  useEffect(() => {
    if (!open) return;
    if (!isEditing) { reset(); return; }
    const f = flowQ.data;
    if (!f) return;
    setOrigin(f.origin_territory_id);
    setDestination(f.destination_territory_id);
    setOriginRow({ id: f.origin_territory_id, kind: f.origin_precision, name: f.origin_name, name_local: null, code: null, empire: null });
    setDestRow({ id: f.destination_territory_id, kind: f.destination_precision, name: f.destination_name, name_local: null, code: null, empire: null });
    setOriginPrec(f.origin_precision);
    setDestPrec(f.destination_precision);
    if (f.temporal_label_id != null) {
      setTimeMode("label");
      setLabelId(f.temporal_label_id);
    } else if (f.date_from && f.date_to) {
      const yf = Number(f.date_from.slice(0, 4));
      const yt = Number(f.date_to.slice(0, 4));
      if (yf === yt) { setTimeMode("year"); setYear(yf); }
      else { setTimeMode("range"); setYearFrom(yf); setYearTo(yt); }
    } else {
      setTimeMode("range");
    }
    setVector(f.vector);
    setTransport(f.transport_mode);
    setCountMethod(f.count_method);
    setCount(f.count);
    setCountLower(f.count_lower);
    setCountUpper(f.count_upper);
    setSharePct(f.share_pct ?? null);
    setShareBaseKind((f.share_base_kind as "flow" | "population") ?? "flow");
    setShareBaseFlowId(f.share_base_flow_id ?? null);
    setShareBaseTerrId(f.share_base_territory_id ?? null);
    setNotes(f.notes ?? "");
    setSourceIds(f.sources.map((s) => s.source_id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, flowId, flowQ.data]);

  const reset = () => {
    setOrigin(null); setDestination(null);
    setOriginRow(null); setDestRow(null);
    setTimeMode("range"); setLabelId(null);
    setYear(null); setYearFrom(null); setYearTo(null);
    setVector("intra_imperial_east"); setTransport("rail");
    setOriginPrec("gubernia"); setDestPrec("region");
    setCountMethod("exact"); setCount(null); setCountLower(null); setCountUpper(null);
    setSharePct(null); setShareBaseKind("flow"); setShareBaseFlowId(null);
    setShareBaseTerrId(null); setShareBaseTerrRow(null);
    setNotes(""); setSourceIds([]);
  };

  /** Resolve the active time inputs into the API triple. */
  const resolveTime = (): {
    temporal_label_id: number | null;
    date_from: string | null;
    date_to: string | null;
    date_precision: string;
  } | null => {
    if (timeMode === "label") {
      if (labelId == null) return { temporal_label_id: null, date_from: null, date_to: null, date_precision: "unknown" };
      const lbl = labelsQ.data?.find((l) => l.id === labelId);
      if (!lbl) return null;
      return {
        temporal_label_id: lbl.id,
        date_from: `${lbl.year_from}-01-01`,
        date_to: `${lbl.year_to}-12-31`,
        date_precision: lbl.kind === "year" ? "year" : "period",
      };
    }
    if (timeMode === "year") {
      if (year == null) return { temporal_label_id: null, date_from: null, date_to: null, date_precision: "unknown" };
      return {
        temporal_label_id: null,
        date_from: `${year}-01-01`,
        date_to: `${year}-12-31`,
        date_precision: "year",
      };
    }
    // range
    if (yearFrom == null || yearTo == null) {
      message.error("Вкажіть «з» і «по» року");
      return null;
    }
    if (yearFrom > yearTo) {
      message.error("«з» має бути не пізніше за «по»");
      return null;
    }
    return {
      temporal_label_id: null,
      date_from: `${yearFrom}-01-01`,
      date_to: `${yearTo}-12-31`,
      date_precision: "year",
    };
  };

  const submit = async () => {
    if (!origin || !destination) {
      message.error("Вкажіть походження і пункт прибуття");
      return;
    }
    if (countMethod === "exact" && count == null) {
      message.error("Для точної оцінки потрібно ввести кількість");
      return;
    }
    if (countMethod === "range" && (countLower == null || countUpper == null)) {
      message.error("Для діапазону потрібні нижня і верхня межа");
      return;
    }
    if (countMethod === "share") {
      if (sharePct == null) { message.error("Вкажіть відсоток"); return; }
      if (shareBaseKind === "flow" && shareBaseFlowId == null) {
        message.error("Оберіть базовий потік для частки"); return;
      }
      if (shareBaseKind === "population" && shareBaseTerrId == null) {
        message.error("Оберіть територію для частки від населення"); return;
      }
    }
    const t = resolveTime();
    if (!t) return;
    const payload = {
      origin_territory_id: origin,
      destination_territory_id: destination,
      ...t,
      count: countMethod === "exact" || countMethod === "estimate" ? count : null,
      count_lower: countMethod === "range" ? countLower : null,
      count_upper: countMethod === "range" ? countUpper : null,
      count_method: countMethod,
      share_pct: countMethod === "share" ? sharePct : null,
      share_base_kind: countMethod === "share" ? shareBaseKind : null,
      share_base_flow_id: countMethod === "share" && shareBaseKind === "flow" ? shareBaseFlowId : null,
      share_base_territory_id: countMethod === "share" && shareBaseKind === "population" ? shareBaseTerrId : null,
      vector, transport_mode: transport,
      origin_precision: originPrec,
      destination_precision: destPrec,
      notes: notes || null,
      sources: sourceIds.map((id) => ({ source_id: id })),
    };
    try {
      if (isEditing) {
        await updateFlow.mutateAsync({ id: flowId!, payload });
        message.success("Потік оновлено");
      } else {
        await createFlow.mutateAsync(payload);
        message.success(
          sourceIds.length
            ? "Потік додано"
            : "Потік додано як provisional (без джерела)"
        );
      }
      reset();
      onClose();
    } catch (e: any) {
      message.error(e?.response?.data?.detail?.[0]?.msg ?? "Помилка збереження");
    }
  };

  return (
    <>
      <Drawer
        title={isEditing ? "Редагувати міграційний потік" : "Додати міграційний потік"}
        open={open}
        onClose={onClose}
        width={520}
        extra={
          <Button type="primary" onClick={submit} loading={createFlow.isPending || updateFlow.isPending}>
            Зберегти
          </Button>
        }
      >
        <Form layout="vertical">
          <Form.Item
            label="Походження"
            required
            help="Почніть писати назву і клацніть варіант зі списку (не Enter)"
          >
            <TerritoryPicker
              value={origin}
              initialRow={originRow}
              onChange={(id, row) => {
                setOrigin(id);
                setOriginRow(row);
                if (row && KIND_TO_PRECISION[row.kind]) setOriginPrec(KIND_TO_PRECISION[row.kind]);
              }}
              placeholder="звідки…"
            />
            <ConfirmChip row={originRow} />
          </Form.Item>
          <Form.Item label="Точність походження" required>
            <Select
              value={originPrec}
              onChange={setOriginPrec}
              options={PRECISION_OPTS}
              getPopupContainer={drawerBodyOrSelf}
            />
          </Form.Item>

          <Form.Item label="Пункт прибуття" required>
            <TerritoryPicker
              value={destination}
              initialRow={destRow}
              onChange={(id, row) => {
                setDestination(id);
                setDestRow(row);
                if (row && KIND_TO_PRECISION[row.kind]) setDestPrec(KIND_TO_PRECISION[row.kind]);
              }}
              placeholder="куди…"
            />
            <ConfirmChip row={destRow} />
          </Form.Item>
          <Form.Item label="Точність прибуття">
            <Select
              value={destPrec}
              onChange={setDestPrec}
              options={PRECISION_OPTS}
              getPopupContainer={drawerBodyOrSelf}
            />
          </Form.Item>

          <Form.Item
            label="Час"
            help="Один з трьох режимів. Усе зводиться до канонічного діапазону років у БД."
          >
            <Radio.Group
              value={timeMode}
              onChange={(e) => setTimeMode(e.target.value)}
              style={{ marginBottom: 8 }}
            >
              <Radio.Button value="range">діапазон років</Radio.Button>
              <Radio.Button value="year">конкретний рік</Radio.Button>
              <Radio.Button value="label">мітка (період / епоха / декада)</Radio.Button>
            </Radio.Group>

            {timeMode === "year" && (
              <InputNumber
                min={1500}
                max={2100}
                value={year ?? undefined}
                onChange={(v) => setYear(v != null ? Number(v) : null)}
                placeholder="напр. 1893"
                style={{ width: "100%" }}
              />
            )}

            {timeMode === "range" && (
              <div style={{ display: "flex", gap: 8 }}>
                <InputNumber
                  min={1500} max={2100}
                  value={yearFrom ?? undefined}
                  onChange={(v) => setYearFrom(v != null ? Number(v) : null)}
                  placeholder="з (рік)"
                  style={{ flex: 1 }}
                />
                <InputNumber
                  min={yearFrom ?? 1500} max={2100}
                  value={yearTo ?? undefined}
                  onChange={(v) => setYearTo(v != null ? Number(v) : null)}
                  placeholder="по (рік)"
                  style={{ flex: 1 }}
                />
              </div>
            )}

            {timeMode === "label" && (
              <Select
                showSearch
                optionFilterProp="label"
                allowClear
                placeholder="оберіть мітку…"
                value={labelId ?? undefined}
                onChange={(v) => setLabelId(v ?? null)}
                options={(labelsQ.data ?? []).map((l) => ({
                  value: l.id,
                  label: `[${l.kind}] ${l.label} · ${l.year_from}–${l.year_to}`,
                }))}
                style={{ width: "100%" }}
                getPopupContainer={drawerBodyOrSelf}
              />
            )}
          </Form.Item>

          <Form.Item label="Вектор" required>
            <Select
              value={vector}
              onChange={setVector}
              options={VECTOR_OPTS}
              getPopupContainer={drawerBodyOrSelf}
            />
          </Form.Item>
          <Form.Item label="Транспорт">
            <Select
              value={transport}
              onChange={setTransport}
              options={TRANSPORT_OPTS}
              getPopupContainer={drawerBodyOrSelf}
            />
          </Form.Item>

          <Form.Item label="Як відома кількість" required>
            <Radio.Group value={countMethod} onChange={(e) => setCountMethod(e.target.value)}>
              <Radio.Button value="exact">точно</Radio.Button>
              <Radio.Button value="estimate">оцінка</Radio.Button>
              <Radio.Button value="range">діапазон</Radio.Button>
              <Radio.Button value="share">частка</Radio.Button>
              <Radio.Button value="unknown">невідомо</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {countMethod === "share" && (
            <>
              <Form.Item label="Відсоток (%)" required help="Частка від явно вказаної бази">
                <InputNumber
                  min={0} max={100} value={sharePct ?? undefined}
                  onChange={(v) => setSharePct(v != null ? Number(v) : null)}
                  style={{ width: "100%" }}
                />
              </Form.Item>
              <Form.Item label="База частки" required>
                <Radio.Group value={shareBaseKind} onChange={(e) => setShareBaseKind(e.target.value)}>
                  <Radio.Button value="flow">від іншого потоку</Radio.Button>
                  <Radio.Button value="population">від населення</Radio.Button>
                </Radio.Group>
              </Form.Item>
              {shareBaseKind === "flow" && (
                <Form.Item label="Базовий потік" required>
                  <Select
                    showSearch optionFilterProp="label"
                    placeholder="оберіть потік…"
                    value={shareBaseFlowId ?? undefined}
                    onChange={(v) => setShareBaseFlowId(v ?? null)}
                    getPopupContainer={drawerBodyOrSelf}
                    options={(flowsForBaseQ.data ?? [])
                      .filter((fl) => fl.id !== flowId)
                      .map((fl) => ({
                        value: fl.id,
                        label: `#${fl.id} ${fl.origin_name} → ${fl.destination_name}` +
                          (fl.count != null ? ` (${fl.count.toLocaleString("uk")})` : ""),
                      }))}
                    style={{ width: "100%" }}
                  />
                </Form.Item>
              )}
              {shareBaseKind === "population" && (
                <Form.Item label="Територія (база населення)" required>
                  <TerritoryPicker
                    value={shareBaseTerrId}
                    initialRow={shareBaseTerrRow}
                    onChange={(id, row) => { setShareBaseTerrId(id); setShareBaseTerrRow(row); }}
                    placeholder="територія…"
                  />
                </Form.Item>
              )}
            </>
          )}

          {(countMethod === "exact" || countMethod === "estimate") && (
            <Form.Item label="Кількість осіб">
              <InputNumber
                min={0}
                value={count ?? undefined}
                onChange={(v) => setCount(v != null ? Number(v) : null)}
                style={{ width: "100%" }}
              />
            </Form.Item>
          )}
          {countMethod === "range" && (
            <div className="flex gap-2">
              <Form.Item label="Від" className="flex-1">
                <InputNumber
                  min={0} value={countLower ?? undefined}
                  onChange={(v) => setCountLower(v != null ? Number(v) : null)}
                  style={{ width: "100%" }}
                />
              </Form.Item>
              <Form.Item label="До" className="flex-1">
                <InputNumber
                  min={countLower ?? 0} value={countUpper ?? undefined}
                  onChange={(v) => setCountUpper(v != null ? Number(v) : null)}
                  style={{ width: "100%" }}
                />
              </Form.Item>
            </div>
          )}

          <Form.Item label="Нотатки">
            <Input.TextArea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Form.Item>

          <Form.Item
            label="Джерела"
            help={sourceIds.length === 0
              ? "Без джерел запис буде позначено як provisional"
              : `${sourceIds.length} джерело(а) обрано`}
          >
            <SourcePicker
              value={sourceIds}
              onChange={setSourceIds}
              onAddNew={() => setNewSourceOpen(true)}
            />
          </Form.Item>
        </Form>

        {isEditing && flowId != null && <RelationsSection flowId={flowId} />}
      </Drawer>

      <NewSourceModal
        open={newSourceOpen}
        onClose={() => setNewSourceOpen(false)}
        onCreated={(id) => {
          setSourceIds((ids) => [...ids, id]);
          setNewSourceOpen(false);
        }}
      />
    </>
  );
};


const RelationsSection: React.FC<{ flowId: number }> = ({ flowId }) => {
  const relationsQ = useFlowRelations(flowId);
  const [showCandidates, setShowCandidates] = useState(false);
  const candidatesQ = useRelationCandidates(showCandidates ? flowId : null);
  const createRel = useCreateRelation();
  const delRel = useDeleteRelation();

  const faint: React.CSSProperties = { color: "var(--text-faint)" };
  const muted: React.CSSProperties = { color: "var(--text-muted)" };

  return (
    <div className="mt-4 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
      <div className="text-xs uppercase tracking-wider mb-2" style={muted}>
        Звʼязки з іншими потоками
      </div>

      {(relationsQ.data ?? []).map((r) => (
        <div key={r.id} className="mb-1.5 text-xs flex items-start justify-between gap-2">
          <div className="leading-snug">
            <div style={{ color: "var(--accent)" }}>{REL_KIND_LABEL[r.kind]}</div>
            <div style={muted}>{r.from_label}</div>
            <div style={faint}>↳ {r.to_label}</div>
          </div>
          <button style={faint} onClick={() => delRel.mutate(r.id)} title="Видалити звʼязок">×</button>
        </div>
      ))}
      {relationsQ.data?.length === 0 && (
        <div className="text-xs italic mb-1" style={faint}>звʼязків ще немає</div>
      )}

      {!showCandidates ? (
        <button
          type="button"
          onClick={() => setShowCandidates(true)}
          className="text-xs hover:underline"
          style={{ color: "var(--accent)" }}
        >
          запропонувати кандидатів
        </button>
      ) : (
        <div className="mt-2">
          <div className="text-[10px] uppercase tracking-wider mb-1" style={faint}>
            Кандидати (підтвердь потрібні)
          </div>
          {candidatesQ.isLoading && <div className="text-xs" style={faint}>пошук…</div>}
          {candidatesQ.data?.length === 0 && (
            <div className="text-xs italic" style={faint}>кандидатів не знайдено</div>
          )}
          {(candidatesQ.data ?? []).map((c) => (
            <div key={c.other_flow_id} className="mb-1.5 text-xs flex items-start justify-between gap-2">
              <div className="leading-snug">
                <div>{c.other_label}</div>
                <div style={faint}>
                  {c.other_count != null && `${c.other_count.toLocaleString("uk")} ос. · `}
                  {c.other_period && `${c.other_period} · `}
                  <span style={{ color: "var(--accent)" }}>{REL_KIND_LABEL[c.kind]}</span>
                </div>
                <div style={faint}>{c.reason}</div>
              </div>
              <button
                type="button"
                className="text-xs px-2 py-0.5 rounded shrink-0"
                style={{ background: "var(--accent-soft)", color: "var(--text-strong)", border: "1px solid var(--accent)" }}
                onClick={() =>
                  createRel.mutate({
                    from_flow_id: c.from_flow_id,
                    to_flow_id: c.to_flow_id,
                    kind: c.kind,
                  })
                }
              >
                підтвердити
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};


const NewSourceModal: React.FC<{
  open: boolean;
  onClose: () => void;
  onCreated: (id: number) => void;
}> = ({ open, onClose, onCreated }) => {
  const [shortTitle, setShortTitle] = useState("");
  const [citation, setCitation] = useState("");
  const [kind, setKind] = useState<string>("monograph");
  const [year, setYear] = useState<number | null>(null);
  const [url, setUrl] = useState("");
  const createSource = useCreateSource();

  const reset = () => {
    setShortTitle(""); setCitation(""); setKind("monograph"); setYear(null); setUrl("");
  };

  const submit = async () => {
    if (!shortTitle.trim() || !citation.trim()) {
      message.error("Назва і повна цитата — обов'язкові");
      return;
    }
    try {
      const s = await createSource.mutateAsync({
        short_title: shortTitle.trim(),
        citation: citation.trim(),
        kind, year: year ?? undefined, url: url || undefined,
      });
      message.success("Джерело додано");
      onCreated(s.id);
      reset();
    } catch (e: any) {
      message.error("Помилка створення джерела");
    }
  };

  return (
    <Modal
      title="Нове джерело"
      open={open}
      onCancel={onClose}
      onOk={submit}
      okText="Додати"
      confirmLoading={createSource.isPending}
    >
      <Form layout="vertical">
        <Form.Item label="Коротка назва" required>
          <Input value={shortTitle} onChange={(e) => setShortTitle(e.target.value)} />
        </Form.Item>
        <Form.Item label="Повна цитата" required>
          <Input.TextArea rows={3} value={citation} onChange={(e) => setCitation(e.target.value)} />
        </Form.Item>
        <Form.Item label="Тип">
          <Select
            value={kind}
            onChange={setKind}
            options={[
              { value: "monograph", label: "Монографія" },
              { value: "article", label: "Стаття" },
              { value: "archive", label: "Архівне джерело" },
              { value: "dataset", label: "Датасет" },
              { value: "map", label: "Карта" },
              { value: "periodical", label: "Періодика" },
              { value: "manual", label: "Власні нотатки" },
            ]}
          />
        </Form.Item>
        <Form.Item label="Рік">
          <InputNumber value={year ?? undefined} onChange={(v) => setYear(v != null ? Number(v) : null)} />
        </Form.Item>
        <Form.Item label="URL">
          <Input value={url} onChange={(e) => setUrl(e.target.value)} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
