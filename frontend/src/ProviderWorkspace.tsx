import { choiceValue, errorMessage } from "./validation";
import Choice from "./Choice";
import { lazy, Suspense, useEffect, useId, useRef, useState } from "react";
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
import "./provider-dashboard.css";
const ProviderDashboard = lazy(() => import("./ProviderDashboard"));
const ProviderOmikuji = lazy(() => import("./ProviderOmikuji"));
const ProviderCircleInvites = lazy(() =>
  import("./Circles").then((module) => ({
    default: module.ProviderCircleInvites,
  })),
);
const ProviderDaytrip = lazy(() =>
  import("./Daytrip").then((module) => ({ default: module.ProviderDaytrip })),
);
function japanDateInput(value: string | null | undefined) {
  if (!value) return "";
  return new Date(new Date(value).getTime() + 9 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 16);
}
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
    nights: 0,
    price_yen: 5000,
    price_basis: "per_person",
    price_scope: "plan_only",
    price_note: "",
    tags: [],
    itinerary: [newStop()],
    status: "draft",
    version: 0,
    source_note: "",
    schedule_type: "on_request",
    starts_at: null,
    ends_at: null,
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
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const fieldId = useId();
  const dirty = JSON.stringify(value) !== JSON.stringify(initial);
  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function requestClose() {
    if (busy) return;
    if (dirty) setConfirmDiscard(true);
    else onClose();
  }
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
    if (busy) return;
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
      setError(errorMessage(e));
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
    (value.schedule_type !== "dated" ||
      (!!value.starts_at &&
        !!value.ends_at &&
        Date.parse(value.ends_at) >= Date.parse(value.starts_at))) &&
    value.itinerary.length > 0 &&
    value.itinerary.every(
      (item) => item.place.trim() && item.day <= value.nights + 1,
    );
  return (
    <Modal
      title={initial.id ? "プランを編集する" : "新しいプランをつくる"}
      onClose={requestClose}
      busy={busy}
      wide
    >
      <ErrorBox message={error} />
      <p className="small-label">{value.provider.name}</p>
      <div className="editor-heading">
        <h3>プランの基本情報</h3>
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
            placeholder="例：6人で森とカフェをめぐる日帰り"
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
        <h3 className="editor-section-title">開催日時</h3>
        <label className="field" htmlFor={`${fieldId}-schedule`}>
          日程の決め方
          <Choice
            id={`${fieldId}-schedule`}
            value={value.schedule_type || "on_request"}
            onChange={(event) =>
              setValue((current) => ({
                ...current,
                schedule_type: choiceValue(
                  event.target.value,
                  ["on_request", "dated"],
                  current.schedule_type || "on_request",
                ),
                starts_at:
                  event.target.value === "on_request"
                    ? null
                    : current.starts_at || null,
                ends_at:
                  event.target.value === "on_request"
                    ? null
                    : current.ends_at || null,
              }))
            }
          >
            <option value="on_request">日程は相談</option>
            <option value="dated">開催日時を指定する</option>
          </Choice>
        </label>
        {value.schedule_type === "dated" && (
          <>
            <div className="field-row">
              <label className="field">
                開催開始（日本時間）
                <input
                  type="datetime-local"
                  value={japanDateInput(value.starts_at)}
                  onChange={(event) =>
                    change(
                      "starts_at",
                      event.target.value
                        ? `${event.target.value}:00+09:00`
                        : null,
                    )
                  }
                />
              </label>
              <label className="field">
                開催終了（日本時間）
                <input
                  type="datetime-local"
                  value={japanDateInput(value.ends_at)}
                  onChange={(event) =>
                    change(
                      "ends_at",
                      event.target.value
                        ? `${event.target.value}:00+09:00`
                        : null,
                    )
                  }
                />
              </label>
            </div>
            <p className="muted">
              開催期間の表示です。空席や各日の出発を確約するものではありません。終了したプランは旅行者の探索に表示されません。
            </p>
          </>
        )}
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
          <label className="field" htmlFor={`${fieldId}-price-basis`}>
            費用の単位
            <Choice
              id={`${fieldId}-price-basis`}
              value={value.price_basis}
              onChange={(e) =>
                change(
                  "price_basis",
                  choiceValue(
                    e.target.value,
                    ["per_person", "party_total"],
                    value.price_basis,
                  ),
                )
              }
            >
              <option value="per_person">1人あたり</option>
              <option value="party_total">全員分</option>
            </Choice>
          </label>
        </div>
        <label className="field" htmlFor={`${fieldId}-price-scope`}>
          費用の範囲
          <Choice
            id={`${fieldId}-price-scope`}
            value={value.price_scope}
            onChange={(e) =>
              change(
                "price_scope",
                choiceValue(
                  e.target.value,
                  ["plan_only", "whole_trip"],
                  value.price_scope,
                ),
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
                      period: choiceValue(
                        e.target.value,
                        ["morning", "afternoon", "evening"],
                        item.period,
                      ),
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
      {confirmDiscard && (
        <Modal title="保存せずに閉じますか？" onClose={() => setConfirmDiscard(false)}>
          <p>入力した変更は失われます。保存済みのプランは変更されません。</p>
          <div className="dialog-actions">
            <button className="button secondary" onClick={() => setConfirmDiscard(false)}>
              編集を続ける
            </button>
            <button className="button danger" onClick={onClose}>
              変更を破棄して閉じる
            </button>
          </div>
        </Modal>
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
  const [tab, setTab] = useState<
    "overview" | "plans" | "consultations" | "circles" | "daytrip" | "omikuji"
  >("overview");
  const [plans, setPlans] = useState<ProviderPlan[]>([]);
  const [planFilter, setPlanFilter] = useState<ProviderPlan["status"] | "all">(
    "published",
  );
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [editing, setEditing] = useState<ProviderPlan | null>(null);
  const [selected, setSelected] = useState<Consultation | null>(null);
  const [messages, setMessages] = useState<MarketMessage[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);
  useEffect(() => () => activeRequest.current?.abort(), []);
  async function load() {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setBusy(true);
    setError("");
    try {
      const [planSets, threads] = await Promise.all([
        Promise.all(
          providers.map((p) =>
            api<{ items: ProviderPlan[] }>(
              `/provider-plans?provider_id=${encodeURIComponent(p.id)}&mine=true`,
              "GET",
              undefined,
              { signal: controller.signal },
            ),
          ),
        ),
        api<{ items: Consultation[] }>("/consultations", "GET", undefined, {
          signal: controller.signal,
        }),
      ]);
      if (controller.signal.aborted) return;
      setPlans(planSets.flatMap((r) => r.items));
      setConsultations(threads.items);
      setLoaded(true);
    } catch (e) {
      if (!controller.signal.aborted) setError(errorMessage(e));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  function changeTab(next: typeof tab) {
    activeRequest.current?.abort();
    setBusy(false);
    setError("");
    setSelected(null);
    setTab(next);
    if (!loaded && (next === "plans" || next === "consultations")) void load();
  }
  async function openThread(thread: Consultation) {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setError("");
    setBusy(true);
    setSelected(null);
    try {
      const [detail, history] = await Promise.all([
        api<Consultation>(`/consultations/${thread.id}`, "GET", undefined, {
          signal: controller.signal,
        }),
        api<{ items: MarketMessage[] }>(
          `/consultations/${thread.id}/messages`,
          "GET",
          undefined,
          { signal: controller.signal },
        ),
      ]);
      if (controller.signal.aborted) return;
      setSelected(detail);
      setMessages(history.items);
    } catch (e) {
      if (!controller.signal.aborted) setError(errorMessage(e));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <section className="provider-workspace">
      <div className="provider-console">
        <nav className="provider-workspace-nav" aria-label="事業者の業務">
          <p>事業者管理</p>
          {(
            [
              ["overview", "実績・地域", "home"],
              ["consultations", "相談", "people"],
              ["circles", "講の招待", "people"],
              ["plans", "プラン", "compass"],
              ["daytrip", "日帰り・特典", "calendar"],
              ["omikuji", "現地おみくじ", "compass"],
            ] as const
          ).map(([id, label, icon]) => (
            <button
              key={id}
              aria-current={tab === id ? "page" : undefined}
              className={tab === id ? "selected" : ""}
              onClick={() => changeTab(id)}
            >
              <Icon name={icon} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="provider-workspace-content">
          {tab !== "overview" && (
            <header className="provider-workspace-heading">
              <h1>
                {
                  {
                    overview: "実績の概要",
                    plans: "プラン管理",
                    consultations: "届いた相談",
                    circles: "講からの招待",
                    daytrip: "日帰りの運営",
                    omikuji: "現地おみくじの受付",
                  }[tab]
                }
              </h1>
              {tab !== "daytrip" && tab !== "omikuji" && (
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => void load()}
                >
                  <Icon name="refresh" />
                  更新
                </button>
              )}
            </header>
          )}
          <ErrorBox message={error} />
          {tab === "overview" ? (
            <Suspense
              fallback={
                <output className="page-load-status">
                  実績を読み込んでいます…
                </output>
              }
            >
              <ProviderDashboard
                key={user.id}
                providers={providers}
                onNavigate={changeTab}
              />
            </Suspense>
          ) : tab === "omikuji" ? (
            <Suspense fallback={<output className="page-load-status">受付をひらいています…</output>}>
              <ProviderOmikuji key={user.id} />
            </Suspense>
          ) : tab === "daytrip" ? (
            <Suspense
              fallback={
                <output className="page-load-status">
                  日帰りの開催をひらいています…
                </output>
              }
            >
              <ProviderDaytrip key={user.id} user={user} />
            </Suspense>
          ) : tab === "circles" ? (
            <Suspense
              fallback={
                <output className="page-load-status">
                  講への招待をひらいています…
                </output>
              }
            >
              <ProviderCircleInvites key={user.id} user={user} />
            </Suspense>
          ) : tab === "plans" ? (
            <>
              <div className="section-title">
                <h2>プランの管理</h2>
                <button
                  className="button primary"
                  disabled={!providers.length}
                  onClick={() => setEditing(blankPlan(providers[0]))}
                >
                  <Icon name="plus" />
                  プランをつくる
                </button>
              </div>
              <div
                className="provider-plan-filters"
                role="group"
                aria-label="プランの公開状態"
              >
                {(
                  [
                    ["published", "公開中"],
                    ["draft", "下書き"],
                    ["archived", "公開終了"],
                    ["all", "すべて"],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    aria-pressed={planFilter === value}
                    className={planFilter === value ? "selected" : ""}
                    onClick={() => setPlanFilter(value)}
                  >
                    {label}
                    <span>
                      {value === "all"
                        ? plans.length
                        : plans.filter((plan) => plan.status === value).length}
                    </span>
                  </button>
                ))}
              </div>
              <div className="provider-plan-list">
                {plans
                  .filter(
                    (plan) =>
                      planFilter === "all" || plan.status === planFilter,
                  )
                  .map((p) => (
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
              {!busy &&
                plans.length > 0 &&
                !plans.some(
                  (plan) => planFilter === "all" || plan.status === planFilter,
                ) && (
                  <Empty title="この公開状態のプランはありません">
                    <button
                      className="button secondary"
                      onClick={() => setPlanFilter("all")}
                    >
                      すべてのプランを見る
                    </button>
                  </Empty>
                )}
              {!busy && !plans.length && (
                <Empty title="登録したプランはありません">
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
                <Empty title="相談はありません">
                  <p>
                    公開したプランを選んだ旅行者から、ここに相談が届きます。
                  </p>
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
                          {c.selection.shared_conditions.date_start ||
                            "希望日未定"}
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
        </div>
      </div>
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
          title="旅行者との相談"
          onClose={() => setSelected(null)}
          wide
          variant="conversation"
        >
          <Conversation
            context={
              <div className="consultation-context">
                <h3>{selected.selection.plan.title}</h3>
                <RequirementsSummary
                  value={selected.selection.shared_conditions}
                />
                {selected.selection.share_note && (
                  <p>{selected.selection.share_note}</p>
                )}
              </div>
            }
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
