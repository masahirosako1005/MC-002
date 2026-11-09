import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import Choice from "./Choice";
import { Empty, ErrorBox, Icon, Modal } from "./ui";
import {
  PlanCard,
  PlanDetail,
  scheduleLabel,
  useRequestKey,
} from "./marketplace-ui";
import type { Community, Tag, User } from "./types";
import type { ProviderPlan } from "./marketplace-types";
import type { CircleDetail, CircleList, CircleSummary } from "./circle-types";
import { ExperienceReference } from "./ExperienceReference";
import type { PublicExperienceSummary } from "./reflection-types";
import "./discovery.css";

export type CandidateCard = {
  id: string;
  circle_id: string;
  plan_id: string;
  plan_version: number;
  snapshot: ProviderPlan;
  saved_by: User;
  created_at: string;
  version: number;
  current_state:
    "available" | "updated" | "unpublished" | "ended" | "conditions_changed";
  current_plan: ProviderPlan | null;
  reasons: string[];
  unknowns: string[];
};
type DiscoveryResult = {
  items: {
    plan: ProviderPlan;
    score: number;
    reasons: string[];
    unknowns: string[];
    match_status: string;
    schedule_status: string;
    experience_reference?: PublicExperienceSummary;
  }[];
  context: {
    community_id: string;
    circle_id: string | null;
    profile_used: boolean;
    requirements_version: number | null;
  };
  method: string;
};
const candidateState = {
  available: "候補として共有中",
  updated: "公開内容が変わりました",
  unpublished: "現在は公開されていません",
  ended: "開催期間が終了しました",
  conditions_changed: "今の旅行条件とは一致しません",
};

export function SavedCandidateList({
  cards,
  onOpen,
}: {
  cards: CandidateCard[];
  onOpen: (plan: ProviderPlan, canInvite: boolean) => void;
}) {
  const [page, setPage] = useState(0);
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil(cards.length / 4) - 1),
  );
  return (
    <section className="saved-candidates">
      <h3>この講の候補一覧</h3>
      <p className="discovery-note">
        候補の保存だけでは、事業者への招待や予約は行われません。
      </p>
      {cards.length ? (
        <>
          {cards.slice(currentPage * 4, (currentPage + 1) * 4).map((card) => (
            <article className="saved-candidate" key={card.id}>
              <p className={`candidate-state ${card.current_state}`}>
                {candidateState[card.current_state]}
              </p>
              <h4>{card.snapshot.title}</h4>
              <p>
                {card.snapshot.area} · {card.snapshot.provider.name}
              </p>
              <p className="plan-schedule">{scheduleLabel(card.snapshot)}</p>
              <p>{card.snapshot.summary}</p>
              <small>
                {card.saved_by.name}が追加 · 保存時 第{card.plan_version}版
              </small>
              {card.reasons.length > 0 && (
                <p className="discovery-reason">{card.reasons.join("・")}</p>
              )}
              {card.unknowns.length > 0 && (
                <details>
                  <summary>確認が必要なこと</summary>
                  <ul>
                    {card.unknowns.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </details>
              )}
              {card.current_state === "updated" && (
                <p className="discovery-note">
                  保存した内容はそのまま残しています。最新の詳細を確認してから行き先を決めてください。
                </p>
              )}
              <button
                className="button secondary full"
                onClick={() =>
                  onOpen(
                    ["available", "updated"].includes(card.current_state)
                      ? card.current_plan || card.snapshot
                      : card.snapshot,
                    ["available", "updated"].includes(card.current_state),
                  )
                }
              >
                {card.current_state === "updated"
                  ? "最新の詳細を確認"
                  : card.current_state === "available"
                    ? "候補の詳細を見る"
                    : "保存した内容を確認"}
                <Icon name="arrow" />
              </button>
            </article>
          ))}
          {cards.length > 4 && (
            <div className="discovery-pager">
              <button
                className="button secondary"
                disabled={!currentPage}
                onClick={() => setPage(currentPage - 1)}
              >
                前へ
              </button>
              <span>
                {currentPage * 4 + 1}〜
                {Math.min((currentPage + 1) * 4, cards.length)} / {cards.length}
                件
              </span>
              <button
                className="button secondary"
                disabled={(currentPage + 1) * 4 >= cards.length}
                onClick={() => setPage(currentPage + 1)}
              >
                次へ
              </button>
            </div>
          )}
        </>
      ) : (
        <p className="muted">プランの「講に追加」から候補を保存できます。</p>
      )}
    </section>
  );
}

