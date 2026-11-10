import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import Choice from "./Choice";
import type { CircleDetail, CircleList, CircleSummary } from "./circle-types";
import type {
  Benefit,
  DaytripCatalog,
  DaytripMe,
  DaytripProviderData,
  Outing,
  Redemption,
  RankStatus,
  Route,
} from "./daytrip-types";
import { RANK_NAMES } from "./daytrip-types";
import type { User } from "./types";
import { Empty, ErrorBox, Icon, Modal } from "./ui";
import DaytripCover from "./DaytripCover";
import {
  BenefitLocation,
  BenefitTerms,
  DaytripBenefits,
  benefitsForRoute,
} from "./DaytripBenefits";
import { errorMessage } from "./validation";
import "./daytrip.css";
import { ScrollHeading, SealMark, TravelCrest, WoodcutArt } from "./WaArt";
import type { ProgramStep } from "./journey-program-types";
const JourneyPrograms = lazy(() => import("./JourneyPrograms"));
const BenefitZonePolicy = lazy(() => import("./BenefitZonePolicy"));

const yen = (value: number) => `${value.toLocaleString("ja-JP")}円`;
const rankLabel = (rank: number) => RANK_NAMES[rank - 1] || RANK_NAMES[0];
const zoneLabel = {
  target: "20〜40km",
  nearby: "20km未満",
  outside: "範囲外",
  unknown: "経路を確認中",
};
const statusLabel = {
  scheduled: "開催予定",
  reporting: "実施確認中",
  confirmed: "実施確認済み",
  cancelled: "中止・取消",
};
const encoded = encodeURIComponent;
function japanDate(value: string, includeYear = false) {
  return new Intl.DateTimeFormat("ja-JP", {
    year: includeYear ? "numeric" : undefined,
    month: "long",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tokyo",
  }).format(new Date(value));
}
function localDate() {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" }).format(
    new Date(),
  );
}
function tomorrowDate() {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" }).format(
    new Date(Date.now() + 86400000),
  );
}
function RouteFacts({ route }: { route: Route }) {
  return (
    <div className="daytrip-facts">
      <span>
        <Icon name="compass" />
        片道{" "}
        {route.one_way_km === null ? "距離未確認" : `${route.one_way_km} km`}
      </span>
      <span>
        <Icon name="calendar" />
        {route.one_way_minutes === null
          ? "時間未確認"
          : `片道 約${route.one_way_minutes}分`}
      </span>
      <span>
        {route.mode === "rail"
          ? "鉄道"
          : route.mode === "car"
            ? "車"
            : route.mode}
      </span>
    </div>
  );
}

function sameRankProgress(first: RankStatus, second: RankStatus) {
  const fields: (keyof RankStatus)[] = [
    "policy_version",
    "rank",
    "name",
    "lifetime_points",
    "recent_points",
    "lifetime_rank",
    "guaranteed_rank",
    "maintenance_points",
    "next_rank",
    "next_rank_points",
    "next_lifetime_points_needed",
    "next_recent_points_needed",
    "next_demotion_at",
  ];
  return fields.every((key) => first[key] === second[key]);
}
function RankProgress({ status }: { status: RankStatus }) {
  return (
    <div className="rank-progress">
      <p>
        直近365日の活動{" "}
        <strong>{status.recent_points.toLocaleString("ja-JP")}点</strong>
        {status.maintenance_points !== null
          ? ` ／ 維持に必要 ${status.maintenance_points.toLocaleString("ja-JP")}点`
          : ""}
      </p>
      {status.next_rank !== null ? (
        <p className="quiet-note">
          次の「{rankLabel(status.next_rank)}」まで累積あと
          {status.next_lifetime_points_needed.toLocaleString("ja-JP")}点
          {status.next_rank > 4
            ? `、直近365日の活動あと${status.next_recent_points_needed.toLocaleString("ja-JP")}点`
            : ""}
          。
        </p>
      ) : (
        <p className="quiet-note">
          最上位の勧進元です。直近365日の活動で維持します。
        </p>
      )}
      {status.next_demotion_at ? (
        <p className="rank-maintenance-note">
          新しい活動がなければ、{japanDate(status.next_demotion_at, true)}
          に階級が下がります。
        </p>
      ) : null}
      <p className="quiet-note">
        累積点による維持は「{rankLabel(status.guaranteed_rank)}
        」まで。期間が過ぎても累積点は減りません。
      </p>
    </div>
  );
}

function RankBoard({
  rules,
  current,
}: {
  rules: DaytripCatalog["rules"];
  current: number;
}) {
  return (
    <details className="daytrip-details rank-guide">
      <summary>旅の番付と降格条件</summary>
      <p className="quiet-note">
        新客から勧進元までの10階級。大先達以上は、累積点と直近365日の活動点の両方で判定します。
      </p>
      <ol className="rank-banzuke" reversed start={rules.rank_names.length}>
        {rules.rank_names
          .map((_, offset) => {
            const index = rules.rank_names.length - 1 - offset;
            return {
              name: rules.rank_names[index],
              level: index + 1,
              points: rules.rank_thresholds[index],
            };
          })
          .map((item) => (
            <li
              key={item.level}
              className={item.level === current ? "current" : ""}
              aria-current={item.level === current ? "step" : undefined}
            >
              <span className="rank-position">{item.level}</span>
              <div>
                <strong>{item.name}</strong>
                {item.level === current ? (
                  <span className="rank-current-label">現在</span>
                ) : null}
                <small>累積 {item.points.toLocaleString("ja-JP")}点</small>
                <small>
                  {item.level > 4
                    ? `直近365日も ${item.points.toLocaleString("ja-JP")}点`
                    : "累積点で維持"}
                </small>
              </div>
            </li>
          ))}
      </ol>
      <p className="quiet-note">
        このアプリ内の旅の階級です。宗教上の資格・認証ではありません。「開催の先達」は、階級にかかわらず開催ごとに任命・承諾する役割です。
      </p>
      <p className="quiet-note">
        実績を取り消した場合は有効な点で再計算します。自然な降格で、確保済みの割引価格が変わることはありません。
      </p>
    </details>
  );
}

