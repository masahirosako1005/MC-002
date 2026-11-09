import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import type { Tag, User } from "./types";
import type {
  MarketMessage,
  ProviderPlan,
  SharedConditions,
} from "./marketplace-types";
import { Avatar, Empty, ErrorBox, Icon, LocalPhoto, Modal, Tags } from "./ui";
export const periods = {
  morning: "午前",
  afternoon: "午後",
  evening: "夕方・夜",
};
export function coverFor(plan: ProviderPlan) {
  return `/api/covers/${plan.tags.includes("coast") ? "coast" : plan.tags.includes("cafe") && !plan.tags.includes("nature") ? "coffee" : "woodland"}`;
}
export function scheduleLabel(plan: ProviderPlan) {
  if (plan.schedule_type !== "dated") return "日程は相談";
  if (!plan.starts_at || !plan.ends_at) return "開催日時を確認してください";
  const format = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${format.format(new Date(plan.starts_at))}〜${format.format(new Date(plan.ends_at))}（日本時間）`;
}
export function priceLabel(plan: ProviderPlan) {
  return `${plan.price_yen.toLocaleString()}円 / ${plan.price_basis === "per_person" ? "1人" : "全員"}`;
}
export function scopeLabel(scope: string | null) {
  return scope === "whole_trip"
    ? "旅行全体"
    : scope === "plan_only"
      ? "プラン部分"
      : "範囲未指定";
}
export function RequirementsSummary({
  value,
}: {
  value: SharedConditions | null;
}) {
  return (
    <div className="requirements-summary">
      <span>
        <Icon name="people" />
        {value ? `${value.planned_people}人` : "人数を決める"}
      </span>
      <span>
        <Icon name="calendar" />
        {value
          ? value.nights === 0
            ? "日帰り"
            : `${value.nights}泊${value.nights + 1}日`
          : "泊数を決める"}
      </span>
      <span>
        {value?.budget_yen
          ? `${value.budget_yen.toLocaleString()}円 / ${value.budget_basis === "per_person" ? "1人" : "全員"} · ${scopeLabel(value.budget_scope)}`
          : "予算は相談"}
      </span>
      <span>{value?.date_start || "日程は相談"}</span>
    </div>
  );
}
export function PlanCard({
  plan,
  tags,
  featured = false,
  reason,
  onOpen,
  actionLabel = "日別の行程を見る",
  onAdd,
}: {
  plan: ProviderPlan;
  tags: Tag[];
  featured?: boolean;
  reason?: string;
  onOpen: () => void;
  actionLabel?: string;
  onAdd?: () => void;
}) {
  return (
    <article className={`market-plan-card ${featured ? "featured" : ""}`}>
      <LocalPhoto src={coverFor(plan)} alt={`${plan.area}の旅のイメージ`} />
      <div className="market-plan-copy">
        <span className="small-label">
          {plan.area} ·{" "}
          {plan.nights === 0
            ? "日帰り"
            : `${plan.nights}泊${plan.nights + 1}日`}
        </span>
        <h3>{plan.title}</h3>
        <p className="provider-name">{plan.provider.name}</p>
        <p className="plan-card-summary">{plan.summary}</p>
        <p className="plan-schedule">
          <Icon name="calendar" />
          {scheduleLabel(plan)}
        </p>
        <Tags ids={plan.tags.slice(0, 3)} tags={tags} />
        {reason && (
          <p className="match-reason">
            <Icon name="leaf" />
            {reason}
          </p>
        )}
        <div className="plan-price">
          <strong>{priceLabel(plan)}</strong>
          <span>
            {scopeLabel(plan.price_scope)}の概算 · {plan.min_people}〜
            {plan.max_people}人
          </span>
        </div>
        <button className="button secondary" onClick={onOpen}>
          {actionLabel}
          <Icon name="arrow" />
        </button>
        {onAdd && (
          <button className="button primary" onClick={onAdd}>
            <Icon name="plus" />
            講に追加
          </button>
        )}
      </div>
    </article>
  );
}
export function PlanDetail({
  plan,
  tags,
  onClose,
  onChoose,
  chooseLabel = "このプランで相談を考える",
  disabled = false,
}: {
  plan: ProviderPlan;
  tags: Tag[];
  onClose: () => void;
  onChoose?: () => void;
  chooseLabel?: string;
  disabled?: boolean;
}) {
  return (
    <Modal title="プランの行程と費用" onClose={onClose} wide busy={disabled}>
      <div className="plan-detail-cover">
        <LocalPhoto src={coverFor(plan)} alt={`${plan.area}の旅のイメージ`} />
        <span>{plan.area}</span>
      </div>
      <p className="small-label">{plan.provider.name}</p>
      <h2 className="plan-detail-title">{plan.title}</h2>
      <p>{plan.summary}</p>
      <p className="plan-schedule">
        <Icon name="calendar" />
        {scheduleLabel(plan)}
      </p>
      <Tags ids={plan.tags} tags={tags} />
      <div className="price-summary">
        <strong>{priceLabel(plan)}</strong>
        <span>
          {scopeLabel(plan.price_scope)}の概算 / {plan.min_people}〜
          {plan.max_people}人
        </span>
        <p>{plan.price_note}</p>
      </div>
      <div className="day-itinerary">
        {Array.from({ length: plan.nights + 1 }, (_, i) => i + 1).map((day) => (
          <section key={day}>
            <div className="day-marker">
              <span>{String(day).padStart(2, "0")}</span>
              <h3>{day}日目</h3>
            </div>
            {plan.itinerary
              .filter((item) => item.day === day)
              .map((item, index) => (
                <div className="itinerary-stop" key={index}>
                  <span>{periods[item.period]}</span>
                  <div>
                    <strong>{item.place}</strong>
                    <p>{item.description}</p>
                    <small>
                      {item.travel_minutes === null
                        ? "移動時間は相談して確認"
                        : `前の場所からの移動目安 ${item.travel_minutes}分`}
                    </small>
                  </div>
                </div>
              ))}
          </section>
        ))}
      </div>
      {onChoose && (
        <div className="plan-detail-action">
          <p className="muted">
            次に共有内容を確認します。まだ事業者への連絡は送られません。
          </p>
          <button
            className="button primary full"
            disabled={disabled}
            onClick={onChoose}
          >
            {chooseLabel}
            <Icon name="arrow" />
          </button>
        </div>
      )}
    </Modal>
  );
}
export function useRequestKey() {
  const ref = useRef({ payload: "", key: "" });
  const keyFor = (payload: unknown) => {
    const text = JSON.stringify(payload);
    if (text !== ref.current.payload || !ref.current.key)
      ref.current = { payload: text, key: crypto.randomUUID() };
    return ref.current.key;
  };
  return Object.assign(keyFor, {
    reset: () => {
      ref.current = { payload: "", key: "" };
    },
  });
}
export function Conversation({
  endpoint,
  messages,
  user,
  onSent,
  closed = false,
  label = "講のメンバーとの会話",
  context,
}: {
  endpoint: string;
  messages: MarketMessage[];
  user: User;
  onSent: () => Promise<void>;
  closed?: boolean;
  label?: string;
  context?: ReactNode;
}) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const requestKey = useRequestKey();
  const history = useRef<HTMLDivElement>(null);
  const latestMessageId = messages.at(-1)?.id;
  useEffect(() => {
    if (history.current)
      history.current.scrollTop = latestMessageId || error ? history.current.scrollHeight : 0;
  }, [latestMessageId, error]);
  async function send() {
    setBusy(true);
    setError("");
    try {
      await api(endpoint, "POST", {
        body,
        client_request_id: requestKey({ endpoint, body }),
      });
      setBody("");
      requestKey.reset();
      await onSent();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="conversation" aria-label={label}>
      <div
        className="conversation-history"
        ref={history}
        tabIndex={0}
        role="region"
        aria-label={`${label}の履歴と共有条件`}
      >
        {context}
        {messages.length === 0 ? (
          <Empty title="まずは、希望をひとこと">
            <p>行きたい場所、人数、泊数、予算などを書いてみましょう。</p>
          </Empty>
        ) : (
          messages.map((m) => (
            <article
              key={m.id}
              className={`message ${m.author_name === user.name ? "mine" : ""}`}
            >
              <Avatar
                user={{
                  name: m.author_name,
                  initials: m.author_name.slice(0, 1),
                  color: "",
                }}
                small
              />
              <div>
                <div className="message-author">
                  <strong>{m.author_name}</strong>
                  <time dateTime={m.created_at}>
                    {new Intl.DateTimeFormat("ja-JP", {
                      month: "numeric",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    }).format(new Date(m.created_at))}
                  </time>
                </div>
                <p>{m.body}</p>
              </div>
            </article>
          ))
        )}
        <ErrorBox message={error} />
      </div>
      {closed ? (
        <p className="quiet-note">この相談は終了しています。</p>
      ) : (
        <form
          className="message-form"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <label className="sr-only" htmlFor={`message-${endpoint}`}>
            {label}に送るメッセージ
          </label>
          <textarea
            id={`message-${endpoint}`}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            disabled={busy}
            maxLength={2000}
            rows={2}
            placeholder="みんなに伝えたいこと"
          />
          <button className="button primary" disabled={busy || !body.trim()}>
            {busy ? "送信中…" : "送る"}
            <Icon name="arrow" />
          </button>
        </form>
      )}
    </section>
  );
}
