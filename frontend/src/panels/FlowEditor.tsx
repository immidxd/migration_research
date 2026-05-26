import React, { useState } from "react";
import { Drawer, Form, Input, InputNumber, Radio, Select, Button, Modal, message } from "antd";

import { useCreateFlow, useCreateSource } from "../api/flows";
import { SourcePicker, TerritoryPicker } from "./pickers";
import { useTemporalLabels } from "../api/temporal";

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


export const FlowEditor: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const [origin, setOrigin] = useState<number | null>(null);
  const [destination, setDestination] = useState<number | null>(null);
  const [labelId, setLabelId] = useState<number | null>(null);

  const [vector, setVector] = useState<string>("transatlantic");
  const [transport, setTransport] = useState<string>("sea");
  const [originPrec, setOriginPrec] = useState<string>("gubernia");
  const [destPrec, setDestPrec] = useState<string>("country");

  const [countMethod, setCountMethod] = useState<"exact" | "estimate" | "range" | "unknown">("estimate");
  const [count, setCount] = useState<number | null>(null);
  const [countLower, setCountLower] = useState<number | null>(null);
  const [countUpper, setCountUpper] = useState<number | null>(null);

  const [notes, setNotes] = useState<string>("");
  const [sourceIds, setSourceIds] = useState<number[]>([]);
  const [newSourceOpen, setNewSourceOpen] = useState(false);

  const labelsQ = useTemporalLabels();
  const createFlow = useCreateFlow();

  const reset = () => {
    setOrigin(null); setDestination(null); setLabelId(null);
    setVector("transatlantic"); setTransport("sea");
    setOriginPrec("gubernia"); setDestPrec("country");
    setCountMethod("estimate"); setCount(null); setCountLower(null); setCountUpper(null);
    setNotes(""); setSourceIds([]);
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
    const sel = labelsQ.data?.find((l) => l.id === labelId);
    try {
      await createFlow.mutateAsync({
        origin_territory_id: origin,
        destination_territory_id: destination,
        temporal_label_id: labelId,
        date_from: sel ? `${sel.year_from}-01-01` : null,
        date_to: sel ? `${sel.year_to}-12-31` : null,
        date_precision: sel ? (sel.kind === "year" ? "year" : "period") : "unknown",
        count: countMethod === "exact" || countMethod === "estimate" ? count : null,
        count_lower: countMethod === "range" ? countLower : null,
        count_upper: countMethod === "range" ? countUpper : null,
        count_method: countMethod,
        vector, transport_mode: transport,
        origin_precision: originPrec,
        destination_precision: destPrec,
        notes: notes || null,
        sources: sourceIds.map((id) => ({ source_id: id })),
      });
      message.success(
        sourceIds.length
          ? "Потік додано"
          : "Потік додано як provisional (без джерела)"
      );
      reset();
      onClose();
    } catch (e: any) {
      message.error(e?.response?.data?.detail?.[0]?.msg ?? "Помилка збереження");
    }
  };

  return (
    <>
      <Drawer
        title="Додати міграційний потік"
        open={open}
        onClose={onClose}
        width={520}
        extra={
          <Button type="primary" onClick={submit} loading={createFlow.isPending}>
            Зберегти
          </Button>
        }
      >
        <Form layout="vertical">
          <Form.Item label="Походження" required>
            <TerritoryPicker
              value={origin}
              onChange={(id) => setOrigin(id)}
              placeholder="звідки…"
            />
          </Form.Item>
          <Form.Item label="Точність походження" required>
            <Select value={originPrec} onChange={setOriginPrec} options={PRECISION_OPTS} />
          </Form.Item>

          <Form.Item label="Пункт прибуття" required>
            <TerritoryPicker
              value={destination}
              onChange={(id) => setDestination(id)}
              placeholder="куди…"
            />
          </Form.Item>
          <Form.Item label="Точність прибуття">
            <Select value={destPrec} onChange={setDestPrec} options={PRECISION_OPTS} />
          </Form.Item>

          <Form.Item label="Часова мітка (період / епоха / декада / рік)">
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
            />
          </Form.Item>

          <Form.Item label="Вектор" required>
            <Select value={vector} onChange={setVector} options={VECTOR_OPTS} />
          </Form.Item>
          <Form.Item label="Транспорт">
            <Select value={transport} onChange={setTransport} options={TRANSPORT_OPTS} />
          </Form.Item>

          <Form.Item label="Як відома кількість" required>
            <Radio.Group value={countMethod} onChange={(e) => setCountMethod(e.target.value)}>
              <Radio.Button value="exact">точно</Radio.Button>
              <Radio.Button value="estimate">оцінка</Radio.Button>
              <Radio.Button value="range">діапазон</Radio.Button>
              <Radio.Button value="unknown">невідомо</Radio.Button>
            </Radio.Group>
          </Form.Item>

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