function CreateOuting({
  route,
  circles,
  catalog,
  initialCircleId,
  requiredPlan,
  onClose,
  onCreated,
  onOpenCircle,
}: {
  route: Route;
  circles: CircleSummary[];
  catalog: DaytripCatalog;
  initialCircleId: string;
  requiredPlan?: { id: string; title: string };
  onClose: () => void;
  onCreated: (outing: Outing) => void;
  onOpenCircle: (id: string) => void;
}) {
  const [circleId, setCircleId] = useState(initialCircleId);
  const [circle, setCircle] = useState<CircleDetail | null>(null);
  const [title, setTitle] = useState(
    requiredPlan?.title ||
      route.experience_title ||
      `${route.destination}の日帰り`,
  );
  const [date, setDate] = useState(tomorrowDate);
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("18:00");
  const [participants, setParticipants] = useState<string[]>([]);
  const [leader, setLeader] = useState("");
  const [useProvider, setUseProvider] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(!!initialCircleId);
  const [error, setError] = useState("");
  const requestId = useRef(crypto.randomUUID());
  const submitting = useRef(false);
  const live = useRef(true);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    if (!circleId) return undefined;
    void api<CircleDetail>(`/circles/${encoded(circleId)}`)
      .then((result) => {
        if (!active) return undefined;
        setCircle(result);
        setParticipants(result.members.map((member) => member.id));
        setLeader(result.representative_id);
        return undefined;
      })
      .catch((cause: unknown) => {
        if (active) setError(errorMessage(cause));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [circleId]);
  const invitation = circle?.active_provider_invitation;
  const linkedPlan =
    invitation?.status === "accepted" &&
    (!requiredPlan || invitation.snapshot.plan.id === requiredPlan.id) &&
    catalog.plans.some(
      (link) =>
        link.plan_id === invitation.snapshot.plan.id &&
        link.route_id === route.id,
    )
      ? invitation.snapshot.plan
      : null;
  const stayMinutes =
    Math.round(
      (Date.parse(`${date}T${end}:00+09:00`) -
        Date.parse(`${date}T${start}:00+09:00`)) /
        60000,
    ) -
    (route.one_way_minutes || 0) * 2;
  const valid =
    !!circle?.can_manage &&
    !!title.trim() &&
    !!date &&
    end > start &&
    participants.length >= 2 &&
    participants.includes(leader) &&
    (!requiredPlan || linkedPlan?.id === requiredPlan.id);
  async function create() {
    if (!valid || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await api<Outing>(
        `/circles/${encoded(circleId)}/outings`,
        "POST",
        {
          title: title.trim(),
          route_id: route.id,
          starts_at: `${date}T${start}:00+09:00`,
          ends_at: `${date}T${end}:00+09:00`,
          participant_ids: participants,
          leader_id: leader,
          plan_id: useProvider || requiredPlan ? linkedPlan?.id || null : null,
          client_request_id: requestId.current,
        },
      );
      if (live.current) onCreated(result);
    } catch (cause) {
      if (live.current) setError(errorMessage(cause));
    } finally {
      submitting.current = false;
      if (live.current) setBusy(false);
    }
  }
  return (
    <Modal title="日帰りの開催をつくる" onClose={onClose} busy={busy}>
      <div className="daytrip-form">
        <p className="daytrip-route-title">
          {route.origin} → {route.destination}
        </p>
        <RouteFacts route={route} />
        {requiredPlan && (
          <p className="daytrip-disclosure">
            通う旅の対象プラン：{requiredPlan.title}
            。このプランで事業者の招待承諾を得た講を選んでください。
          </p>
        )}
        <ErrorBox message={error} />
        <fieldset disabled={busy}>
          <label className="field">
            一緒に出かける講
            <Choice
              value={circleId}
              onChange={(event) => {
                // Choosing the current item must preserve its loaded participants and edits.
                if (event.target.value === circleId) return;
                setCircleId(event.target.value);
                setCircle(null);
                setParticipants([]);
                setLeader("");
                setUseProvider(false);
                setError("");
                setLoading(!!event.target.value);
              }}
            >
              <option value="">講を選ぶ</option>
              {circles.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </Choice>
          </label>
          {loading && <output>講の参加者を確認しています…</output>}
          {circle && !circle.can_manage && (
            <p className="hint-box">
              開催は講の代表者が作成できます。
              <button
                className="text-button"
                onClick={() => onOpenCircle(circle.id)}
              >
                この講で相談する
                <Icon name="arrow" />
              </button>
            </p>
          )}
          {circle?.can_manage && (
            <>
              <label className="field">
                開催名
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  maxLength={120}
                />
              </label>
              <label className="field">
                開催日
                <input
                  type="date"
                  value={date}
                  min={localDate()}
                  onChange={(event) => setDate(event.target.value)}
                />
              </label>
              <div className="field-row">
                <label className="field">
                  集合（日本時間）
                  <input
                    type="time"
                    value={start}
                    onChange={(event) => setStart(event.target.value)}
                  />
                </label>
                <label className="field">
                  帰着（同日）
                  <input
                    type="time"
                    value={end}
                    onChange={(event) => setEnd(event.target.value)}
                  />
                </label>
              </div>
              {route.one_way_minutes !== null &&
                Number.isFinite(stayMinutes) && (
                  <p className="quiet-note">
                    往復移動を除く時間：約
                    {Math.max(0, Math.floor(stayMinutes / 60))}時間
                    {Math.max(0, stayMinutes % 60)}分
                    {stayMinutes < 240
                      ? "。現地で4時間ほど過ごせる行程を目安に調整してください。"
                      : ""}
                  </p>
                )}
              <div className="field">
                <span>参加をお願いする人</span>
                {circle.members.map((member) => (
                  <label className="daytrip-check" key={member.id}>
                    <input
                      type="checkbox"
                      checked={participants.includes(member.id)}
                      onChange={(event) =>
                        setParticipants((current) =>
                          event.target.checked
                            ? [...current, member.id]
                            : current.filter((id) => id !== member.id),
                        )
                      }
                    />
                    {member.name}
                  </label>
                ))}
                <p className="quiet-note">
                  一人ずつ参加承諾が必要です。選ぶだけで参加確定にはなりません。
                </p>
              </div>
              <label className="field">
                開催の先達（取りまとめ役）
                <Choice
                  value={leader}
                  onChange={(event) => setLeader(event.target.value)}
                >
                  <option value="">依頼する人を選ぶ</option>
                  {circle.members
                    .filter((member) => participants.includes(member.id))
                    .map((member) => (
                      <option key={member.id} value={member.id}>
                        {member.name}
                      </option>
                    ))}
                </Choice>
              </label>
              <p className="quiet-note">
                今回の募集・日程調整を担う役割です。本人の承諾と、実施後の他参加者の確認を別に記録します。
              </p>
              {linkedPlan ? (
                <label className="daytrip-check">
                  <input
                    type="checkbox"
                    checked={!!requiredPlan || useProvider}
                    disabled={!!requiredPlan}
                    onChange={(event) => setUseProvider(event.target.checked)}
                  />
                  <span>
                    承諾済みの事業者プランを利用する
                    <br />
                    <small>
                      {linkedPlan.title} · {yen(linkedPlan.price_yen)}{" "}
                      {linkedPlan.price_basis === "per_person" ? "/人" : "/組"}
                    </small>
                  </span>
                </label>
              ) : (
                <p className="quiet-note">
                  事業者を利用する場合は、講でプランと共有内容を決め、事業者の参加承諾を受けてください。
                  <button
                    className="text-button"
                    onClick={() => onOpenCircle(circle.id)}
                  >
                    講でプランを相談する
                    <Icon name="arrow" />
                  </button>
                </p>
              )}
              <p className="daytrip-disclosure">
                集合地点は「{route.origin}」。保存すると講の参加者
                {(useProvider || requiredPlan) && linkedPlan
                  ? `と${linkedPlan.provider.name}`
                  : ""}
                に開催の情報が共有されます。予約は別途必要です。
              </p>
            </>
          )}
        </fieldset>
        <button
          className="button primary full"
          disabled={busy || loading || !valid}
          onClick={() => void create()}
        >
          {busy ? "保存しています…" : "開催を保存して参加を依頼"}
        </button>
      </div>
    </Modal>
  );
}

function OutingDetail({
  initial,
  user,
  onClose,
  onUpdated,
}: {
  initial: Outing;
  user: User;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [outing, setOuting] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [fullRoute, setFullRoute] = useState(true);
  const [leader, setLeader] = useState(initial.leader_id);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [correctionId, setCorrectionId] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const lock = useRef(false);
  const live = useRef(true);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  const me = outing.participants.find(
    (participant) => participant.user_id === user.id,
  );
  const [clock, setClock] = useState(Date.now);
  useEffect(() => {
    const boundaries = [
      Date.parse(outing.starts_at),
      Date.parse(outing.ends_at),
    ].filter((value) => value > clock);
    if (!boundaries.length) return undefined;
    const timer = window.setTimeout(
      () => setClock(Date.now()),
      Math.min(Math.min(...boundaries) - Date.now() + 50, 2147483647),
    );
    return () => window.clearTimeout(timer);
  }, [outing.starts_at, outing.ends_at, clock]);
  const before = clock < Date.parse(outing.starts_at);
  const ended = clock >= Date.parse(outing.ends_at);
  const active = outing.status !== "cancelled";
  async function action(
    name: string,
    payload: Record<string, unknown>,
    text: string,
  ) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api<Outing>(
        `/daytrip/outings/${encoded(outing.id)}/${name}`,
        "POST",
        { version: outing.version, ...payload },
      );
      if (!live.current) return;
      setOuting(result);
      setLeader(result.leader_id);
      setNotice(text);
      onUpdated();
    } catch (cause) {
      if (live.current) setError(errorMessage(cause));
      if (cause instanceof ApiError && cause.status === 409 && live.current) {
        try {
          const current = await api<Outing>(
            `/daytrip/outings/${encoded(outing.id)}`,
          );
          if (live.current) {
            setOuting(current);
            setLeader(current.leader_id);
          }
        } catch {
          /* Keep the original error; never replay a conflicting change. */
        }
      }
    } finally {
      lock.current = false;
      if (live.current) setBusy(false);
    }
  }
  const providerTargets = outing.participants.filter(
    (person) =>
      person.confirmed_by &&
      !person.revoked &&
      !person.provider_verified &&
      person.user_id !== user.id,
  );
  return (
    <Modal title={outing.title} onClose={onClose} busy={busy}>
      <div className="daytrip-form">
        <p className="daytrip-status">{statusLabel[outing.status]}</p>
        <p>
          {japanDate(outing.starts_at)} 集合
          <br />
          {japanDate(outing.ends_at)} 帰着
        </p>
        <p className="daytrip-route-title">
          {outing.route.origin} → {outing.route.destination}
        </p>
        <RouteFacts route={outing.route} />
        <p className="quiet-note">
          集合地から往復する参考経路です。予約の確定や入金を示す記録ではありません。
        </p>
        <ErrorBox message={error} />
        {notice && <output className="notice">{notice}</output>}
        <section className="daytrip-leader">
          <SealMark className="daytrip-seal" decorative>
            先達
          </SealMark>
          <div>
            <h3>開催の先達（取りまとめ役）</h3>
            <p>
              {outing.participants.find(
                (person) => person.user_id === outing.leader_id,
              )?.name || "未選択"}{" "}
              ·{" "}
              {outing.status === "cancelled"
                ? "開催取消済み"
                : outing.leader_accepted
                  ? "本人承諾済み"
                  : "本人の承諾待ち"}
            </p>
          </div>
        </section>
        {active &&
          before &&
          me &&
          !me.revoked &&
          (!me.accepted ||
            (outing.leader_id === user.id && !outing.leader_accepted)) && (
            <button
              className="button primary full"
              disabled={busy}
              onClick={() =>
                void action(
                  "accept",
                  { accept_leader: outing.leader_id === user.id },
                  "参加の承諾を保存しました。",
                )
              }
            >
              {outing.leader_id === user.id
                ? "参加と開催の先達を承諾"
                : "この開催への参加を承諾"}
            </button>
          )}
        {active && ended && me?.accepted && !me.revoked && !me.claimed && (
          <div className="daytrip-action-box">
            <h3>今回の参加を申告</h3>
            <label className="daytrip-check">
              <input
                type="checkbox"
                checked={fullRoute}
                disabled={busy}
                onChange={(event) => setFullRoute(event.target.checked)}
              />
              集合から帰着まで全行程に参加した
            </label>
            <p className="quiet-note">
              部分参加は参加点のみです。他の参加者が確認するまで加点されません。
            </p>
            <button
              className="button primary full"
              disabled={busy}
              onClick={() =>
                void action(
                  "claim",
                  { full_route: fullRoute },
                  "実参加の申告を保存しました。他の参加者の確認をお待ちください。",
                )
              }
            >
              実参加を申告する
            </button>
          </div>
        )}
        {active && !before && !ended && (
          <p className="hint-box">
            実施と参加の確認は、帰着予定時刻の後に行えます。
          </p>
        )}
        <section>
          <h3>参加者の確認</h3>
          <div className="daytrip-attendees">
            {outing.participants.map((person) => (
              <div key={person.user_id} className="daytrip-attendee">
                <div>
                  <strong>
                    {person.name}
                    {person.user_id === user.id ? "（自分）" : ""}
                  </strong>
                  <small>
                    {outing.status === "cancelled"
                      ? "参加取消済み"
                      : person.revoked
                        ? "実参加を取消済み"
                        : person.confirmed_by
                          ? "他参加者が実施確認済み"
                          : person.claimed
                            ? "実参加の申告済み"
                            : person.accepted
                              ? "参加承諾済み"
                              : "参加承諾待ち"}
                    {person.provider_verified ? " · 事業者の利用確認済み" : ""}
                  </small>
                  {person.points > 0 && (
                    <small className="daytrip-earned">
                      {person.points}点
                      {person.user_id === outing.leader_id &&
                      person.full_route &&
                      outing.leader_accepted
                        ? " · 先達分を含む"
                        : ""}
                    </small>
                  )}
                </div>
                {active &&
                  ended &&
                  me?.claimed &&
                  !me.revoked &&
                  person.claimed &&
                  !person.revoked &&
                  !person.confirmed_by &&
                  person.user_id !== user.id && (
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() =>
                        void action(
                          "confirm",
                          { participant_id: person.user_id },
                          `${person.name}さんの実参加を確認しました。`,
                        )
                      }
                    >
                      実参加を確認
                    </button>
                  )}
              </div>
            ))}
          </div>
          <p className="quiet-note">
            一緒に参加した人だけを確認してください。自分の実参加は自分では確定できません。
          </p>
        </section>
        {active &&
          ended &&
          (outing.can_manage || (me?.claimed && !me.revoked)) && (
            <details className="daytrip-details">
              <summary>実参加の記録を訂正する</summary>
              <p className="quiet-note">
                参加していなかった人の申告と加点を取り消します。その人が確認していた他の参加者は、別の実参加者による再確認が必要です。
              </p>
              <label className="field" htmlFor="outing-correction-person">
                取り消す参加者
                <Choice
                  id="outing-correction-person"
                  value={correctionId}
                  disabled={busy}
                  onChange={(event) => setCorrectionId(event.target.value)}
                >
                  <option value="">参加者を選ぶ</option>
                  {outing.participants
                    .filter(
                      (person) =>
                        !person.revoked &&
                        person.claimed &&
                        (outing.can_manage || person.user_id === user.id),
                    )
                    .map((person) => (
                      <option key={person.user_id} value={person.user_id}>
                        {person.name}
                      </option>
                    ))}
                </Choice>
              </label>
              <label className="field">
                訂正の理由
                <textarea
                  value={correctionReason}
                  onChange={(event) => setCorrectionReason(event.target.value)}
                  maxLength={400}
                  disabled={busy}
                />
              </label>
              <button
                className="button danger-button full"
                disabled={busy || !correctionId || !correctionReason.trim()}
                onClick={() =>
                  void action(
                    `participants/${encoded(correctionId)}/cancel`,
                    { reason: correctionReason.trim() },
                    "実参加の記録を取り消しました。加点と他の参加者の確認状態を更新しました。",
                  )
                }
              >
                実参加を取り消す
              </button>
            </details>
          )}
        {active &&
          outing.is_provider &&
          ended &&
          providerTargets.length > 0 && (
            <div className="daytrip-action-box">
              <h3>事業者の利用確認</h3>
              <p>
                対象：{providerTargets.map((person) => person.name).join("、")}
              </p>
              <p className="quiet-note">
                利用を確認すると、この開催のポイントが金銭特典の資格へ反映されます。入金の記録とは別です。
              </p>
              <button
                className="button primary full"
                disabled={busy}
                onClick={() =>
                  void action(
                    "provider-confirm",
                    {
                      participant_ids: providerTargets.map(
                        (person) => person.user_id,
                      ),
                    },
                    "事業者の利用確認を保存しました。",
                  )
                }
              >
                対象者の利用を確認
              </button>
            </div>
          )}
        {active && outing.can_manage && before && (
          <details className="daytrip-details">
            <summary>開催の先達を交代する</summary>
            <label className="field">
              新しい開催の先達
              <Choice
                value={leader}
                disabled={busy}
                onChange={(event) => setLeader(event.target.value)}
              >
                {outing.participants.map((person) => (
                  <option key={person.user_id} value={person.user_id}>
                    {person.name}
                  </option>
                ))}
              </Choice>
            </label>
            <p className="quiet-note">
              新しい先達に、改めて本人の承諾を依頼します。
            </p>
            <button
              className="button secondary full"
              disabled={busy || leader === outing.leader_id}
              onClick={() =>
                void action(
                  "leader",
                  { leader_id: leader },
                  "先達の交代を保存しました。本人の承諾が必要です。",
                )
              }
            >
              先達を変更する
            </button>
          </details>
        )}
        {active && outing.can_manage && (
          <details
            className="daytrip-details"
            open={cancelling}
            onToggle={(event) => setCancelling(event.currentTarget.open)}
          >
            <summary>開催の中止・実施記録の取消</summary>
            <p className="quiet-note">
              参加者の加点と未利用特典を取り消します。利用済み特典は事業者の調整確認へ進み、履歴は残ります。
            </p>
            <label className="field">
              理由
              <textarea
                value={cancelReason}
                onChange={(event) => setCancelReason(event.target.value)}
                maxLength={400}
                disabled={busy}
              />
            </label>
            <button
              className="button danger-button full"
              disabled={busy || !cancelReason.trim()}
              onClick={() =>
                void action(
                  "cancel",
                  { reason: cancelReason.trim() },
                  "開催を取り消しました。加点・特典の状態を更新しました。",
                )
              }
            >
              理由を保存して取り消す
            </button>
          </details>
        )}
      </div>
    </Modal>
  );
}

