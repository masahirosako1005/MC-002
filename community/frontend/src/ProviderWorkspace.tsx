import Choice from "./Choice";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Tag, User } from "./types";
import type {
  Consultation,
  ItineraryItem,
  MarketMessage,
  Provider,
  ProviderPlan,
} from "./marketplace-types";
import {
  Conversation,
  periods,
  PlanCard,
  PlanDetail,
  RequirementsSummary,
} from "./marketplace-ui";
import { Empty, ErrorBox, Icon, Modal, TagPicker } from "./ui";
import "./marketplace.css";
const newStop = (): ItineraryItem => ({
  day: 1,
  period: "afternoon",
  place: "",
  description: "",
  travel_minutes: null,
});
function blankPlan(provider: Provider): ProviderPlan {
  return {
    id: "",
    provider,
    title: "",
    summary: "",
    area: provider.area,
    min_people: 1,
    max_people: 6,
    nights: 2,
    price_yen: 20000,
    price_basis: "per_person",
    price_scope: "plan_only",
    price_note: "",
    tags: [],
    itinerary: [newStop()],
    status: "draft",
    version: 0,
    source_note: "",
  };
}
function PlanEditor({
  initial,
  tags,
  onClose,
  onSaved,
}: {
  initial: ProviderPlan;
  tags: Tag[];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(false);
  function change<K extends keyof ProviderPlan>(key: K, next: ProviderPlan[K]) {
    setValue((v) => ({ ...v, [key]: next }));
  }
  function stop(index: number, next: Partial<ItineraryItem>) {
    change(
      "itinerary",
      value.itinerary.map((item, i) =>
        i === index ? { ...item, ...next } : item,
      ),
    );
  }
  function move(index: number, direction: number) {
    const items = [...value.itinerary];
    const target = index + direction;
    if (target < 0 || target >= items.length) return;
    [items[index], items[target]] = [items[target], items[index]];
    change("itinerary", items);
  }
  async function save(status: ProviderPlan["status"]) {
    setBusy(true);
    setError("");
    try {
      const { id, provider, source_note, ...body } = value;
      void source_note;
      const response = await api<ProviderPlan>(
        id ? `/provider-plans/${id}` : `/providers/${provider.id}/plans`,
        id ? "PATCH" : "POST",
        { ...body, status },
      );
      setValue(response);
      await onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const valid =
    value.title.trim() &&
    value.area.trim() &&
    value.price_note.trim() &&
    value.min_people >= 1 &&
    value.max_people >= value.min_people &&
    value.price_yen > 0 &&
    value.itinerary.length > 0 &&
    value.itinerary.every(
      (item) => item.place.trim() && item.day <= value.nights + 1,
    );
  return (
    <Modal
      title={initial.id ? "プランを編集する" : "新しいプランをつくる"}
      onClose={onClose}
      busy={busy}
      wide
    >
      <ErrorBox message={error} />
      <p className="small-label">{value.provider.name}</p>
      <div className="editor-heading">
        <h3>誰と、どんな旅を楽しむ？</h3>
        <button
          className="text-button"
          onClick={() => setPreview(true)}
          disabled={busy}
        >
          旅行者の表示を見る
          <Icon name="arrow" />
        </button>
      </div>
      <fieldset className="editor-fields" disabled={busy}>
        <label className="field">
          プランの名前
          <input
            value={value.title}
            onChange={(e) => change("title", e.target.value)}
            maxLength={120}
            placeholder="例：6人で森とカフェをめぐる2泊3日"
          />
        </label>
        <label className="field">
          紹介
          <textarea
            value={value.summary}
            onChange={(e) => change("summary", e.target.value)}
            rows={3}
            maxLength={1000}
          />
        </label>
        <label className="field">
          地域
          <input
            value={value.area}
            onChange={(e) => change("area", e.target.value)}
            maxLength={120}
          />
        </label>
        <h3 className="editor-section-title">人数・泊数・費用</h3>
        <div className="numeric-grid">
          <label className="field">
            最少人数
            <input
              type="number"
              min={1}
              max={500}
              value={value.min_people}
              onChange={(e) => change("min_people", Number(e.target.value))}
            />
          </label>
          <label className="field">
            最大人数
            <input
              type="number"
              min={1}
              max={500}
              value={value.max_people}
              onChange={(e) => change("max_people", Number(e.target.value))}
            />
          </label>
          <label className="field">
            泊数
            <input
              type="number"
              min={0}
              max={30}
              value={value.nights}
              onChange={(e) => change("nights", Number(e.target.value))}
            />
          </label>
        </div>
        <div className="field-row">
          <label className="field">
            概算費用（円）
            <input
              type="number"
              min={1}
              max={100000000}
              value={value.price_yen}
              onChange={(e) => change("price_yen", Number(e.target.value))}
            />
          </label>
          <label className="field">
            費用の単位
            <Choice
              value={value.price_basis}
              onChange={(e) =>
                change(
                  "price_basis",
                  e.target.value as ProviderPlan["price_basis"],
                )
              }
            >
              <option value="per_person">1人あたり</option>
              <option value="party_total">全員分</option>
            </Choice>
          </label>
        </div>
        <label className="field">
          費用の範囲
          <Choice
            value={value.price_scope}
            onChange={(e) =>
              change(
                "price_scope",
                e.target.value as ProviderPlan["price_scope"],
              )
            }
          >
            <option value="plan_only">プラン部分</option>
            <option value="whole_trip">旅行全体</option>
          </Choice>
        </label>
        <label className="field">
          含むもの・含まないもの
          <textarea
            value={value.price_note}
            onChange={(e) => change("price_note", e.target.value)}
            maxLength={400}
            rows={2}
            placeholder="例：宿泊・体験の概算。出発地からの交通費は含みません。"
          />
        </label>
        <TagPicker
          tags={tags}
          value={value.tags}
          onChange={(v) => change("tags", v)}
          label="このプランで楽しめること"
        />
        <h3 className="editor-section-title">日別の行程</h3>
        <p className="muted">
          公開には、すべての日に訪問先が必要です。移動時間が不明なら空欄にできます。
        </p>
        {value.itinerary.map((item, i) => (
          <div className="stop-editor" key={i}>
            <div className="stop-editor-head">
              <strong>訪問先 {i + 1}</strong>
              <div>
                <button
                  type="button"
                  className="text-button"
                  disabled={i === 0}
                  onClick={() => move(i, -1)}
                  aria-label={`訪問先${i + 1}を上へ`}
                >
                  上へ
                </button>
                <button
                  type="button"
                  className="text-button"
                  disabled={i === value.itinerary.length - 1}
                  onClick={() => move(i, 1)}
                  aria-label={`訪問先${i + 1}を下へ`}
                >
                  下へ
                </button>
                <button
                  type="button"
                  className="text-button danger"
                  onClick={() =>
                    change(
                      "itinerary",
                      value.itinerary.filter((_, index) => index !== i),
                    )
                  }
                  aria-label={`訪問先${i + 1}を削除`}
                >
                  削除
                </button>
              </div>
            </div>
            <div className="field-row">
              <label className="field">
                何日目
                <input
                  type="number"
                  min={1}
                  max={value.nights + 1}
                  value={item.day}
                  onChange={(e) => stop(i, { day: Number(e.target.value) })}
                />
              </label>
              <label className="field">
                時間帯
                <Choice
                  value={item.period}
                  onChange={(e) =>
                    stop(i, {
                      period: e.target.value as ItineraryItem["period"],
                    })
                  }
                >
                  {Object.entries(periods).map(([id, label]) => (
                    <option value={id} key={id}>
                      {label}
                    </option>
                  ))}
                </Choice>
              </label>
            </div>
            <label className="field">
              店・場所の名前
              <input
                value={item.place}
                onChange={(e) => stop(i, { place: e.target.value })}
                maxLength={120}
              />
            </label>
            <label className="field">
              ここでできること
              <textarea
                value={item.description}
                onChange={(e) => stop(i, { description: e.target.value })}
                maxLength={400}
                rows={2}
              />
            </label>
            <label className="field">
              前の場所からの移動目安（分・任意）
              <input
                type="number"
                min={0}
                max={1440}
                value={item.travel_minutes ?? ""}
                onChange={(e) =>
                  stop(i, {
                    travel_minutes:
                      e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </label>
          </div>
        ))}
        <button
          className="button secondary"
          disabled={value.itinerary.length >= 60}
          onClick={() => change("itinerary", [...value.itinerary, newStop()])}
        >
          <Icon name="plus" />
          訪問先を追加
        </button>
      </fieldset>
      <div className="dialog-actions">
        <button
          className="button secondary"
          disabled={busy || !valid}
          onClick={() => void save("draft")}
        >
          下書きに保存
        </button>
        <button
          className="button primary"
          disabled={busy || !valid}
          onClick={() => void save("published")}
        >
          {busy ? "保存中…" : "この内容で公開する"}
        </button>
      </div>
      {preview && (
        <PlanDetail
          plan={value}
          tags={tags}
          onClose={() => setPreview(false)}
        />
      )}
    </Modal>
  );
}
export default function ProviderWorkspace({
  providers,
  tags,
  user,
}: {
  providers: Provider[];
  tags: Tag[];
  user: User;
}) {
  const [tab, setTab] = useState<"plans" | "consultations">("plans");
  const [plans, setPlans] = useState<ProviderPlan[]>([]);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [editing, setEditing] = useState<ProviderPlan | null>(null);
  const [selected, setSelected] = useState<Consultation | null>(null);
  const [messages, setMessages] = useState<MarketMessage[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    setBusy(true);
    setError("");
    try {
      const [planSets, threads] = await Promise.all([
        Promise.all(
          providers.map((p) =>
            api<{ items: ProviderPlan[] }>(
              `/provider-plans?provider_id=${encodeURIComponent(p.id)}&mine=true`,
            ),
          ),
        ),
        api<{ items: Consultation[] }>("/consultations"),
      ]);
      setPlans(planSets.flatMap((r) => r.items));
      setConsultations(threads.items);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void load();
  }, [user.id]);
  async function openThread(thread: Consultation) {
    setError("");
    setBusy(true);
    setSelected(null);
    try {
      const [detail, history] = await Promise.all([
        api<Consultation>(`/consultations/${thread.id}`),
        api<{ items: MarketMessage[] }>(`/consultations/${thread.id}/messages`),
      ]);
      setSelected(detail);
      setMessages(history.items);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="provider-workspace">
      <div className="page-heading">
        <p className="eyebrow">{providers.map((p) => p.name).join("・")}</p>
        <h1>旅のプランと相談</h1>
      </div>
      <div className="market-tabs">
        <button
          aria-pressed={tab === "plans"}
          className={tab === "plans" ? "selected" : ""}
          onClick={() => setTab("plans")}
        >
          自社のプラン
        </button>
        <button
          aria-pressed={tab === "consultations"}
          className={tab === "consultations" ? "selected" : ""}
          onClick={() => setTab("consultations")}
        >
          届いた相談
        </button>
        <button
          className="text-button"
          disabled={busy}
          onClick={() => void load()}
        >
          <Icon name="refresh" />
          更新
        </button>
      </div>
      <ErrorBox message={error} />
      {tab === "plans" ? (
        <>
          <div className="section-title">
            <h2>公開・下書き</h2>
            <button
              className="button primary"
              disabled={!providers.length}
              onClick={() => setEditing(blankPlan(providers[0]))}
            >
              <Icon name="plus" />
              プランをつくる
            </button>
          </div>
          <div className="provider-plan-list">
            {plans.map((p) => (
              <div key={p.id}>
                <span
                  className={`plan-state ${p.status === "published" ? "published" : ""}`}
                >
                  {p.status === "published"
                    ? "公開中"
                    : p.status === "draft"
                      ? "下書き"
                      : "公開終了"}
                </span>
                <PlanCard
                  plan={p}
                  tags={tags}
                  onOpen={() => setEditing(p)}
                  actionLabel="プランを編集する"
                />
              </div>
            ))}
          </div>
          {!busy && !plans.length && (
            <Empty title="最初のプランをつくりましょう">
              <p>地域の場所やお店を、日別の行程にまとめられます。</p>
            </Empty>
          )}
        </>
      ) : (
        <>
          <p className="muted">
            旅行者がプランを選び、共有を確認した相談だけが届きます。
          </p>
          {consultations.length === 0 ? (
            <Empty title="相談が届くのを待っています">
              <p>公開したプランを選んだ旅行者から、ここに相談が届きます。</p>
            </Empty>
          ) : (
            <div className="consultation-list">
              {consultations.map((c) => (
                <button
                  key={c.id}
                  className="consultation-row"
                  data-consultation-id={c.id}
                  disabled={busy}
                  onClick={() => void openThread(c)}
                >
                  <span className="round-icon">
                    <Icon name="people" />
                  </span>
                  <span>
                    <strong>{c.selection.plan.title}</strong>
                    <small>
                      {c.selection.shared_conditions.planned_people}人 ·{" "}
                      {c.selection.shared_conditions.nights === 0
                        ? "日帰り"
                        : `${c.selection.shared_conditions.nights}泊${c.selection.shared_conditions.nights + 1}日`}{" "}
                      ·{" "}
                      {c.selection.shared_conditions.date_start || "希望日未定"}
                    </small>
                    {c.selection.share_note.trim() && (
                      <small className="consultation-preview">
                        {c.selection.share_note
                          .replace(/\s+/g, " ")
                          .trim()
                          .slice(0, 70)}
                        {c.selection.share_note.replace(/\s+/g, " ").trim()
                          .length > 70
                          ? "…"
                          : ""}
                      </small>
                    )}
                    <span className="thread-status">
                      {c.status === "open" ? "相談中" : "終了"}
                    </span>
                  </span>
                  <Icon name="arrow" />
                </button>
              ))}
            </div>
          )}
        </>
      )}
      {editing && (
        <PlanEditor
          initial={editing}
          tags={tags}
          onClose={() => setEditing(null)}
          onSaved={load}
        />
      )}{" "}
      {selected && (
        <Modal
          title={selected.selection.plan.title}
          onClose={() => setSelected(null)}
          wide
        >
          <div className="consultation-context">
            <span className="small-label">{selected.selection.plan.title}</span>
            <RequirementsSummary value={selected.selection.shared_conditions} />
            {selected.selection.share_note && (
              <p>{selected.selection.share_note}</p>
            )}
          </div>
          <Conversation
            endpoint={`/consultations/${selected.id}/messages`}
            messages={messages}
            user={user}
            closed={selected.status === "closed"}
            label="旅行者との相談"
            onSent={async () => {
              const result = await api<{ items: MarketMessage[] }>(
                `/consultations/${selected.id}/messages`,
              );
              setMessages(result.items);
            }}
          />
        </Modal>
      )}
    </section>
  );
}
