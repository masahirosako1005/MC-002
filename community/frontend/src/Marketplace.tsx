import Choice from "./Choice";
import { lazy, Suspense, useEffect, useState } from "react";
import { api } from "./api";
import type { Community, Group, Tag, User } from "./types";
import type {
  BudgetBasis,
  BudgetScope,
  ConditionDraft,
  Consultation,
  MarketMessage,
  Party,
  ProviderPlan,
  RecommendationRun,
  Requirements,
  SelectionPreview,
} from "./marketplace-types";
import {
  Conversation,
  PlanCard,
  PlanDetail,
  RequirementsSummary,
  useRequestKey,
} from "./marketplace-ui";
import { Empty, ErrorBox, Icon, Modal, TagPicker } from "./ui";
import "./marketplace.css";
const PlanDiscovery = lazy(() => import("./PlanDiscovery"));
export const emptyRequirements: Requirements = {
  planned_people: 6,
  nights: 2,
  budget_yen: null,
  budget_basis: null,
  budget_scope: null,
  date_start: null,
  interests: [],
  departure_label: "",
  version: 0,
};
export function RequirementEditor({
  initial,
  tags,
  draft,
  busy,
  onSave,
  unknownFields = [],
  requireBudget = false,
}: {
  initial: Requirements | null;
  tags: Tag[];
  draft: ConditionDraft | null;
  busy: boolean;
  onSave: (v: Requirements) => Promise<void>;
  unknownFields?: string[];
  requireBudget?: boolean;
}) {
  const [value, setValue] = useState<Requirements>(
    initial || emptyRequirements,
  );
  const [missing, setMissing] = useState(unknownFields);
  const [amount, setAmount] = useState(
    unknownFields.includes("budget_yen")
      ? ""
      : initial?.budget_yen?.toString() || "",
  );
  const [basis, setBasis] = useState<BudgetBasis | "">(
    unknownFields.includes("budget_basis")
      ? ""
      : initial?.budget_basis || "per_person",
  );
  const [scope, setScope] = useState<BudgetScope | "">(
    unknownFields.includes("budget_scope")
      ? ""
      : initial?.budget_scope || "plan_only",
  );
  function patch(v: Partial<Requirements>) {
    setValue((current) => ({ ...current, ...v }));
  }
  return (
    <div className="requirement-editor">
      {draft && (
        <div className="condition-draft">
          <div className="section-kicker">
            <Icon name="leaf" />
            会話から整理した候補
          </div>
          {draft.candidates.map((item, index) => (
            <div className="draft-values" key={item.message_id}>
              <strong>会話 {index + 1} の数値候補</strong>
              <div className="tag-options">
                {item.candidates.planned_people?.map((n) => (
                  <button
                    key={`p${n}`}
                    className="chip"
                    disabled={busy}
                    onClick={() => patch({ planned_people: n })}
                  >
                    人数に {n}人を使う
                  </button>
                ))}
                {item.candidates.nights?.map((n) => (
                  <button
                    key={`n${n}`}
                    className="chip"
                    disabled={busy}
                    onClick={() => patch({ nights: n })}
                  >
                    泊数に {n}泊を使う
                  </button>
                ))}
                {item.candidates.budget_yen?.map((n) => (
                  <button
                    key={`b${n}`}
                    className="chip"
                    disabled={busy}
                    onClick={() => setAmount(String(n))}
                  >
                    予算に {n.toLocaleString()}円を使う
                  </button>
                ))}
              </div>
            </div>
          ))}
          <p className="muted">{draft.warning}</p>
          <p className="muted">
            会話中の数値から見つけた候補です。内容を確かめてから条件へ反映してください。
          </p>
          <p className="muted">
            予算の単位と範囲は、下の項目で確認してください。
          </p>
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (
            missing.includes("planned_people") ||
            missing.includes("nights") ||
            (requireBudget && (!amount || !basis || !scope))
          )
            return;
          void onSave({
            ...value,
            budget_yen: amount ? Number(amount) : null,
            budget_basis: amount ? basis || null : null,
            budget_scope: amount ? scope || null : null,
          });
        }}
      >
        <fieldset className="editor-fields" disabled={busy}>
          <div className="field-row">
            <label className="field">
              予定している旅行人数
              <input
                type="number"
                min={1}
                max={500}
                required
                value={
                  missing.includes("planned_people") ? "" : value.planned_people
                }
                onChange={(e) => {
                  patch({ planned_people: Number(e.target.value) });
                  setMissing((items) =>
                    e.target.value === ""
                      ? [
                          ...items.filter((item) => item !== "planned_people"),
                          "planned_people",
                        ]
                      : items.filter((item) => item !== "planned_people"),
                  );
                }}
              />
            </label>
            <label className="field">
              泊数
              <input
                type="number"
                min={0}
                max={30}
                required
                value={missing.includes("nights") ? "" : value.nights}
                onChange={(e) => {
                  patch({ nights: Number(e.target.value) });
                  setMissing((items) =>
                    e.target.value === ""
                      ? [...items.filter((item) => item !== "nights"), "nights"]
                      : items.filter((item) => item !== "nights"),
                  );
                }}
              />
            </label>
          </div>
          <p className="muted">
            {missing.includes("nights")
              ? "泊数を確認してください。"
              : value.nights === 0
                ? "日帰りの予定。"
                : `${value.nights}泊${value.nights + 1}日の予定。`}
            人数を入力しても、誰かが自動で参加することはありません。
          </p>
          <div className="field-row">
            <label className="field">
              {requireBudget
                ? "予算の目安（円・必須）"
                : "予算の目安（円・任意）"}
              <input
                type="number"
                min={1}
                max={100000000}
                required={requireBudget}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="例：30000"
              />
            </label>
            <label className="field">
              予算の単位
              <Choice
                value={basis}
                onChange={(e) => setBasis(e.target.value as BudgetBasis)}
                disabled={!amount || busy}
              >
                <option value="">単位を選ぶ</option>
                <option value="per_person">1人あたり</option>
                <option value="party_total">全員分</option>
              </Choice>
            </label>
          </div>
          <label className="field">
            どこまで含む予算？
            <Choice
              value={scope}
              onChange={(e) => setScope(e.target.value as BudgetScope)}
              disabled={!amount || busy}
            >
              <option value="">費用の範囲を選ぶ</option>
              <option value="plan_only">選ぶプラン部分</option>
              <option value="whole_trip">出発地からの旅行全体</option>
            </Choice>
          </label>
          <div className="field-row">
            <label className="field">
              出発日の希望 <span className="optional">任意</span>
              <input
                type="date"
                value={value.date_start || ""}
                onChange={(e) => patch({ date_start: e.target.value || null })}
              />
            </label>
            <label className="field">
              出発地 <span className="optional">任意</span>
              <input
                value={value.departure_label}
                onChange={(e) => patch({ departure_label: e.target.value })}
                maxLength={120}
                placeholder="例：東京駅"
              />
            </label>
          </div>
          <TagPicker
            tags={tags}
            value={value.interests}
            onChange={(interests) => patch({ interests })}
            label="この旅で楽しみたいこと"
          />
          <button
            type="submit"
            className="button primary full"
            disabled={
              missing.includes("planned_people") ||
              missing.includes("nights") ||
              (requireBudget && (!amount || !basis || !scope))
            }
          >
            {busy ? "保存中…" : "この旅行条件で確定する"}
            <Icon name="check" />
          </button>
        </fieldset>
      </form>
    </div>
  );
}
export default function Marketplace({
  community,
  groups,
  tags,
  user,
  onOpenCircle,
}: {
  community: Community | null;
  groups: Group[];
  tags: Tag[];
  user: User;
  onOpenCircle: (id: string) => void;
}) {
  const [parties, setParties] = useState<Party[]>([]);
  const [party, setParty] = useState<Party | null>(null);
  const [plans, setPlans] = useState<ProviderPlan[]>([]);
  const [messages, setMessages] = useState<MarketMessage[]>([]);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [tab, setTab] = useState<
    "conversation" | "conditions" | "plans" | "consultation"
  >("plans");
  const [source, setSource] = useState<"recommended" | "catalog">("catalog");
  const [run, setRun] = useState<RecommendationRun | null>(null);
  const [draft, setDraft] = useState<ConditionDraft | null>(null);
  const [detail, setDetail] = useState<ProviderPlan | null>(null);
  const [preview, setPreview] = useState<SelectionPreview | null>(null);
  const [chosen, setChosen] = useState<ProviderPlan | null>(null);
  const [shareNote, setShareNote] = useState("");
  const [shareConfirmed, setShareConfirmed] = useState(false);
  const [thread, setThread] = useState<Consultation | null>(null);
  const [threadMessages, setThreadMessages] = useState<MarketMessage[]>([]);
  const [creating, setCreating] = useState(false);
  const [closing, setClosing] = useState(false);
  const [title, setTitle] = useState("");
  const [groupId, setGroupId] = useState("");
  const [memberIds, setMemberIds] = useState<string[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const requestKey = useRequestKey();
  async function load() {
    setBusy("load");
    setError("");
    try {
      const [list, catalog, threads] = await Promise.all([
        api<{ items: Party[] }>("/travel-parties"),
        api<{ items: ProviderPlan[] }>("/provider-plans"),
        api<{ items: Consultation[] }>("/consultations"),
      ]);
      setParties(list.items);
      setPlans(catalog.items);
      setConsultations(threads.items);
      if (party) {
        const latest = await api<Party>(`/travel-parties/${party.id}`);
        setParty(latest);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  useEffect(() => {
    void load();
  }, [user.id]);
  async function loadParty(id: string) {
    setBusy("party");
    setError("");
    try {
      const [item, history] = await Promise.all([
        api<Party>(`/travel-parties/${id}`),
        api<{ items: MarketMessage[] }>(`/travel-parties/${id}/messages`),
      ]);
      setParty(item);
      setMessages(history.items);
      setRun(null);
      setDraft(null);
      setThread(null);
      setNotice("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function refreshMessages() {
    if (!party) return;
    const r = await api<{ items: MarketMessage[] }>(
      `/travel-parties/${party.id}/messages`,
    );
    setMessages(r.items);
  }
  async function create() {
    if (!community) return;
    setBusy("create");
    setError("");
    try {
      const item = await api<Party>(
        `/communities/${community.id}/travel-parties`,
        "POST",
        { title, ko_group_id: groupId || null, member_ids: memberIds },
      );
      setParties((v) => [item, ...v]);
      setParty(item);
      setMessages([]);
      setRun(null);
      setDraft(null);
      setCreating(false);
      setTab("conversation");
      setTitle("");
      setGroupId("");
      setMemberIds([]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function extract() {
    if (!party) return;
    setBusy("extract");
    setError("");
    try {
      const result = await api<ConditionDraft>(
        `/travel-parties/${party.id}/condition-drafts`,
        "POST",
        { message_ids: messages.slice(-50).map((m) => m.id) },
      );
      setDraft(result);
      setTab("conditions");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function saveRequirements(value: Requirements) {
    if (!party) return;
    setBusy("requirements");
    setError("");
    setNotice("");
    try {
      const updated = await api<Party>(
        `/travel-parties/${party.id}/requirements`,
        "PUT",
        value,
      );
      setParty(updated);
      setRun(null);
      setDraft(null);
      setNotice("旅行条件を保存しました。この条件に合う候補を探せます。");
      setTab("plans");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function recommend() {
    if (!party?.requirements) return;
    setBusy("recommend");
    setError("");
    try {
      const result = await api<RecommendationRun>(
        `/travel-parties/${party.id}/recommendations`,
        "POST",
        { version: party.requirements.version },
      );
      setRun(result);
      setSource("recommended");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function prepare(plan: ProviderPlan) {
    if (!party?.requirements) {
      setDetail(null);
      setTab("conditions");
      setNotice("先に旅行条件を確認してください。");
      return;
    }
    setBusy("preview");
    setError("");
    try {
      const result = await api<SelectionPreview>(
        `/travel-parties/${party.id}/selection-preview`,
        "POST",
        {
          plan_id: plan.id,
          plan_version: plan.version,
          requirements_version: party.requirements.version,
        },
      );
      setPreview(result);
      setChosen(plan);
      setDetail(null);
      setShareNote("");
      setShareConfirmed(false);
    } catch (e) {
      setError((e as Error).message);
      setDetail(null);
    } finally {
      setBusy("");
    }
  }
  async function select() {
    if (!party?.requirements || !chosen) return;
    setBusy("selection");
    setError("");
    const payload = {
      plan_id: chosen.id,
      plan_version: chosen.version,
      requirements_version: party.requirements.version,
      share_note: shareNote,
      sharing_confirmed: true,
    };
    try {
      const selected = await api<Consultation>(
        `/travel-parties/${party.id}/selections`,
        "POST",
        {
          ...payload,
          client_request_id: requestKey({ party_id: party.id, ...payload }),
        },
      );
      const threads = await api<{ items: Consultation[] }>("/consultations");
      setConsultations(threads.items);
      setParty({ ...party, consultation_id: selected.id });
      requestKey.reset();
      setPreview(null);
      setChosen(null);
      setTab("consultation");
      setNotice("相談を送りました。予約はまだ確定していません。");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function closeParty() {
    if (!party) return;
    setBusy("close");
    setError("");
    try {
      const latest = await api<Party>(
        `/travel-parties/${party.id}/close`,
        "POST",
        {},
      );
      setParty(latest);
      setParties((items) =>
        items.map((p) => (p.id === latest.id ? latest : p)),
      );
      setClosing(false);
      setNotice("計画を閉じました。新しい相談や条件の変更はできません。");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function openThread(value: Consultation) {
    setBusy("thread");
    setError("");
    try {
      const [latest, history] = await Promise.all([
        api<Consultation>(`/consultations/${value.id}`),
        api<{ items: MarketMessage[] }>(`/consultations/${value.id}/messages`),
      ]);
      setThread(latest);
      setThreadMessages(history.items);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  const myGroups = groups.filter((g) => g.community_id === community?.id);
  const creatingGroup = myGroups.find((g) => g.id === groupId);
  const isRep =
    party?.status === "open" &&
    (party.can_manage || party.representative_id === user.id);
  const currentThreads = consultations.filter(
    (c) => c.id === party?.consultation_id,
  );
  const candidates =
    source === "recommended"
      ? run?.items.filter((c) => c.eligible).map((c) => c.plan) || []
      : plans;
  return (
    <section className="marketplace">
      <div className="page-heading">
        <h1>旅を見つける</h1>
      </div>
      <button
        className="travel-search-pill"
        disabled={!community || !!busy}
        onClick={() => {
          if (party) setTab("conditions");
          else setCreating(true);
        }}
      >
        <Icon name="compass" />
        <span>
          <strong>
            {party?.requirements
              ? `${party.requirements.planned_people}人 · ${party.requirements.nights === 0 ? "日帰り" : `${party.requirements.nights}泊${party.requirements.nights + 1}日`}`
              : "行きたい旅を探す"}
          </strong>
          <small>
            {party?.requirements?.budget_yen
              ? `${party.requirements.budget_yen.toLocaleString()}円 / ${party.requirements.budget_basis === "per_person" ? "1人" : "全員"} · 条件を見直す`
              : "人数・泊数・予算を設定"}
          </small>
        </span>
        <Icon name="arrow" />
      </button>
      <div className="party-toolbar">
        <label className="field">
          旅行の計画
          <Choice
            value={party?.id || ""}
            disabled={!!busy}
            onChange={(e) => {
              if (e.target.value) void loadParty(e.target.value);
              else setParty(null);
            }}
          >
            <option value="">自分の計画</option>
            {parties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </Choice>
        </label>
        <button
          className="button primary"
          disabled={!community || !!busy}
          onClick={() => {
            setError("");
            setCreating(true);
          }}
        >
          <Icon name="plus" />
          旅を計画
        </button>
        <button
          className="icon-button"
          aria-label="計画と候補を更新"
          disabled={!!busy}
          onClick={() => void load()}
        >
          <Icon name="refresh" />
        </button>
      </div>
      <ErrorBox message={error} />
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      {party && (
        <header className="party-header">
          <div>
            <span className="small-label">
              {isRep ? "あなたが代表者" : "計画のメンバー"} · 計画中のアカウント{" "}
              {party.active_account_count}人
            </span>
            <h2>{party.title}</h2>
          </div>
          <RequirementsSummary value={party.requirements} />
          {isRep && (
            <button className="text-button" onClick={() => setClosing(true)}>
              この計画を閉じる
            </button>
          )}
          {party.status === "closed" && (
            <p className="hint-box">
              終了した計画です。内容を振り返ることができます。
            </p>
          )}
          <div className="market-tabs">
            {(
              [
                { id: "conversation", label: "講の会話" },
                { id: "conditions", label: "旅行条件" },
                { id: "plans", label: "行程を探す" },
                { id: "consultation", label: "事業者に相談" },
              ] as const
            ).map((t) => (
              <button
                className={tab === t.id ? "selected" : ""}
                aria-pressed={tab === t.id}
                key={t.id}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </header>
      )}
      {party && tab === "conversation" ? (
        <>
          <div className="section-title">
            <h2>旅行条件の相談</h2>
            <button
              className="text-button"
              disabled={!!busy || !messages.length || party.status === "closed"}
              onClick={() => void extract()}
            >
              <Icon name="leaf" />
              {busy === "extract" ? "整理中…" : "最近の会話から条件を整理"}
            </button>
          </div>
          <p className="muted">
            この計画のメンバーだけの会話です。事業者には公開されません。
          </p>
          <Conversation
            endpoint={`/travel-parties/${party.id}/messages`}
            messages={messages}
            user={user}
            onSent={refreshMessages}
            closed={party.status === "closed"}
          />
        </>
      ) : party && tab === "conditions" ? (
        <section className="surface">
          <h2>旅行条件を確かめる</h2>
          <p className="muted">
            代表者が条件を確定します。全員の旅行参加が確定したことを意味しません。
          </p>
          {isRep ? (
            <RequirementEditor
              key={`${party.id}-${party.requirements?.version || 0}`}
              initial={party.requirements}
              tags={tags}
              draft={draft}
              busy={!!busy}
              onSave={saveRequirements}
            />
          ) : (
            <RequirementsSummary value={party.requirements} />
          )}
        </section>
      ) : party && tab === "consultation" ? (
        <>
          <div className="section-title">
            <h2>選んだ事業者との相談</h2>
            <button
              className="text-button"
              disabled={!!busy}
              onClick={() => void load()}
            >
              <Icon name="refresh" />
              更新
            </button>
          </div>
          {currentThreads.length === 0 ? (
            <Empty title="相談するプランが選ばれていません">
              <p>
                共有内容を確認して送るまで、事業者にあなたの計画は見えません。
              </p>
              <button
                className="button secondary"
                onClick={() => setTab("plans")}
              >
                行程を探す
              </button>
            </Empty>
          ) : (
            currentThreads.map((c) => (
              <button
                key={c.id}
                className="consultation-row"
                data-consultation-id={c.id}
                disabled={!!busy}
                onClick={() => void openThread(c)}
              >
                <span className="round-icon">
                  <Icon name="people" />
                </span>
                <span>
                  <strong>{c.selection.plan.provider.name}</strong>
                  <small>{c.selection.plan.title}</small>
                  <span className="thread-status">
                    {c.status === "open" ? "相談中" : "終了"}
                  </span>
                </span>
                <Icon name="arrow" />
              </button>
            ))
          )}
        </>
      ) : !party && community ? (
        <Suspense fallback={<p role="status">関連する旅をひらいています…</p>}>
          <PlanDiscovery
            key={`${user.id}-${community.id}`}
            community={community}
            tags={tags}
            onOpenCircle={onOpenCircle}
          />
        </Suspense>
      ) : (
        <>
          <div className="market-discovery-heading">
            <div>
              <h2>
                {party ? "この仲間で、こんな旅。" : "地域の人が案内する旅"}
              </h2>
            </div>
            {party && (
              <button
                className="button secondary"
                disabled={
                  !!busy || !party.requirements || party.status === "closed"
                }
                onClick={() => void recommend()}
              >
                <Icon name="leaf" />
                {busy === "recommend" ? "探しています…" : "条件から候補を探す"}
              </button>
            )}
          </div>
          {party && !party.requirements && (
            <p className="hint-box">
              旅行条件を確定すると、人数・泊数・予算に合う候補を探せます。
            </p>
          )}
          <div className="catalog-switch">
            <button
              className={source === "catalog" ? "selected" : ""}
              aria-pressed={source === "catalog"}
              onClick={() => setSource("catalog")}
            >
              事業者の全プラン
            </button>
            <button
              className={source === "recommended" ? "selected" : ""}
              aria-pressed={source === "recommended"}
              disabled={!run}
              onClick={() => setSource("recommended")}
            >
              条件に合う候補
            </button>
          </div>
          {source === "recommended" && run && (
            <p className="muted">
              確認した旅行条件との照合結果です。営業時間・空席・予約可否は別途相談してください。
            </p>
          )}
          {candidates.length === 0 ? (
            <Empty
              title={
                source === "recommended"
                  ? "この条件に合うプランはありません"
                  : "プランを読み込んでいます"
              }
            >
              <p>人数・泊数・予算の範囲を確認し、条件を調整してみましょう。</p>
              {party && (
                <button
                  className="button secondary"
                  onClick={() => setTab("conditions")}
                >
                  旅行条件を見直す
                </button>
              )}
            </Empty>
          ) : (
            <div className="market-plan-grid">
              {candidates.map((p, index) => {
                const match = run?.items.find((item) => item.plan.id === p.id);
                return (
                  <PlanCard
                    key={p.id}
                    plan={p}
                    tags={tags}
                    featured={index === 0}
                    reason={
                      source === "recommended" ? match?.reasons[0] : undefined
                    }
                    onOpen={() => setDetail(p)}
                  />
                );
              })}
            </div>
          )}
          {source === "recommended" &&
            run &&
            run.items.filter((c) => !c.eligible).length > 0 && (
              <details className="mismatch-details">
                <summary>条件に合わなかったプランを確認</summary>
                {run.items
                  .filter((c) => !c.eligible)
                  .map((c) => (
                    <div key={c.plan.id}>
                      <strong>{c.plan.title}</strong>
                      <p>{c.excluded_reasons.join(" / ")}</p>
                    </div>
                  ))}
              </details>
            )}
        </>
      )}
      {closing && (
        <Modal
          title="この計画を閉じますか？"
          onClose={() => setClosing(false)}
          busy={!!busy}
        >
          <p>関連する事業者との相談も終了します。これまでの記録は残ります。</p>
          <ErrorBox message={error} />
          <div className="dialog-actions">
            <button
              className="button secondary"
              disabled={!!busy}
              onClick={() => setClosing(false)}
            >
              続けて計画する
            </button>
            <button
              className="button primary"
              disabled={!!busy}
              onClick={() => void closeParty()}
            >
              計画を閉じる
            </button>
          </div>
        </Modal>
      )}
      {creating && (
        <Modal
          title="新しい旅を計画する"
          onClose={() => setCreating(false)}
          busy={!!busy}
        >
          <ErrorBox message={error} />
          <p className="muted">
            {community?.name}で、旅行の希望をまとめる場所をつくります。
          </p>
          <label className="field">
            旅の名前
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={120}
              disabled={!!busy}
              placeholder="例：同期6人、軽井沢の週末"
            />
          </label>
          <label className="field">
            誰と計画する？
            <Choice
              value={groupId}
              onChange={(e) => {
                setGroupId(e.target.value);
                setMemberIds([]);
              }}
              disabled={!!busy}
            >
              <option value="">まずは代表者の自分だけ</option>
              {myGroups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.purpose}
                </option>
              ))}
            </Choice>
          </label>
          {creatingGroup && (
            <fieldset className="permission-group" disabled={!!busy}>
              <legend>計画を共有する講のメンバー</legend>
              {creatingGroup.members
                .filter((m) => m.id !== user.id)
                .map((m) => (
                  <label className="check-row" key={m.id}>
                    <input
                      type="checkbox"
                      checked={memberIds.includes(m.id)}
                      onChange={(e) =>
                        setMemberIds(
                          e.target.checked
                            ? [...memberIds, m.id]
                            : memberIds.filter((id) => id !== m.id),
                        )
                      }
                    />
                    <span>{m.name}</span>
                  </label>
                ))}
            </fieldset>
          )}
          <p className="muted">
            代表者はあなたです。予定する旅行人数は次の画面で入力できます。計画の共有と、旅行参加の承諾は別です。
          </p>
          <button
            className="button primary full"
            disabled={!!busy || !title.trim()}
            onClick={() => void create()}
          >
            {busy ? "作成中…" : "旅の計画をつくる"}
          </button>
        </Modal>
      )}
      {detail && (
        <PlanDetail
          plan={detail}
          tags={tags}
          onClose={() => setDetail(null)}
          disabled={!!busy}
          onChoose={
            isRep || !party
              ? () => {
                  if (!party) {
                    setDetail(null);
                    setCreating(true);
                  } else void prepare(detail);
                }
              : undefined
          }
          chooseLabel={!party ? "この旅の計画をつくる" : "共有する内容を確認"}
        />
      )}
      {preview && chosen && party && (
        <Modal
          title="この事業者に相談を送る"
          onClose={() => setPreview(null)}
          busy={!!busy}
          wide
        >
          <ErrorBox message={error} />
          <div className="sharing-recipient">
            <Icon name="people" />
            <div>
              <span className="small-label">送る相手</span>
              <h3>{chosen.provider.name}</h3>
            </div>
          </div>
          <h3>{chosen.title}</h3>
          <RequirementsSummary value={preview.shared_conditions} />
          {preview.match.unknowns.map((w, i) => (
            <p className="muted" key={i}>
              {w}
            </p>
          ))}
          <label className="field">
            最初に相談したいこと
            <textarea
              value={shareNote}
              onChange={(e) => setShareNote(e.target.value)}
              maxLength={1000}
              rows={4}
              disabled={!!busy}
              placeholder="例：6人で利用したいです。食事の時間を相談できますか？"
            />
          </label>
          <div className="privacy-summary">
            <strong>相手に共有する内容</strong>
            <p>
              選んだプラン、人数・泊数・希望日・予算、相談文、相談中の発言者の表示名。
            </p>
            <p>講の内部会話・元の写真・個別の好みは共有しません。</p>
          </div>
          {currentThreads.some((c) => c.status === "open") && (
            <p className="hint-box">
              新しく選ぶと、現在の事業者との相談は終了します。過去に送った内容は相手が既に見ている場合があります。
            </p>
          )}
          <label className="check-row">
            <input
              type="checkbox"
              checked={shareConfirmed}
              disabled={!!busy}
              onChange={(e) => setShareConfirmed(e.target.checked)}
            />
            <span>
              送る相手と共有内容を確認しました。予約の確定ではないことを理解しています。
            </span>
          </label>
          <button
            className="button primary full"
            disabled={!!busy || !shareConfirmed}
            onClick={() => void select()}
          >
            {busy ? "送信中…" : "この内容で相談を送る"}
            <Icon name="arrow" />
          </button>
        </Modal>
      )}
      {thread && (
        <Modal
          title="事業者との相談"
          onClose={() => setThread(null)}
          wide
          variant="conversation"
        >
          <Conversation
            context={
              <div className="consultation-context">
                <span className="small-label">
                  {thread.selection.plan.provider.name}
                </span>
                <h3>{thread.selection.plan.title}</h3>
                <RequirementsSummary
                  value={thread.selection.shared_conditions}
                />
                {thread.selection.share_note && (
                  <p>{thread.selection.share_note}</p>
                )}
              </div>
            }
            endpoint={`/consultations/${thread.id}/messages`}
            messages={threadMessages}
            user={user}
            closed={thread.status === "closed"}
            label="事業者との相談"
            onSent={async () => {
              const r = await api<{ items: MarketMessage[] }>(
                `/consultations/${thread.id}/messages`,
              );
              setThreadMessages(r.items);
            }}
          />
        </Modal>
      )}
    </section>
  );
}