function OutingRow({ outing, onOpen }: { outing: Outing; onOpen: () => void }) {
  return (
    <button className="daytrip-outing-row" onClick={onOpen}>
      <span className="outing-date">
        <strong>
          {new Intl.DateTimeFormat("ja-JP", {
            month: "numeric",
            day: "numeric",
            timeZone: "Asia/Tokyo",
          }).format(new Date(outing.starts_at))}
        </strong>
        <small>{statusLabel[outing.status]}</small>
      </span>
      <span>
        <strong>{outing.title}</strong>
        <small>
          {outing.route.origin}発 · {outing.participants.length}人 · 日帰り
        </small>
      </span>
      <Icon name="arrow" />
    </button>
  );
}

function RedemptionList({
  items,
  benefits,
  outings,
  provider,
  busy,
  onAction,
}: {
  items: Redemption[];
  benefits: Benefit[];
  outings: Outing[];
  provider?: boolean;
  busy: boolean;
  onAction: (item: Redemption, action: "cancel" | "redeem") => void;
}) {
  if (!items.length) return null;
  return (
    <section className="daytrip-redemptions">
      <h3>{provider ? "割引の確保・利用" : "確保した特典"}</h3>
      {items.map((item) => (
        <article key={item.id} className="daytrip-benefit">
          <span className="daytrip-status">
            {item.status === "reserved"
              ? "確保済み"
              : item.status === "redeemed"
                ? "利用記録済み"
                : "取消済み"}
          </span>
          <h3>
            {benefits.find((benefit) => benefit.id === item.benefit_id)
              ?.title || "階級に応じた特典"}
          </h3>
          <p>
            {outings.find((outing) => outing.id === item.outing_id)?.title ||
              "対象の開催"}
          </p>
          <dl className="daytrip-totals">
            <div>
              <dt>通常額</dt>
              <dd>{yen(item.original_yen)}</dd>
            </div>
            <div>
              <dt>割引</dt>
              <dd>−{yen(item.discount_yen)}</dd>
            </div>
            <div>
              <dt>適用後</dt>
              <dd>{yen(item.total_yen)}</dd>
            </div>
          </dl>
          <p className="quiet-note">
            一人分の対象プラン料金。予約・入金の確定ではありません。
          </p>
          {item.adjustment_required && (
            <p className="hint-box">
              実績の訂正があります。事業者による金額の調整確認が必要です。
            </p>
          )}
          {item.status === "reserved" && (
            <div className="daytrip-actions">
              {provider && (
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={() => onAction(item, "redeem")}
                >
                  利用を記録
                </button>
              )}
              <button
                className="text-button"
                disabled={busy}
                onClick={() => onAction(item, "cancel")}
              >
                確保を取り消す
              </button>
            </div>
          )}
        </article>
      ))}
    </section>
  );
}