function SaveToCircle({
  plan,
  community,
  circles,
  initialCircleId,
  onClose,
  onSaved,
}: {
  plan: ProviderPlan;
  community: Community;
  circles: CircleSummary[];
  initialCircleId: string;
  onClose: () => void;
  onSaved: (circleId: string) => void;
}) {
  const [circleId, setCircleId] = useState(initialCircleId);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<CircleDetail | null>(null);
  const key = useRequestKey();
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  async function save() {
    setBusy(true);
    setError("");
    try {
      let target = circleId;
      if (!target) {
        const payload = {
          community_id: community.id,
          title: title.trim(),
          mode: "manual",
          tags: [],
          desired_count: 2,
          invitee_ids: [],
        };
        const result = await api<CircleDetail>("/circles", "POST", {
          ...payload,
          client_request_id: key(payload),
        });
        if (!alive.current) return;
        target = result.id;
        setCircleId(result.id);
        setCreated(result);
      }
      const payload = { plan_id: plan.id, plan_version: plan.version };
      await api(`/circles/${target}/candidate-cards`, "POST", {
        ...payload,
        client_request_id: key({ circle: target, ...payload }),
      });
      if (alive.current) onSaved(target);
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  const options =
    created && !circles.some((circle) => circle.id === created.id)
      ? [...circles, created]
      : circles;
  return (
    <Modal title="講に候補を追加する" onClose={onClose} busy={busy} wide>
      <div className="discovery-save">
        <ErrorBox message={error} />
        <p className="small-label">
          {plan.area} · {plan.provider.name}
        </p>
        <h3>{plan.title}</h3>
        <p>{scheduleLabel(plan)}</p>
        <label className="field">
          追加する講
          <Choice
            value={circleId}
            disabled={busy}
            onChange={(event) => setCircleId(event.target.value)}
          >
            <option value="">新しい講をつくる</option>
            {options.map((circle) => (
              <option value={circle.id} key={circle.id}>
                {circle.title}
              </option>
            ))}
          </Choice>
        </label>
        {!circleId && (
          <>
            <label className="field">
              新しい講の名前
              <input
                maxLength={120}
                value={title}
                disabled={busy}
                placeholder="例：次の休日に森を歩く仲間"
                onChange={(event) => setTitle(event.target.value)}
              />
            </label>
            <p className="discovery-note">
              まず自分の講をつくり、候補を残します。仲間は講の画面から招待できます。
            </p>
          </>
        )}
        <div className="discovery-sharing">
          <Icon name="people" />
          <p>
            選んだ講の参加者に、プランの公開内容を候補として共有します。プロフィールの個人的な関心や、おすすめ理由は共有しません。
          </p>
        </div>
        <p className="discovery-note">
          事業者への招待・予約・訪問実績にはなりません。
        </p>
        <button
          className="button primary full"
          disabled={busy || (!circleId && !title.trim())}
          onClick={() => void save()}
        >
          {busy ? "候補を保存しています…" : "候補を保存して講で話す"}
          <Icon name="arrow" />
        </button>
      </div>
    </Modal>
  );
}

export default function PlanDiscovery({
  community,
  tags,
  circle,
  onOpenCircle,
  refreshKey = 0,
}: {
  community: Community;
  tags: Tag[];
  circle?: CircleSummary;
  onOpenCircle: (circleId: string) => void;
  refreshKey?: number;
}) {
  const [circleId, setCircleId] = useState(circle?.id || "");
  const [circles, setCircles] = useState<CircleSummary[]>([]);
  const [data, setData] = useState<DiscoveryResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadKey, setLoadKey] = useState(0);
  const [page, setPage] = useState(0);
  const [detail, setDetail] = useState<ProviderPlan | null>(null);
  const [saving, setSaving] = useState<ProviderPlan | null>(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setData(null);
    setPage(0);
    const selected = circle?.id || circleId;
    Promise.all([
      api<DiscoveryResult>(
        `/plan-discovery?community_id=${encodeURIComponent(community.id)}${selected ? `&circle_id=${encodeURIComponent(selected)}` : ""}`,
      ),
      api<CircleList>("/circles"),
    ])
      .then(([result, list]) => {
        if (!active) return;
        setData(result);
        setCircles(
          list.items.filter(
            (item) =>
              item.community_id === community.id && item.status === "open",
          ),
        );
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [
    community.id,
    circle?.id,
    circle?.version,
    circle?.requirements?.version,
    circleId,
    loadKey,
    refreshKey,
  ]);
  return (
    <section className="plan-discovery">
      <div className="market-discovery-heading">
        <div>
          <p className="eyebrow">
            {circle || circleId
              ? "あなたの講へのおすすめ順"
              : "地域の人が案内する旅"}
          </p>
          <h2>{circle ? "この講の旅行プラン" : "旅行プラン"}</h2>
        </div>
        <button
          className="text-button"
          disabled={loading}
          onClick={() => setLoadKey((value) => value + 1)}
        >
          <Icon name="refresh" />
          おすすめを更新
        </button>
      </div>
      {!circle && (
        <label className="field">
          どの講で行く旅を探す？
          <Choice
            value={circleId}
            disabled={loading}
            onChange={(event) => setCircleId(event.target.value)}
          >
            <option value="">自分の関心から探す</option>
            {circles.map((item) => (
              <option value={item.id} key={item.id}>
                {item.title}
              </option>
            ))}
          </Choice>
        </label>
      )}
      <ErrorBox message={error} />
      {data && (
        <p className="discovery-note">
          {data.context.profile_used
            ? "このコミュニティで利用を許可した自分の関心"
            : "プロフィールの関心は使用せず、公開内容"}
          {data.context.circle_id ? "と、この講の希望・確定した旅行条件" : ""}
          をもとに、関連する順に表示しています。人気順や予約可能の保証ではありません。
        </p>
      )}
      {loading ? (
        <p role="status">関連する旅を探しています…</p>
      ) : data?.items.length ? (
        <>
          <div className="market-plan-grid">
            {data.items.slice(page * 4, (page + 1) * 4).map((item) => (
              <div className="discovery-plan" key={item.plan.id}>
                <PlanCard
                  plan={item.plan}
                  tags={tags}
                  reason={item.reasons.join("・")}
                  onOpen={() => setDetail(item.plan)}
                  onAdd={() => setSaving(item.plan)}
                />
                <p className="discovery-note">
                  {item.schedule_status === "ongoing"
                    ? "開催期間中。空席は確認が必要です。"
                    : item.schedule_status === "upcoming"
                      ? "開催予定。空席は確認が必要です。"
                      : "日程は相談。希望日が決まったら確認しましょう。"}
                </p>
                {item.experience_reference && (
                  <ExperienceReference summary={item.experience_reference} />
                )}
                {item.unknowns.length > 0 && (
                  <details className="discovery-unknowns">
                    <summary>確認が必要なこと</summary>
                    <ul>
                      {item.unknowns.map((unknown, index) => (
                        <li key={index}>{unknown}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))}
          </div>
          {data.items.length > 4 && (
            <div className="discovery-pager">
              <button
                className="button secondary"
                disabled={!page}
                onClick={() => setPage((value) => value - 1)}
              >
                前へ
              </button>
              <span>
                {page * 4 + 1}〜{Math.min((page + 1) * 4, data.items.length)} /{" "}
                {data.items.length}件
              </span>
              <button
                className="button secondary"
                disabled={(page + 1) * 4 >= data.items.length}
                onClick={() => setPage((value) => value + 1)}
              >
                次へ
              </button>
            </div>
          )}
        </>
      ) : (
        !error && (
          <Empty title="今の希望に合うプランはありません">
            <p>講の希望や旅行条件を見直して、もう一度探してみましょう。</p>
          </Empty>
        )
      )}
      {detail && (
        <PlanDetail
          plan={detail}
          tags={tags}
          onClose={() => setDetail(null)}
          chooseLabel="このプランを講に追加"
          onChoose={() => {
            setSaving(detail);
            setDetail(null);
          }}
        />
      )}
      {saving && (
        <SaveToCircle
          plan={saving}
          community={community}
          circles={
            circle && !circles.some((item) => item.id === circle.id)
              ? [...circles, circle]
              : circles
          }
          initialCircleId={circle?.id || circleId}
          onClose={() => setSaving(null)}
          onSaved={(id) => {
            setSaving(null);
            onOpenCircle(id);
          }}
        />
      )}
    </section>
  );
}