export default function Daytrip({
  user,
  initialCircleId,
  onOpenCircle,
  onFindCircles,
  onExplore,
}: {
  user: User;
  initialCircleId: string;
  onOpenCircle: (id: string) => void;
  onFindCircles: () => void;
  onExplore: () => void;
}) {
  const [tab, setTab] = useState<
    "explore" | "programs" | "outings" | "journal" | "coupons"
  >("explore");
  const [catalog, setCatalog] = useState<DaytripCatalog | null>(null);
  const [me, setMe] = useState<DaytripMe | null>(null);
  const [circles, setCircles] = useState<CircleSummary[]>([]);
  const [outings, setOutings] = useState<Outing[]>([]);
  const [origin, setOrigin] = useState("");
  const [zone, setZone] = useState("target");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [chosenRoute, setChosenRoute] = useState<Route | null>(null);
  const [programStep, setProgramStep] = useState<ProgramStep | null>(null);
  const [selected, setSelected] = useState<Outing | null>(null);
  const [benefit, setBenefit] = useState<Benefit | null>(null);
  const [benefitRoute, setBenefitRoute] = useState<Route | null>(null);
  const [benefitOuting, setBenefitOuting] = useState("");
  const [reservationAt, setReservationAt] = useState(0);
  const [loadedRevision, setLoadedRevision] = useState(-1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  const loading = loadedRevision !== revision;
  const live = useRef(true);
  const lock = useRef(false);
  const reserveId = useRef(crypto.randomUUID());
  const pageStart = useRef<HTMLElement>(null);
  const pageTitle = useRef<HTMLHeadingElement>(null);
  const personalReview = me?.rank_status.next_demotion_at;
  const eligibleReview = me?.eligible_rank_status.next_demotion_at;
  const nextReview =
    personalReview && eligibleReview
      ? personalReview < eligibleReview
        ? personalReview
        : eligibleReview
      : personalReview || eligibleReview;
  const evaluatedAt = me?.rank_status.evaluated_at;
  useEffect(() => {
    if (!nextReview || !evaluatedAt) return undefined;
    // Server timestamps schedule a refresh; the browser never awards a rank.
    const delay = Math.min(
      2147483647,
      Math.max(1000, Date.parse(nextReview) - Date.parse(evaluatedAt) + 1000),
    );
    const timer = window.setTimeout(
      () => setRevision((value) => value + 1),
      delay,
    );
    return () => window.clearTimeout(timer);
  }, [nextReview, evaluatedAt]);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    void Promise.all([
      api<DaytripCatalog>("/daytrip/catalog"),
      api<DaytripMe>("/daytrip/me"),
      api<CircleList>("/circles"),
    ])
      .then(async ([routes, personal, list]) => {
        const openCircles = list.items.filter((item) => item.status === "open");
        const records = await Promise.all(
          openCircles.map((item) =>
            api<{ items: Outing[] }>(`/circles/${encoded(item.id)}/outings`),
          ),
        );
        if (!active) return undefined;
        setCatalog(routes);
        setMe(personal);
        setCircles(openCircles);
        setOutings(records.flatMap((record) => record.items));
        setOrigin((current) =>
          routes.routes.some((route) => route.origin === current)
            ? current
            : routes.routes[0]?.origin || "",
        );
        return undefined;
      })
      .catch((cause: unknown) => {
        if (active) setError(errorMessage(cause));
      })
      .finally(() => {
        if (active) setLoadedRevision(revision);
      });
    return () => {
      active = false;
    };
  }, [revision]);
  async function mutate(path: string, data: unknown, message: string) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api(path, "POST", data);
      if (live.current) {
        setBenefit(null);
        setNotice(message);
        setRevision((value) => value + 1);
      }
    } catch (cause) {
      if (live.current) setError(errorMessage(cause));
    } finally {
      lock.current = false;
      if (live.current) setBusy(false);
    }
  }
  const matchingRoutes =
    catalog?.routes.filter(
      (route) =>
        route.origin === origin && (zone === "all" || route.zone === zone),
    ) || [];
  const routes = [
    ...matchingRoutes.filter((route) => route.experience_title),
    ...matchingRoutes.filter((route) => !route.experience_title),
  ];
  const origins = [
    ...new Set(catalog?.routes.map((route) => route.origin) || []),
  ];
  const reservableOutings = benefit
    ? outings.filter((outing) => {
        const day = new Intl.DateTimeFormat("sv-SE", {
          timeZone: "Asia/Tokyo",
        }).format(new Date(outing.starts_at));
        return (
          outing.plan_id === benefit.plan_id &&
          outing.status === "scheduled" &&
          Date.parse(outing.starts_at) > reservationAt &&
          day >= benefit.starts_on &&
          day <= benefit.ends_on &&
          outing.participants.some(
            (person) =>
              person.user_id === user.id && person.accepted && !person.revoked,
          ) &&
          !me?.redemptions.some((item) => item.outing_id === outing.id)
        );
      })
    : [];
  function openTab(next: typeof tab, focusTitle = true) {
    setTab(next);
    pageStart.current?.scrollIntoView({ block: "start", behavior: "auto" });
    if (focusTitle) pageTitle.current?.focus({ preventScroll: true });
  }
  const refresh = () => {
    setError("");
    setRevision((value) => value + 1);
  };
  return (
    <section className="daytrip-page" ref={pageStart}>
      <header className="daytrip-heading">
        <ScrollHeading>
          <h1 className="wa-title-script" ref={pageTitle} tabIndex={-1}>
            {tab === "explore"
              ? "日帰りを探す"
              : tab === "programs"
                ? "通う旅"
                : tab === "outings"
                  ? "講の開催"
                  : tab === "coupons"
                    ? "クーポン"
                    : "旅の手帳"}
          </h1>
        </ScrollHeading>
        <button
          className="daytrip-rank-link"
          onClick={() => openTab("journal")}
          aria-label="旅の手帳と階級を開く"
        >
          <SealMark className="daytrip-seal">
            {me ? rankLabel(me.rank) : "手帳"}
          </SealMark>
          <small>{me ? `${me.points}点` : loading ? "確認中" : "未取得"}</small>
        </button>
      </header>
      <fieldset className="daytrip-tabs" aria-label="日帰りのメニュー">
        {(
          [
            ["explore", "日帰り"],
            ["programs", "通う旅"],
            ["outings", "開催"],
            ["journal", "手帳"],
            ["coupons", "クーポン"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            aria-pressed={tab === value}
            className={tab === value ? "selected" : ""}
            onClick={() => {
              if (value === "coupons") setBenefitRoute(null);
              openTab(value, false);
            }}
          >
            {label}
          </button>
        ))}
      </fieldset>
      <ErrorBox message={error} />
      {error && (
        <button className="text-button" disabled={loading} onClick={refresh}>
          読み込み直す
        </button>
      )}
      {notice && <output className="notice">{notice}</output>}
      {loading && !catalog && (
        <output className="loading-inline">
          日帰りの行き先を確認しています…
        </output>
      )}
      {catalog && tab === "explore" && (
        <>
          <button
            className="daytrip-condition-summary"
            onClick={() => setFiltersOpen(true)}
            aria-label={`日帰りの条件を変更。${origin}発、${zone === "target" ? "片道20〜40km" : zone === "nearby" ? "片道20km未満" : "すべての距離"}`}
          >
            <Icon name="compass" />
            <span>
              {origin}発 <span aria-hidden="true">·</span>{" "}
              {zone === "target"
                ? "片道20〜40km"
                : zone === "nearby"
                  ? "片道20km未満"
                  : "すべての距離"}
            </span>
            <Icon name="filter" />
          </button>
          <div className="daytrip-route-list">
            {routes.map((route, index) => (
              <article className="daytrip-route-card" key={route.id}>
                <div className="daytrip-route-photo">
                  <DaytripCover route={route} priority={index === 0} />
                  <span className="daytrip-photo-caption">イメージ</span>
                  <span className="daytrip-route-tag">
                    {zoneLabel[route.zone]}
                  </span>
                </div>
                <div className="daytrip-route-content">
                  <p className="small-label">{route.destination} · 日帰り</p>
                  <h2>{route.experience_title || route.destination}</h2>
                  <RouteFacts route={route} />
                  <p className="daytrip-distance-note">
                    距離・時間は参考値。現地の移動は別に確認。
                  </p>
                  <button
                    className="button primary full"
                    onClick={() => {
                      if (circles.length) {
                        setProgramStep(null);
                        setChosenRoute(route);
                      } else onFindCircles();
                    }}
                  >
                    {circles.length
                      ? "この行き先で開催をつくる"
                      : "一緒に出かける講を選ぶ"}
                    <Icon name="arrow" />
                  </button>
                  <button
                    className="daytrip-coupon-link"
                    onClick={() => {
                      setBenefitRoute(route);
                      openTab("coupons");
                    }}
                  >
                    <span>この場所のクーポン</span>
                    <strong>
                      {
                        benefitsForRoute(me?.benefits || [], route, catalog)
                          .length
                      }
                      件
                    </strong>
                    <Icon name="arrow" />
                  </button>
                  <details className="daytrip-source">
                    <summary>体験・経路の詳細</summary>
                    {route.summary && (
                      <p className="daytrip-experience-summary">
                        {route.summary}
                      </p>
                    )}
                    <p>{route.distance_note}</p>
                    <p>
                      {route.checked_on}条件更新 · 実測GPS距離ではありません。
                      当日の運行と集合場所を確認してください。
                    </p>
                    {route.source_url.startsWith("https://") && (
                      <a
                        href={route.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        経路の情報元を開く
                      </a>
                    )}
                    {route.time_source_url?.startsWith("https://") && (
                      <a
                        href={route.time_source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        所要時間の情報元を開く
                      </a>
                    )}
                  </details>
                </div>
              </article>
            ))}
          </div>
          {!routes.length && (
            <Empty title="この範囲の経路はありません">
              <p>出発拠点や距離の範囲を変更してください。</p>
            </Empty>
          )}
          <button
            className="text-button daytrip-other-plans"
            onClick={onExplore}
          >
            宿泊も含めて事業者のプランを見る
            <Icon name="arrow" />
          </button>
        </>
      )}
      {tab === "programs" && catalog && (
        <Suspense
          fallback={
            <output className="loading-inline">通う旅をひらいています…</output>
          }
        >
          <JourneyPrograms
            key={`${user.id}-${revision}`}
            onOpenOuting={setSelected}
            onFindCircles={onFindCircles}
            onCreateStep={(step) => {
              const route = catalog.routes.find(
                (item) => item.id === step.route_id,
              );
              if (route && circles.length) {
                setProgramStep(step);
                setChosenRoute(route);
              } else if (!circles.length) onFindCircles();
              else
                setError(
                  "この回の経路を確認できません。一覧を更新してください。",
                );
            }}
          />
        </Suspense>
      )}
      {filtersOpen && (
        <Modal title="日帰りの条件" onClose={() => setFiltersOpen(false)}>
          <div className="daytrip-form">
            <label className="field daytrip-origin">
              出発・集合の拠点
              <Choice
                value={origin}
                onChange={(event) => setOrigin(event.target.value)}
              >
                {origins.map((item) => (
                  <option value={item} key={item}>
                    {item}
                  </option>
                ))}
              </Choice>
            </label>
            <fieldset className="daytrip-filter" aria-label="片道の距離">
              {[
                ["target", "20〜40km"],
                ["nearby", "20km未満"],
                ["all", "すべて"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  className={zone === value ? "selected" : ""}
                  aria-pressed={zone === value}
                  onClick={() => setZone(value)}
                >
                  {label}
                </button>
              ))}
            </fieldset>
            <p className="quiet-note">
              同じ日に帰る旅を探します。距離と時間は発地からの参考条件です。待ち時間や現地での移動を含めて、当日の行程を確認してください。
            </p>
            <button
              className="button primary full"
              onClick={() => setFiltersOpen(false)}
            >
              この条件で見る
            </button>
          </div>
        </Modal>
      )}
      {tab === "outings" && (
        <>
          <div className="section-title">
            <h2>開催と実施の記録</h2>
            <button
              className="text-button"
              disabled={loading}
              onClick={refresh}
            >
              <Icon name="refresh" />
              更新
            </button>
          </div>
          <p className="quiet-note">
            参加承諾 → 実参加の申告 →
            他参加者の確認。事業者の利用確認は別に記録します。
          </p>
          {outings.length ? (
            <div className="daytrip-outing-list">
              {outings.map((outing) => (
                <OutingRow
                  key={outing.id}
                  outing={outing}
                  onOpen={() => setSelected(outing)}
                />
              ))}
            </div>
          ) : (
            <Empty title="開催はまだありません">
              <p>講の仲間と出かける日帰りを選びましょう。</p>
              <button
                className="button primary"
                onClick={() => openTab("explore")}
              >
                日帰りの行き先を見る
              </button>
            </Empty>
          )}
        </>
      )}
      {tab === "journal" && me && (
        <>
          <section className="daytrip-passbook">
            <div className="passbook-inscription">
              <div className="passbook-title">
                <TravelCrest />
                <span>講の旅帳</span>
              </div>
              <WoodcutArt />
            </div>
            <div className="passbook-rank">
              <SealMark className="daytrip-seal large">
                {rankLabel(me.rank)}
              </SealMark>
              <div>
                <p className="small-label">{user.name}さんの旅の階級</p>
                <h2 className="rank-current-name wa-title-script">
                  {me.rank_status.name}
                </h2>
                <p className="passbook-points">
                  {me.points.toLocaleString()}
                  <span>累積点</span>
                </p>
              </div>
            </div>
            <div className="passbook-stats">
              <div>
                <strong>{me.completed_count}</strong>
                <span>確認済みの開催</span>
              </div>
              <div>
                <strong>{me.leader_count}</strong>
                <span>開催の先達を務めた回数</span>
              </div>
            </div>
            <RankProgress status={me.rank_status} />
            <hr />
            <p>
              <strong>特典対象の階級：{rankLabel(me.eligible_rank)}</strong>
            </p>
            <p className="quiet-note">
              事業者の利用確認がある累積
              {me.eligible_points.toLocaleString("ja-JP")}
              点が対象です。仲間の確認だけの点は特典資格に含めません。
            </p>
            {sameRankProgress(me.rank_status, me.eligible_rank_status) ? (
              <p className="quiet-note">
                昇格・維持の見通しは、上の旅の階級と同じです。
              </p>
            ) : (
              <RankProgress status={me.eligible_rank_status} />
            )}
            <button
              className="button secondary full"
              onClick={() => {
                setBenefitRoute(null);
                openTab("coupons");
              }}
            >
              階級別のクーポンを見る
              <Icon name="arrow" />
            </button>
            <button
              className="text-button"
              disabled={loading}
              onClick={refresh}
            >
              <Icon name="refresh" />
              階級を更新
            </button>
          </section>
          {catalog ? (
            <RankBoard rules={catalog.rules} current={me.rank} />
          ) : null}
          <details className="daytrip-details">
            <summary>加点のしくみ</summary>
            <p>
              確認済みの参加 {catalog?.rules.base_points}
              点＋往復経路10kmあたり1点（最大
              {Math.floor((catalog?.rules.distance_cap_km || 200) / 10)}
              点）＋開催の先達 {catalog?.rules.leader_points}点。
            </p>
            <p className="quiet-note">
              一人一日一開催が対象。部分参加や距離未確認は参加点のみ。提案・写真・候補保存では加点しません。規則{" "}
              {catalog?.rules.version}
            </p>
          </details>
          <section className="daytrip-ledger">
            <h2>獲得・訂正の内訳</h2>
            {me.ledger.length ? (
              me.ledger.map((entry) => (
                <div key={entry.id} className="ledger-row">
                  <SealMark className="ledger-stamp">
                    {entry.kind === "reverse"
                      ? "取消"
                      : entry.kind === "verify"
                        ? "利用"
                        : "参加"}
                  </SealMark>
                  <span>
                    <strong>{entry.reason}</strong>
                    <small>
                      {new Intl.DateTimeFormat("ja-JP", {
                        dateStyle: "medium",
                        timeZone: "Asia/Tokyo",
                      }).format(new Date(entry.created_at))}
                    </small>
                  </span>
                  <b>
                    {entry.points > 0 ? "+" : ""}
                    {entry.points}点
                  </b>
                </div>
              ))
            ) : (
              <p className="quiet-note">
                確認済みの開催から記録されます。過去の写真や訪問記録から自動で加点されることはありません。
              </p>
            )}
          </section>
        </>
      )}
      {tab === "coupons" && me && catalog && (
        <>
          <DaytripBenefits
            key={benefitRoute?.id || "all"}
            benefits={me.benefits}
            catalog={catalog}
            route={benefitRoute}
            eligibleRank={me.eligible_rank}
            eligiblePoints={me.eligible_points}
            busy={busy}
            onClearRoute={() => setBenefitRoute(null)}
            onExplore={() => openTab("explore")}
            onSelect={(item) => {
              setBenefit(item);
              setBenefitOuting("");
              setReservationAt(Date.now());
              reserveId.current = crypto.randomUUID();
            }}
          />
          <RedemptionList
            items={me.redemptions}
            benefits={me.benefits}
            outings={outings}
            busy={busy}
            onAction={(item) =>
              void mutate(
                `/daytrip/redemptions/${encoded(item.id)}/cancel`,
                { version: item.version },
                "特典の確保を取り消しました。",
              )
            }
          />
        </>
      )}
      {chosenRoute && catalog && (
        <CreateOuting
          route={chosenRoute}
          catalog={catalog}
          requiredPlan={
            programStep
              ? { id: programStep.plan_id, title: programStep.plan_title }
              : undefined
          }
          circles={circles}
          initialCircleId={
            circles.some((circle) => circle.id === initialCircleId)
              ? initialCircleId
              : circles.length === 1
                ? circles[0].id
                : ""
          }
          onClose={() => {
            setChosenRoute(null);
            setProgramStep(null);
          }}
          onOpenCircle={onOpenCircle}
          onCreated={(outing) => {
            setChosenRoute(null);
            setSelected(outing);
            if (programStep) {
              openTab("programs");
              setNotice(
                "開催を作成しました。参加承諾後、通う旅の該当する回でこの開催を選んでください。",
              );
            } else openTab("outings");
            setProgramStep(null);
            refresh();
          }}
        />
      )}
      {selected && (
        <OutingDetail
          initial={selected}
          user={user}
          onClose={() => setSelected(null)}
          onUpdated={refresh}
        />
      )}
      {benefit && (
        <Modal
          title="クーポンを使う開催"
          onClose={() => setBenefit(null)}
          busy={busy}
        >
          <div className="daytrip-form">
            <BenefitLocation benefit={benefit} />
            <h3>{benefit.title}</h3>
            <BenefitTerms benefit={benefit} />
            <ErrorBox message={error} />
            {reservableOutings.length > 0 ? (
              <label className="field" htmlFor="coupon-outing">
                対象プランを利用する開催
                <Choice
                  id="coupon-outing"
                  value={benefitOuting}
                  disabled={busy}
                  onChange={(event) => setBenefitOuting(event.target.value)}
                >
                  <option value="">開催を選ぶ</option>
                  {reservableOutings.map((outing) => (
                    <option key={outing.id} value={outing.id}>
                      {outing.title} · {japanDate(outing.starts_at)}
                    </option>
                  ))}
                </Choice>
              </label>
            ) : (
              <div className="coupon-empty-outing">
                <h4>対象の開催がありません</h4>
                <p>
                  講で対象プランを決め、事業者の招待承諾後に開催を作って参加承諾してください。対象期間内で、まだ始まっていない開催を選べます。
                </p>
                <button
                  className="button secondary full"
                  disabled={busy}
                  onClick={() => {
                    setBenefit(null);
                    onFindCircles();
                  }}
                >
                  講でプランを相談する
                  <Icon name="arrow" />
                </button>
              </div>
            )}
            <p className="quiet-note">
              対象プランの開催に本人が参加承諾済みであることが必要です。本人一人分の料金に適用し、講全員への適用は行いません。
            </p>
            <button
              className="button primary full"
              disabled={
                busy ||
                benefit.zone_offer?.can_reserve === false ||
                !reservableOutings.some((outing) => outing.id === benefitOuting)
              }
              onClick={() =>
                void mutate(
                  `/daytrip/benefits/${encoded(benefit.id)}/reserve`,
                  {
                    outing_id: benefitOuting,
                    client_request_id: reserveId.current,
                  },
                  "特典を確保しました。通常額・割引額・適用後の金額を確認できます。",
                )
              }
            >
              条件を確認してクーポンを確保
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}

export function ProviderDaytrip({ user }: { user: User }) {
  const [data, setData] = useState<DaytripProviderData | null>(null);
  const [catalog, setCatalog] = useState<DaytripCatalog | null>(null);
  const [tab, setTab] = useState<"outings" | "benefits" | "routes">("outings");
  const [selected, setSelected] = useState<Outing | null>(null);
  const [editing, setEditing] = useState(false);
  const [planId, setPlanId] = useState("");
  const [routeId, setRouteId] = useState("");
  const [title, setTitle] = useState("");
  const [minRank, setMinRank] = useState("1");
  const [discountType, setDiscountType] = useState("amount");
  const [discountValue, setDiscountValue] = useState("300");
  const [maxDiscount, setMaxDiscount] = useState("500");
  const [maxRedemptions, setMaxRedemptions] = useState("20");
  const [start, setStart] = useState(localDate);
  const [end, setEnd] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loadedRevision, setLoadedRevision] = useState(-1);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  const loading = loadedRevision !== revision;
  const lock = useRef(false);
  const live = useRef(true);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    void Promise.all([
      api<DaytripProviderData>("/daytrip/provider"),
      api<DaytripCatalog>("/daytrip/catalog"),
    ])
      .then(([result, routes]) => {
        if (active) {
          setData(result);
          setCatalog(routes);
        }
        return undefined;
      })
      .catch((cause: unknown) => {
        if (active) setError(errorMessage(cause));
      })
      .finally(() => {
        if (active) setLoadedRevision(revision);
      });
    return () => {
      active = false;
    };
  }, [revision]);
  async function mutate(
    path: string,
    method: string,
    payload: unknown,
    message: string,
  ) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api(path, method, payload);
      if (live.current) {
        setEditing(false);
        setNotice(message);
        setRevision((value) => value + 1);
      }
    } catch (cause) {
      if (live.current) setError(errorMessage(cause));
    } finally {
      lock.current = false;
      if (live.current) setBusy(false);
    }
  }
  const dayPlans = data?.plans.filter((plan) => plan.nights === 0) || [];
  const benefitPlans = dayPlans.filter(
    (plan) => plan.status === "published" && plan.price_basis === "per_person",
  );
  const selectedPlan = benefitPlans.find((plan) => plan.id === planId);
  const previewDiscount = selectedPlan
    ? Math.min(
        selectedPlan.price_yen,
        Number(maxDiscount),
        discountType === "percent"
          ? Math.floor((selectedPlan.price_yen * Number(discountValue)) / 100)
          : Number(discountValue),
      )
    : 0;
  const valid =
    !!selectedPlan &&
    !!title.trim() &&
    Number(discountValue) > 0 &&
    (discountType !== "percent" || Number(discountValue) <= 100) &&
    Number(maxDiscount) > 0 &&
    Number(maxRedemptions) > 0 &&
    !!start &&
    !!end &&
    end >= start &&
    consent;
  return (
    <section className="provider-daytrip">
      <fieldset className="daytrip-tabs" aria-label="日帰りの管理">
        {(
          [
            ["outings", "実施確認"],
            ["benefits", "階級特典"],
            ["routes", "集合と経路"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            className={tab === value ? "selected" : ""}
            aria-pressed={tab === value}
            onClick={() => {
              setTab(value);
              setPlanId("");
            }}
          >
            {label}
          </button>
        ))}
      </fieldset>
      <ErrorBox message={error} />
      {notice && <output className="notice">{notice}</output>}
      <div className="daytrip-update">
        <button
          className="text-button"
          disabled={loading || busy}
          onClick={() => setRevision((value) => value + 1)}
        >
          <Icon name="refresh" />
          更新
        </button>
      </div>
      {loading && !data && <output>開催と特典を確認しています…</output>}
      {data && tab === "outings" && (
        <>
          <p className="quiet-note">
            自社のプランを使う開催です。参加者同士の実施確認後、利用を確認してください。
          </p>
          {data.outings.length ? (
            <div className="daytrip-outing-list">
              {data.outings.map((outing) => (
                <OutingRow
                  key={outing.id}
                  outing={outing}
                  onOpen={() => setSelected(outing)}
                />
              ))}
            </div>
          ) : (
            <div className="daytrip-empty-scroll">
              <TravelCrest />
              <div>
                <h3>確認する開催はありません</h3>
                <p>
                  参加を承諾した講が日帰りの開催を登録すると、ここに届きます。
                </p>
              </div>
            </div>
          )}
          <RedemptionList
            items={data.redemptions}
            benefits={data.benefits}
            outings={data.outings}
            provider
            busy={busy}
            onAction={(item, action) =>
              void mutate(
                `/daytrip/redemptions/${encoded(item.id)}/${action}`,
                "POST",
                { version: item.version },
                action === "redeem"
                  ? "割引の利用を記録しました。"
                  : "特典の確保を取り消しました。",
              )
            }
          />
        </>
      )}
      {data && tab === "benefits" && (
        <>
          <div className="section-title">
            <h2>自社の階級特典</h2>
            <button
              className="button primary"
              disabled={busy || !benefitPlans.length}
              onClick={() => {
                setEditing(true);
                setPlanId(benefitPlans[0]?.id || "");
                setConsent(false);
                setTitle("");
                setError("");
              }}
            >
              <Icon name="plus" />
              特典をつくる
            </button>
          </div>
          <p className="quiet-note">
            公開済み・日帰り・一人料金のプランが対象です。割引の負担と条件を確認して公開します。
          </p>
          {!data.benefits.length && (
            <Empty title="公開した特典はありません">
              <p>自社の条件で特典を設定できます。</p>
            </Empty>
          )}
          {data.benefits.map((item) => (
            <article className="daytrip-benefit" key={item.id}>
              <span className="daytrip-status">
                {item.status === "active" || item.status === "published"
                  ? "公開中"
                  : "公開終了"}
              </span>
              <h3>{item.title}</h3>
              <p className="quiet-note">
                {data.plans.find((plan) => plan.id === item.plan_id)?.title}
              </p>
              <BenefitTerms benefit={item} />
              <p className="quiet-note">最大{item.max_redemptions}件</p>
              <Suspense fallback={<output>割引予算をひらいています…</output>}>
                <BenefitZonePolicy
                  key={`${item.id}-${item.version}`}
                  benefit={item}
                  disabled={busy || loading}
                  onSaved={() => {
                    setNotice("追加率と割引予算を保存しました。");
                    setRevision((value) => value + 1);
                  }}
                  onRefresh={() => setRevision((value) => value + 1)}
                />
              </Suspense>
              {["active", "published"].includes(item.status) && (
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() =>
                    void mutate(
                      `/daytrip/benefits/${encoded(item.id)}/close`,
                      "POST",
                      { version: item.version },
                      "特典の公開を終了しました。",
                    )
                  }
                >
                  公開を終了する
                </button>
              )}
            </article>
          ))}
        </>
      )}
      {data && catalog && tab === "routes" && (
        <div className="daytrip-form">
          <h2>日帰りプランの経路</h2>
          <p className="quiet-note">
            集合地点から目的地への参考経路を設定します。本人の自宅住所は使いません。
          </p>
          <label className="field">
            自社の日帰りプラン
            <Choice
              value={planId}
              disabled={busy}
              onChange={(event) => {
                setPlanId(event.target.value);
                setRouteId(
                  data.links.find((link) => link.plan_id === event.target.value)
                    ?.route_id || "",
                );
              }}
            >
              <option value="">プランを選ぶ</option>
              {dayPlans.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.title}
                </option>
              ))}
            </Choice>
          </label>
          <label className="field">
            集合と目的地
            <Choice
              value={routeId}
              disabled={busy}
              onChange={(event) => setRouteId(event.target.value)}
            >
              <option value="">経路を選ぶ</option>
              {catalog.routes.map((route) => (
                <option key={route.id} value={route.id}>
                  {route.origin} → {route.destination}
                </option>
              ))}
            </Choice>
          </label>
          {catalog.routes.find((route) => route.id === routeId) && (
            <RouteFacts
              route={catalog.routes.find((route) => route.id === routeId)!}
            />
          )}
          <button
            className="button primary full"
            disabled={busy || !planId || !routeId}
            onClick={() =>
              void mutate(
                `/daytrip/plan-routes/${encoded(planId)}`,
                "PUT",
                { route_id: routeId },
                "プランの経路を保存しました。",
              )
            }
          >
            この経路を設定する
          </button>
        </div>
      )}
      {selected && (
        <OutingDetail
          initial={selected}
          user={user}
          onClose={() => setSelected(null)}
          onUpdated={() => setRevision((value) => value + 1)}
        />
      )}
      {editing && (
        <Modal
          title="階級特典を公開する"
          onClose={() => setEditing(false)}
          busy={busy}
        >
          <div className="daytrip-form">
            <ErrorBox message={error} />
            <fieldset disabled={busy}>
              <label className="field">
                対象プラン
                <Choice
                  value={planId}
                  onChange={(event) => setPlanId(event.target.value)}
                >
                  {benefitPlans.map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.title}
                    </option>
                  ))}
                </Choice>
              </label>
              <label className="field">
                特典の名前
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  maxLength={120}
                  placeholder="例：日帰り体験の参加割引"
                />
              </label>
              <label className="field" htmlFor="benefit-min-rank">
                対象となる特典階級
                <Choice
                  id="benefit-min-rank"
                  value={minRank}
                  onChange={(event) => setMinRank(event.target.value)}
                >
                  {RANK_NAMES.map((_, index) => index + 1).map((rank) => (
                    <option key={rank} value={rank}>
                      {rankLabel(rank)}から
                    </option>
                  ))}
                </Choice>
              </label>
              <div className="field-row">
                <label className="field" htmlFor="benefit-discount-type">
                  割引方法
                  <Choice
                    id="benefit-discount-type"
                    value={discountType}
                    onChange={(event) => setDiscountType(event.target.value)}
                  >
                    <option value="amount">金額（円）</option>
                    <option value="percent">割合（%）</option>
                  </Choice>
                </label>
                <label className="field">
                  割引{discountType === "percent" ? "率（%）" : "額（円）"}
                  <input
                    type="number"
                    min={1}
                    max={discountType === "percent" ? 100 : 1000000}
                    value={discountValue}
                    onChange={(event) => setDiscountValue(event.target.value)}
                  />
                </label>
              </div>
              <div className="field-row">
                <label className="field">
                  一人の割引上限（円）
                  <input
                    type="number"
                    min={1}
                    value={maxDiscount}
                    onChange={(event) => setMaxDiscount(event.target.value)}
                  />
                </label>
                <label className="field">
                  利用の上限件数
                  <input
                    type="number"
                    min={1}
                    max={10000}
                    value={maxRedemptions}
                    onChange={(event) => setMaxRedemptions(event.target.value)}
                  />
                </label>
              </div>
              <div className="field-row">
                <label className="field">
                  利用開始日
                  <input
                    type="date"
                    value={start}
                    onChange={(event) => setStart(event.target.value)}
                  />
                </label>
                <label className="field">
                  利用終了日
                  <input
                    type="date"
                    value={end}
                    min={start}
                    onChange={(event) => setEnd(event.target.value)}
                  />
                </label>
              </div>
              <div className="daytrip-cost-preview">
                <strong>一人分の確認</strong>
                <p>
                  {yen(selectedPlan?.price_yen || 0)} −{" "}
                  {yen(Number.isFinite(previewDiscount) ? previewDiscount : 0)}{" "}
                  ={" "}
                  {yen(
                    Math.max(
                      0,
                      (selectedPlan?.price_yen || 0) -
                        (Number.isFinite(previewDiscount)
                          ? previewDiscount
                          : 0),
                    ),
                  )}
                </p>
                <small>対象プラン料金に適用・円未満切捨て</small>
              </div>
              <label className="daytrip-check">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                />
                <span>
                  自社で割引を負担し、他特典との併用を認めない条件で公開する
                </span>
              </label>
            </fieldset>
            <button
              className="button primary full"
              disabled={busy || !valid}
              onClick={() =>
                void mutate(
                  "/daytrip/benefits",
                  "POST",
                  {
                    plan_id: planId,
                    title: title.trim(),
                    min_rank: Number(minRank),
                    rank_policy_version: "R2",
                    discount_type: discountType,
                    discount_value: Number(discountValue),
                    max_discount_yen: Number(maxDiscount),
                    max_redemptions: Number(maxRedemptions),
                    starts_on: start,
                    ends_on: end,
                  },
                  "条件を保存して特典を公開しました。",
                )
              }
            >
              条件と負担を確認して公開
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}
