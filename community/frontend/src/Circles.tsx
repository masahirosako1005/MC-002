import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api } from "./api";
import Choice from "./Choice";
import { Avatar, Empty, ErrorBox, Icon, Modal, TagPicker, Tags } from "./ui";
import {
  Conversation,
  periods,
  PlanDetail,
  RequirementsSummary,
  scopeLabel,
  useRequestKey,
} from "./marketplace-ui";
import { emptyRequirements, RequirementEditor } from "./Marketplace";
import type { Community, Tag, User } from "./types";
import type {
  ItineraryItem,
  MarketMessage,
  ProviderPlan,
  Requirements,
} from "./marketplace-types";
import type {
  AssistantTurn,
  CircleCandidates,
  CircleDetail,
  CircleInvitation,
  CircleList,
  CircleProposal,
  CircleRoom,
  ProviderInvitation,
} from "./circle-types";
import "./circles.css";
import PlanDiscovery, { SavedCandidateList } from "./PlanDiscovery";
import type { CandidateCard } from "./PlanDiscovery";
const ReflectionWorkspace = lazy(() => import("./ReflectionWorkspace"));
const CircleOccasions = lazy(() =>
  import("./Occasions").then((module) => ({ default: module.CircleOccasions })),
);

function useAlive() {
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  return alive;
}
const statusLabel = (status: string) =>
  ({
    pending: "返事を待っています",
    accepted: "参加済み",
    declined: "見送り",
    cancelled: "取消済み",
    closed: "終了",
  })[status] || status;

function CreateCircle({
  community,
  user,
  tags,
  mode,
  circle,
  onClose,
  onSaved,
}: {
  community: Community;
  user: User;
  tags: Tag[];
  mode: "recommended" | "manual";
  circle?: CircleDetail;
  onClose: () => void;
  onSaved: (circle: CircleDetail) => void;
}) {
  const [title, setTitle] = useState("");
  const [desired, setDesired] = useState(3);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [candidates, setCandidates] = useState<CircleCandidates | null>(null);
  const [people, setPeople] = useState<User[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(mode === "manual");
  const [error, setError] = useState("");
  const alive = useAlive();
  const key = useRequestKey();
  useEffect(() => {
    if (mode !== "manual") return;
    let active = true;
    api<{ items: User[] }>(
      `/journal/people?community_id=${encodeURIComponent(community.id)}`,
    )
      .then((r) => {
        if (active) setPeople(r.items);
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
  }, [community.id, mode]);
  async function findCandidates() {
    setBusy(true);
    setError("");
    setSelected([]);
    setCandidates(null);
    try {
      const result = await api<CircleCandidates>(
        "/circles/candidates",
        "POST",
        {
          community_id: community.id,
          tags: selectedTags,
          desired_count: desired,
        },
      );
      if (alive.current) setCandidates(result);
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  async function save() {
    setBusy(true);
    setError("");
    try {
      const body = circle
        ? { invitee_ids: selected, version: circle.version }
        : {
            community_id: community.id,
            title: title.trim(),
            mode,
            tags: selectedTags,
            desired_count: desired,
            invitee_ids: selected,
          };
      const result = await api<CircleDetail>(
        circle ? `/circles/${circle.id}/invitations` : "/circles",
        "POST",
        { ...body, client_request_id: key(body) },
      );
      if (alive.current) onSaved(result);
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  const options = (
    mode === "recommended"
      ? candidates?.items.map((item) => item.user) || []
      : people
  ).filter(
    (person) =>
      person.id !== user.id &&
      !circle?.members.some((member) => member.id === person.id) &&
      !circle?.invitations.some(
        (invitation) =>
          invitation.invitee.id === person.id &&
          invitation.status === "pending",
      ),
  );
  return (
    <Modal
      title={
        circle
          ? "この講に仲間を招く"
          : mode === "recommended"
            ? "関心から旅仲間を探す"
            : "知っている仲間と講をつくる"
      }
      busy={busy}
      onClose={onClose}
      wide
    >
      <div className="circle-form">
        <p className="muted">
          {community.name}
          の仲間から選びます。招待を受けた本人が返事をするまで、参加は確定しません。
        </p>
        <ErrorBox message={error} />
        {!circle && (
          <>
            <label className="field">
              講の名前
              <input
                value={title}
                maxLength={100}
                disabled={busy}
                placeholder="例：森を歩いて、カフェに寄る休日"
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label className="field">
              一緒に計画したい人数（自分を含む）
              <input
                type="number"
                min={2}
                max={20}
                value={desired}
                disabled={busy}
                onChange={(e) => {
                  setDesired(Number(e.target.value));
                  setCandidates(null);
                  setSelected([]);
                }}
              />
            </label>
          </>
        )}
        {mode === "recommended" && (
          <>
            <TagPicker
              tags={tags}
              value={selectedTags}
              disabled={busy}
              onChange={(value) => {
                setSelectedTags(value);
                setCandidates(null);
                setSelected([]);
              }}
              label="一緒に楽しみたいこと"
            />
            <button
              className="button secondary full"
              disabled={
                busy || !selectedTags.length || desired < 2 || desired > 20
              }
              onClick={() => void findCandidates()}
            >
              {busy ? "候補を探しています…" : "この関心で候補を探す"}
            </button>
            {candidates && (
              <p className="circle-note">
                本人が利用を許可した関心から、{options.length}
                人の候補が見つかりました。
                {candidates.shortage_count > 0 &&
                  `希望人数まで${candidates.shortage_count}人分が不足しています。`}
              </p>
            )}
          </>
        )}
        {loading ? (
          <p role="status">仲間を読み込んでいます…</p>
        ) : (
          <fieldset className="circle-member-picker" disabled={busy}>
            <legend>招待する人を選ぶ（{selected.length}人）</legend>
            {options.map((person) => (
              <label key={person.id} className="circle-member-option">
                <input
                  type="checkbox"
                  disabled={
                    !circle &&
                    !selected.includes(person.id) &&
                    selected.length >= desired - 1
                  }
                  checked={selected.includes(person.id)}
                  onChange={(e) =>
                    setSelected(
                      e.target.checked
                        ? [...selected, person.id]
                        : selected.filter((id) => id !== person.id),
                    )
                  }
                />
                <Avatar user={person} small />
                <span>
                  <strong>{person.name}</strong>
                  {mode === "recommended" && (
                    <Tags
                      ids={
                        candidates?.items.find(
                          (item) => item.user.id === person.id,
                        )?.common_tags || []
                      }
                      tags={tags}
                    />
                  )}
                </span>
              </label>
            ))}
            {!options.length && (mode === "manual" || candidates) && (
              <p className="muted">
                今、招待できる仲間はいません。参加済みの人や、返事待ちの人は除いています。
              </p>
            )}
          </fieldset>
        )}
        <p className="circle-note">
          旅行の予定人数は、この後の条件確認で別に決められます。
        </p>
        <button
          className="button primary full"
          disabled={
            busy ||
            loading ||
            selected.length > 19 ||
            (circle
              ? !selected.length
              : !title.trim() ||
                desired < 2 ||
                desired > 20 ||
                (mode === "recommended" && !candidates))
          }
          onClick={() => void save()}
        >
          {busy
            ? "保存しています…"
            : circle
              ? "選んだ仲間へ招待を送る"
              : "講をつくって招待を送る"}
          <Icon name="arrow" />
        </button>
      </div>
    </Modal>
  );
}

function ProposalView({
  proposal,
  room,
  busy,
  onConfirm,
  onEdit,
}: {
  proposal: CircleProposal;
  room: CircleRoom;
  busy: boolean;
  onConfirm: () => void;
  onEdit: () => void;
}) {
  const mineConfirmed = proposal.confirmations.some(
    (item) => item.role === room.my_role,
  );
  return (
    <section className="circle-proposal">
      <p className="eyebrow">行程と概算見積 · 第{proposal.version}版</p>
      <h3>{proposal.title}</h3>
      <p>{proposal.date_start || "日程は相談中"}</p>
      <div className="circle-quote">
        <strong>
          {proposal.estimated_price_yen.toLocaleString()}円 /{" "}
          {proposal.price_basis === "per_person" ? "1人" : "全員"}
        </strong>
        <span>{scopeLabel(proposal.price_scope)}の概算</span>
        <p>{proposal.price_note}</p>
      </div>
      <details className="circle-itinerary">
        <summary>日別の行程を確認する</summary>
        {proposal.itinerary.map((item, index) => (
          <div className="circle-stop" key={index}>
            <strong>
              {item.day}日目・{periods[item.period]} {item.place}
            </strong>
            <p>{item.description}</p>
            <small>
              {item.travel_minutes === null
                ? "移動時間は確認中"
                : `移動目安 ${item.travel_minutes}分`}
            </small>
          </div>
        ))}
      </details>
      <div className="circle-unknowns">
        <strong>まだ確認が必要なこと</strong>
        {proposal.unknowns.length ? (
          <ul>
            {proposal.unknowns.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        ) : (
          <p>
            追加の未確認事項は記載されていません。予約・空席は別途確認が必要です。
          </p>
        )}
      </div>
      <div className="circle-confirmations">
        <span>
          {proposal.confirmations.some((item) => item.role === "traveler")
            ? "✓ 旅行者代表が確認済み"
            : "旅行者代表の確認待ち"}
        </span>
        <span>
          {proposal.confirmations.some((item) => item.role === "provider")
            ? "✓ 事業者が確認済み"
            : "事業者の確認待ち"}
        </span>
      </div>
      {proposal.confirmations.map((confirmation) => (
        <p className="circle-note" key={confirmation.role}>
          {confirmation.user.name}が第{proposal.version}版を確認 ·{" "}
          {new Intl.DateTimeFormat("ja-JP", {
            timeZone: "Asia/Tokyo",
            month: "numeric",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          }).format(new Date(confirmation.confirmed_at))}
          （日本時間）
        </p>
      ))}
      <p className="circle-reservation">
        {proposal.status === "both_confirmed"
          ? "双方がこの版の内容を確認しました。"
          : "双方で、この版の内容を確かめます。"}
        外部予約は未確定です。
      </p>
      <div className="circle-actions">
        {room.can_confirm && (
          <button
            className="button primary"
            disabled={busy || mineConfirmed}
            onClick={onConfirm}
          >
            {mineConfirmed
              ? "この版は確認済み"
              : `第${proposal.version}版の内容を確認する`}
          </button>
        )}
        {room.can_propose && (
          <button className="button secondary" disabled={busy} onClick={onEdit}>
            行程・見積を改訂
          </button>
        )}
      </div>
    </section>
  );
}

function ProposalEditor({
  room,
  onClose,
  onSaved,
}: {
  room: CircleRoom;
  onClose: () => void;
  onSaved: () => void;
}) {
  const initial = room.proposal;
  const snapshot = room.invitation.snapshot;
  const [title, setTitle] = useState(initial?.title || snapshot.plan.title);
  const [date, setDate] = useState(
    initial?.date_start || snapshot.shared_conditions.date_start || "",
  );
  const [itinerary, setItinerary] = useState<ItineraryItem[]>(
    (initial?.itinerary || snapshot.plan.itinerary).map((stop) => ({
      ...stop,
    })),
  );
  const [price, setPrice] = useState(
    initial?.estimated_price_yen ?? snapshot.plan.price_yen,
  );
  const [basis, setBasis] = useState(
    initial?.price_basis || snapshot.plan.price_basis,
  );
  const [scope, setScope] = useState(
    initial?.price_scope || snapshot.plan.price_scope,
  );
  const [note, setNote] = useState(
    initial?.price_note || snapshot.plan.price_note,
  );
  const [unknowns, setUnknowns] = useState(
    (initial?.unknowns || snapshot.unknowns).join("\n"),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const alive = useAlive();
  const key = useRequestKey();
  function patch(index: number, value: Partial<ItineraryItem>) {
    setItinerary((items) =>
      items.map((item, i) => (i === index ? { ...item, ...value } : item)),
    );
  }
  async function save() {
    setBusy(true);
    setError("");
    const body = {
      title: title.trim(),
      date_start: date || null,
      itinerary,
      estimated_price_yen: price,
      price_basis: basis,
      price_scope: scope,
      price_note: note,
      unknowns: unknowns
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean),
      version: initial?.version || 0,
    };
    if (
      !body.unknowns.length ||
      body.unknowns.length > 12 ||
      body.unknowns.some((item) => item.length > 200)
    ) {
      setError("未確認事項は1行200文字以内で、1〜12件を記入してください。");
      setBusy(false);
      return;
    }
    try {
      await api(
        `/circle-provider-invitations/${room.invitation.id}/proposals`,
        "POST",
        { ...body, client_request_id: key(body) },
      );
      if (alive.current) onSaved();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <Modal
      title={initial ? "行程と見積を改訂する" : "行程と見積を提案する"}
      onClose={onClose}
      busy={busy}
      wide
    >
      <form
        className="circle-form"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <ErrorBox message={error} />
        <p className="muted">
          新しい版では双方の確認を取り直します。外部の予約や決済は行いません。
        </p>
        <fieldset disabled={busy} className="circle-editor-fields">
          <label className="field">
            提案の名前
            <input
              required
              maxLength={120}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label className="field">
            出発日
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          {Array.from(
            { length: snapshot.plan.nights + 1 },
            (_, i) => i + 1,
          ).map((day) => (
            <section key={day} className="circle-day-editor">
              <h3>{day}日目</h3>
              {itinerary.map((item, index) =>
                item.day !== day ? null : (
                  <div className="circle-edit-stop" key={index}>
                    <label className="field">
                      時間帯
                      <Choice
                        value={item.period}
                        onChange={(e) =>
                          patch(index, {
                            period: e.target.value as ItineraryItem["period"],
                          })
                        }
                      >
                        {Object.entries(periods).map(([id, name]) => (
                          <option key={id} value={id}>
                            {name}
                          </option>
                        ))}
                      </Choice>
                    </label>
                    <label className="field">
                      訪問先
                      <input
                        required
                        maxLength={120}
                        value={item.place}
                        onChange={(e) =>
                          patch(index, { place: e.target.value })
                        }
                      />
                    </label>
                    <label className="field">
                      体験と行程
                      <textarea
                        rows={2}
                        maxLength={400}
                        value={item.description}
                        onChange={(e) =>
                          patch(index, { description: e.target.value })
                        }
                      />
                    </label>
                    <label className="field">
                      前の場所からの移動時間（分・任意）
                      <input
                        type="number"
                        min={0}
                        max={1440}
                        value={item.travel_minutes ?? ""}
                        onChange={(e) =>
                          patch(index, {
                            travel_minutes:
                              e.target.value === ""
                                ? null
                                : Number(e.target.value),
                          })
                        }
                      />
                    </label>
                    <button
                      type="button"
                      className="text-button danger"
                      disabled={
                        itinerary.filter((stop) => stop.day === day).length <= 1
                      }
                      onClick={() =>
                        setItinerary((items) =>
                          items.filter((_, i) => i !== index),
                        )
                      }
                    >
                      この訪問先を外す
                    </button>
                  </div>
                ),
              )}
              <button
                type="button"
                className="text-button"
                onClick={() =>
                  setItinerary((items) => [
                    ...items,
                    {
                      day,
                      period: "afternoon",
                      place: "",
                      description: "",
                      travel_minutes: null,
                    },
                  ])
                }
              >
                <Icon name="plus" />
                {day}日目の訪問先を追加
              </button>
            </section>
          ))}
          <label className="field">
            概算費用（円）
            <input
              type="number"
              required
              min={1}
              max={100000000}
              value={price}
              onChange={(e) => setPrice(Number(e.target.value))}
            />
          </label>
          <label className="field">
            費用の単位
            <Choice
              value={basis}
              onChange={(e) => setBasis(e.target.value as typeof basis)}
            >
              <option value="per_person">1人あたり</option>
              <option value="party_total">全員分</option>
            </Choice>
          </label>
          <label className="field">
            費用の範囲
            <Choice
              value={scope}
              onChange={(e) => setScope(e.target.value as typeof scope)}
            >
              <option value="plan_only">プラン部分</option>
              <option value="whole_trip">旅行全体</option>
            </Choice>
          </label>
          <label className="field">
            含む費用・含まない費用
            <textarea
              required
              rows={3}
              maxLength={400}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <label className="field">
            未確認事項（1行200文字以内・12件まで）
            <textarea
              required
              rows={3}
              maxLength={2400}
              value={unknowns}
              onChange={(e) => setUnknowns(e.target.value)}
              placeholder="空席、営業日、交通の手配など"
            />
          </label>
          <button
            className="button primary full"
            disabled={busy || !title.trim() || !note.trim() || !unknowns.trim()}
          >
            {busy ? "保存しています…" : "この行程と見積を共有する"}
          </button>
        </fieldset>
      </form>
    </Modal>
  );
}

export function SharedCircleRoom({
  invitation,
  user,
  onClose,
}: {
  invitation: ProviderInvitation;
  user: User;
  onClose: () => void;
}) {
  const [room, setRoom] = useState<CircleRoom | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editor, setEditor] = useState(false);
  const alive = useAlive();
  const key = useRequestKey();
  async function load() {
    setError("");
    try {
      const result = await api<CircleRoom>(
        `/circle-provider-invitations/${invitation.id}/room`,
      );
      if (alive.current) setRoom(result);
    } catch (e) {
      if (alive.current) {
        setRoom(null);
        setError((e as Error).message);
      }
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [invitation.id]);
  async function confirm() {
    if (!room?.proposal) return;
    setBusy(true);
    setError("");
    const body = {
      proposal_id: room.proposal.id,
      version: room.proposal.version,
    };
    try {
      await api(
        `/circle-provider-invitations/${invitation.id}/confirmations`,
        "POST",
        { ...body, client_request_id: key(body) },
      );
      if (alive.current) await load();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <>
      <Modal
        title="講の共有相談"
        onClose={onClose}
        wide
        variant="conversation"
        busy={busy}
      >
        {loading ? (
          <p className="circle-room-loading" role="status">
            共有の会話をひらいています…
          </p>
        ) : room ? (
          <Conversation
            endpoint={`/circle-provider-invitations/${invitation.id}/messages`}
            messages={room.messages}
            user={user}
            label="講の共有相談"
            onSent={load}
            context={
              <div className="circle-room-context">
                <div className="consultation-context">
                  <p className="eyebrow">この旅の共有相談</p>
                  <h3>{room.invitation.snapshot.plan.title}</h3>
                  <p>共有相手：旅行者の講と {room.invitation.provider.name}</p>
                  <RequirementsSummary
                    value={room.invitation.snapshot.shared_conditions}
                  />
                  <p>{room.invitation.snapshot.share_note}</p>
                  <p className="circle-note">
                    ここに書いた内容だけを事業者と共有します。内輪の会話、写真、個人の関心は表示されません。
                  </p>
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => void load()}
                  >
                    <Icon name="refresh" />
                    会話と提案を更新
                  </button>
                </div>
                <ErrorBox message={error} />
                {room.proposal ? (
                  <ProposalView
                    proposal={room.proposal}
                    room={room}
                    busy={busy}
                    onConfirm={() => void confirm()}
                    onEdit={() => setEditor(true)}
                  />
                ) : (
                  <div className="circle-proposal-empty">
                    <h3>行程と概算見積</h3>
                    <p>
                      {room.can_propose
                        ? "選ばれたプランをもとに、この講へ日程・行程・概算費用を提案できます。"
                        : "事業者が行程と概算見積を提案すると、ここで内容を確認できます。"}
                    </p>
                    {room.can_propose && (
                      <button
                        className="button secondary"
                        onClick={() => setEditor(true)}
                      >
                        行程・見積をつくる
                      </button>
                    )}
                    <p className="circle-reservation">外部予約は未確定です。</p>
                  </div>
                )}
              </div>
            }
          />
        ) : (
          <div className="circle-room-loading">
            <ErrorBox message={error} />
            <button className="button secondary" onClick={() => void load()}>
              もう一度読み込む
            </button>
          </div>
        )}
      </Modal>
      {editor && room && (
        <ProposalEditor
          room={room}
          onClose={() => setEditor(false)}
          onSaved={() => {
            setEditor(false);
            void load();
          }}
        />
      )}
    </>
  );
}

function InviteProvider({
  circle,
  plan,
  onClose,
  onSaved,
}: {
  circle: CircleDetail;
  plan: ProviderPlan;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [note, setNote] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const alive = useAlive();
  const key = useRequestKey();
  async function send() {
    if (!circle.requirements) return;
    setBusy(true);
    setError("");
    const body = {
      plan_id: plan.id,
      plan_version: plan.version,
      requirements_version: circle.requirements.version,
      share_note: note,
      sharing_confirmed: true,
      version: circle.version,
    };
    try {
      await api(`/circles/${circle.id}/provider-invitations`, "POST", {
        ...body,
        client_request_id: key(body),
      });
      if (alive.current) onSaved();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <Modal
      title="行き先を決めて、事業者を招く"
      onClose={onClose}
      busy={busy}
      wide
    >
      <div className="circle-form">
        <ErrorBox message={error} />
        <div className="sharing-recipient">
          <Icon name="people" />
          <div>
            <p className="small-label">招待先</p>
            <strong>{plan.provider.name}</strong>
          </div>
        </div>
        <h3>{plan.title}</h3>
        <RequirementsSummary value={circle.requirements} />
        <p>{plan.price_note}</p>
        <label className="field">
          事業者に伝える希望
          <textarea
            value={note}
            maxLength={1000}
            rows={4}
            disabled={busy}
            onChange={(e) => {
              setNote(e.target.value);
              setConfirmed(false);
            }}
            placeholder="集合場所の希望や、行程について相談したいこと"
          />
        </label>
        <div className="circle-share-list">
          <strong>招待で共有する内容</strong>
          <p>選んだプラン、人数・泊数・予算・希望日、上に書いた相談内容。</p>
          <p>
            講の内輪の会話、写真、個人の関心は共有しません。事業者が参加を承諾した後、共有の会話が開きます。
          </p>
        </div>
        <label className="check-row">
          <input
            type="checkbox"
            checked={confirmed}
            disabled={busy}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          <span>
            この行き先と共有内容を確認し、この事業者を講の共有相談へ招きます。
          </span>
        </label>
        <p className="circle-reservation">
          この操作では予約・決済は確定しません。
        </p>
        <button
          className="button primary full"
          disabled={busy || !confirmed || !circle.requirements}
          onClick={() => void send()}
        >
          {busy ? "招待を送っています…" : "この行き先で事業者を招く"}
          <Icon name="arrow" />
        </button>
      </div>
    </Modal>
  );
}

function CircleWorkspace({
  id,
  communities,
  user,
  tags,
  onBack,
  onOpenCircle,
}: {
  id: string;
  communities: Community[];
  user: User;
  tags: Tag[];
  onBack: () => void;
  onOpenCircle: (id: string) => void;
}) {
  const [circle, setCircle] = useState<CircleDetail | null>(null);
  const [messages, setMessages] = useState<MarketMessage[]>([]);
  const [turns, setTurns] = useState<AssistantTurn[]>([]);
  const [tab, setTab] = useState<
    | "conversation"
    | "assistant"
    | "plans"
    | "members"
    | "reflections"
    | "occasions"
  >("conversation");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [loading, setLoading] = useState(true);
  const [body, setBody] = useState("");
  const [editRequirements, setEditRequirements] = useState<{
    value: Requirements;
    unknownFields: string[];
    notice: string;
    fromAssistant: boolean;
  } | null>(null);
  const [cards, setCards] = useState<CandidateCard[]>([]);
  const [detailBlocked, setDetailBlocked] = useState(false);
  const [editingTags, setEditingTags] = useState<string[] | null>(null);
  const [detail, setDetail] = useState<ProviderPlan | null>(null);
  const [chosen, setChosen] = useState<ProviderPlan | null>(null);
  const [addMembers, setAddMembers] = useState(false);
  const [room, setRoom] = useState<ProviderInvitation | null>(null);
  const [help, setHelp] = useState<{
    description: string;
    limitations: string[];
  } | null>(null);
  const [confirmAction, setConfirmAction] = useState<
    "leave" | "close" | "cancel-provider" | null
  >(null);
  const alive = useAlive();
  const key = useRequestKey();
  async function load() {
    setError("");
    try {
      const [c, m, t, candidateCards] = await Promise.all([
        api<CircleDetail>(`/circles/${id}`),
        api<{ items: MarketMessage[] }>(`/travel-parties/${id}/messages`),
        api<{ items: AssistantTurn[] }>(`/circles/${id}/assistant-turns`),
        api<{ items: CandidateCard[] }>(`/circles/${id}/candidate-cards`),
      ]);
      if (alive.current) {
        setCircle(c);
        setMessages(m.items);
        setTurns(t.items);
        setCards(candidateCards.items);
      }
    } catch (e) {
      if (alive.current) {
        setCircle(null);
        setError((e as Error).message);
      }
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [id]);
  async function talk() {
    setBusy("assistant");
    setError("");
    const payload = { body };
    try {
      await api(`/circles/${id}/assistant-turns`, "POST", {
        ...payload,
        client_request_id: key(payload),
      });
      if (!alive.current) return;
      key.reset();
      setBody("");
      await load();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy("");
    }
  }
  async function saveConditions(value: Requirements) {
    setBusy("conditions");
    setError("");
    try {
      await api(`/travel-parties/${id}/requirements`, "PUT", value);
      if (!alive.current) return;
      setEditRequirements(null);
      await load();
      setTab("plans");
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy("");
    }
  }
  async function cancelMember(invitation: CircleInvitation) {
    setBusy(invitation.id);
    setError("");
    const payload = { version: invitation.version };
    try {
      await api(`/circle-invitations/${invitation.id}/cancel`, "POST", {
        ...payload,
        client_request_id: key({ invitation: invitation.id, ...payload }),
      });
      if (alive.current) await load();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy("");
    }
  }
  async function saveCircleTags() {
    if (!circle || !editingTags) return;
    setBusy("tags");
    setError("");
    try {
      await api(`/circles/${id}/preferences`, "PUT", {
        tags: editingTags,
        version: circle.version,
      });
      if (!alive.current) return;
      setEditingTags(null);
      await load();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy("");
    }
  }
  async function finalAction() {
    if (!circle || !confirmAction) return;
    setBusy(confirmAction);
    setError("");
    try {
      if (
        confirmAction === "cancel-provider" &&
        circle.active_provider_invitation
      ) {
        const invite = circle.active_provider_invitation;
        const payload = { version: invite.version };
        await api(`/circle-provider-invitations/${invite.id}/cancel`, "POST", {
          ...payload,
          client_request_id: key({ invitation: invite.id, ...payload }),
        });
      } else
        await api(`/circles/${id}/${confirmAction}`, "POST", {
          version: circle.version,
        });
      if (!alive.current) return;
      setConfirmAction(null);
      if (confirmAction === "leave") onBack();
      else await load();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy("");
    }
  }
  if (loading) return <p role="status">講をひらいています…</p>;
  if (!circle)
    return (
      <>
        <ErrorBox message={error} />
        <button className="button secondary" onClick={onBack}>
          講の一覧へ
        </button>
      </>
    );
  const invitation = circle.active_provider_invitation;
  const community =
    communities.find((item) => item.id === circle.community_id) || null;
  const open = circle.status === "open";
  const openCandidate = (plan: ProviderPlan, canInvite: boolean) => {
    setDetailBlocked(!canInvite);
    setDetail(plan);
  };
  const updateConditions = (turn?: AssistantTurn) => {
    const conditions = turn ? turn.proposed_conditions : circle.requirements;
    const requiredKeys = [
      "planned_people",
      "nights",
      "budget_yen",
      "budget_basis",
      "budget_scope",
    ] as const;
    setEditRequirements({
      value: {
        ...emptyRequirements,
        ...conditions,
        version: circle.requirements?.version || 0,
      },
      unknownFields: turn
        ? requiredKeys.filter((field) => conditions?.[field] == null)
        : [],
      fromAssistant: !!turn,
      notice: turn
        ? `会話から整理した未確定の候補です。空欄の条件はご自身で入力してください。${turn.ambiguities.join("。")}`
        : "保存する旅行条件を確認してください。",
    });
  };
  return (
    <section className="circle-workspace">
      <button className="text-button" onClick={onBack}>
        ← 講の一覧へ
      </button>
      <header className="circle-heading">
        <p className="eyebrow">{community?.name || "旅の仲間"}</p>
        <h1>{circle.title}</h1>
        <p>
          参加済み {circle.accepted_count}人 · 招待中 {circle.pending_count}人
          {circle.shortage_count > 0 &&
            ` · あと${circle.shortage_count}人を募集中`}
        </p>
        <small>
          旅行の予定人数：{circle.requirements?.planned_people ?? "未確認"}
          {circle.requirements ? "人" : ""} ／ 一緒に計画する人数とは別です。
        </small>
      </header>
      <ErrorBox message={error} />
      <div className="circle-actions">
        <button
          className="text-button"
          disabled={!!busy}
          onClick={() => void load()}
        >
          <Icon name="refresh" />
          講を更新
        </button>
        {circle.can_manage && open && (
          <button
            className="text-button"
            disabled={!!busy}
            onClick={() => updateConditions()}
          >
            <Icon name="calendar" />
            旅行条件を確認
          </button>
        )}
      </div>
      {!open && (
        <p className="hint-box">
          この講は終了しています。新しい招待や投稿はできません。
        </p>
      )}
      {invitation && (
        <section className="circle-provider-card">
          <p className="eyebrow">この講の行き先と事業者</p>
          <h3>{invitation.snapshot.plan.title}</h3>
          <p>
            {invitation.provider.name} · {statusLabel(invitation.status)}
          </p>
          {invitation.status === "pending" ? (
            <p className="circle-note">
              事業者の参加承諾を待っています。まだ共有の会話は開いていません。
            </p>
          ) : (
            invitation.status === "accepted" && (
              <>
                <p className="circle-note">
                  共有相手：この講の参加者と {invitation.provider.name}
                  。内輪の会話とは分けて話せます。
                </p>
                <button
                  className="button primary full"
                  onClick={() => setRoom(invitation)}
                >
                  この講で事業者と話す
                  <Icon name="arrow" />
                </button>
              </>
            )
          )}
          {circle.can_manage && open && (
            <button
              className="text-button danger"
              disabled={!!busy}
              onClick={() => setConfirmAction("cancel-provider")}
            >
              {invitation.status === "accepted"
                ? "事業者との共有相談を終了"
                : "事業者への招待を取り消す"}
            </button>
          )}
        </section>
      )}
      <nav className="market-tabs circle-tabs" aria-label="講の中の操作">
        {(
          [
            ["conversation", "仲間と話す"],
            ["assistant", "AIに相談"],
            ["plans", "行き先"],
            ["members", "参加者"],
            ["reflections", "振り返り"],
            ["occasions", "記念日"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            className={tab === value ? "selected" : ""}
            aria-pressed={tab === value}
            onClick={() => setTab(value)}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "occasions" ? (
        <Suspense fallback={<p role="status">記念日をひらいています…</p>}>
          <CircleOccasions
            key={id}
            circleId={id}
            circleTitle={circle.title}
            tags={tags}
            onOpenConversation={() => {
              setTab("conversation");
              void load();
            }}
          />
        </Suspense>
      ) : tab === "reflections" ? (
        <Suspense fallback={<p role="status">振り返りをひらいています…</p>}>
          <ReflectionWorkspace
            key={id}
            circleId={id}
            canManage={circle.can_manage}
          />
        </Suspense>
      ) : tab === "conversation" ? (
        <>
          <p className="circle-note">
            この会話は講の参加者だけに見えます。事業者には共有されません。
          </p>
          <Conversation
            context={
              <SavedCandidateList cards={cards} onOpen={openCandidate} />
            }
            endpoint={`/travel-parties/${id}/messages`}
            messages={messages}
            user={user}
            onSent={load}
            closed={!open}
            label="講の内輪の会話"
          />
        </>
      ) : tab === "assistant" ? (
        <div className="circle-assistant">
          <div className="circle-assistant-intro">
            <Icon name="leaf" />
            <div>
              <h2>旅行条件の相談</h2>
              <p>
                人数、泊数、予算、行き先を入力できます。整理した条件は、確認してから保存します。
              </p>
              <button
                className="text-button"
                onClick={async () => {
                  try {
                    const result = await api<{
                      description: string;
                      limitations: string[];
                    }>("/circles/help");
                    if (alive.current) setHelp(result);
                  } catch (e) {
                    if (alive.current) setError((e as Error).message);
                  }
                }}
              >
                案内の仕組みを見る
              </button>
            </div>
          </div>
          <div className="circle-assistant-turns">
            {turns.slice(-10).map((turn) => (
              <article className="circle-assistant-turn" key={turn.id}>
                <p className="circle-question">
                  <strong>{turn.author_name}</strong>
                  {turn.user_body}
                </p>
                <div className="circle-answer">
                  <strong>旅の案内役</strong>
                  <p>{turn.reply}</p>
                  {turn.ambiguities.length > 0 && (
                    <ul>
                      {turn.ambiguities.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  )}
                  {turn.needs_confirmation && circle.can_manage && open && (
                    <button
                      className="button secondary"
                      disabled={!!busy}
                      onClick={() => updateConditions(turn)}
                    >
                      この候補を確認・訂正する
                    </button>
                  )}
                  {turn.candidates.length > 0 && (
                    <div className="circle-turn-plans">
                      {turn.candidates.slice(0, 3).map((candidate) => (
                        <button
                          className="circle-plan-link"
                          key={candidate.plan.id}
                          onClick={() => openCandidate(candidate.plan, true)}
                        >
                          <span>
                            <strong>{candidate.plan.title}</strong>
                            <small>{candidate.reasons.join("・")}</small>
                          </span>
                          <Icon name="arrow" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
          {turns.length > 10 && (
            <p className="circle-note">最近10回のやり取りを表示しています。</p>
          )}
          {open && (
            <form
              className="circle-assistant-form"
              onSubmit={(e) => {
                e.preventDefault();
                void talk();
              }}
            >
              <label className="field">
                案内役に相談する
                <textarea
                  rows={3}
                  value={body}
                  maxLength={2000}
                  disabled={!!busy}
                  placeholder="6人で2泊3日、1人3万円で森とカフェを楽しみたい"
                  onChange={(e) => setBody(e.target.value)}
                />
              </label>
              <button
                className="button primary full"
                disabled={!!busy || !body.trim()}
              >
                {busy === "assistant"
                  ? "希望を整理しています…"
                  : "この希望を伝える"}
                <Icon name="arrow" />
              </button>
            </form>
          )}
        </div>
      ) : tab === "plans" ? (
        <>
          <RequirementsSummary value={circle.requirements} />
          <p className="circle-note">
            講の希望と確認済みの条件から、関連する順に探せます。候補を保存し、行き先と共有内容を確認してから事業者を招きます。
          </p>
          <Tags ids={circle.tags || []} tags={tags} />
          {circle.can_manage && open && (
            <button
              className="text-button"
              onClick={() => setEditingTags(circle.tags || [])}
            >
              講の希望を見直す
            </button>
          )}
          {!circle.requirements && circle.can_manage && open && (
            <button className="text-button" onClick={() => updateConditions()}>
              旅行条件を確認する
            </button>
          )}
          <SavedCandidateList cards={cards} onOpen={openCandidate} />
          {community && open && (
            <PlanDiscovery
              community={community}
              tags={tags}
              circle={circle}
              onOpenCircle={(nextId) => {
                if (nextId === id) {
                  setTab("conversation");
                  void load();
                } else onOpenCircle(nextId);
              }}
            />
          )}
        </>
      ) : (
        <div className="circle-members">
          <h2>参加している仲間</h2>
          {circle.members.map((member) => (
            <div className="circle-person" key={member.id}>
              <Avatar user={member} small />
              <strong>{member.name}</strong>
              <span>
                {circle.representative_id === member.id ? "代表" : "参加済み"}
              </span>
            </div>
          ))}
          <h3>招待と返事</h3>
          {circle.invitations.map((memberInvitation) => (
            <div className="circle-person" key={memberInvitation.id}>
              <Avatar user={memberInvitation.invitee} small />
              <span>
                <strong>{memberInvitation.invitee.name}</strong>
                <small>{statusLabel(memberInvitation.status)}</small>
              </span>
              {circle.can_manage &&
                memberInvitation.status === "pending" &&
                open && (
                  <button
                    className="text-button danger"
                    disabled={!!busy}
                    onClick={() => void cancelMember(memberInvitation)}
                  >
                    招待取消
                  </button>
                )}
            </div>
          ))}
          {circle.can_manage && community && open && (
            <button
              className="button secondary full"
              onClick={() => setAddMembers(true)}
            >
              仲間を追加で招く
            </button>
          )}
          {open && (
            <button
              className="text-button danger"
              onClick={() =>
                setConfirmAction(circle.can_manage ? "close" : "leave")
              }
            >
              {circle.can_manage ? "この講を終了する" : "この講から退出する"}
            </button>
          )}
        </div>
      )}
      {editingTags && (
        <Modal
          title="講の希望を見直す"
          onClose={() => setEditingTags(null)}
          busy={!!busy}
        >
          <ErrorBox message={error} />
          <p className="circle-note">
            この講で楽しみたいことを選んでください。保存すると、おすすめの順番にも反映されます。
          </p>
          <TagPicker
            tags={tags}
            value={editingTags}
            onChange={setEditingTags}
            disabled={!!busy}
          />
          <button
            className="button primary full"
            disabled={!!busy}
            onClick={() => void saveCircleTags()}
          >
            {busy ? "保存しています…" : "講の希望を保存"}
          </button>
        </Modal>
      )}
      {editRequirements && (
        <Modal
          title="旅行条件を確認する"
          onClose={() => setEditRequirements(null)}
          busy={!!busy}
          wide
        >
          <ErrorBox message={error} />
          <p className="circle-note">
            人数・泊数・予算の単位と範囲を確かめてください。参加者を自動で増やす操作ではありません。
          </p>
          <p className="hint-box">{editRequirements.notice}</p>
          <RequirementEditor
            initial={editRequirements.value}
            unknownFields={editRequirements.unknownFields}
            requireBudget={editRequirements.fromAssistant}
            tags={tags}
            draft={null}
            busy={!!busy}
            onSave={saveConditions}
          />
        </Modal>
      )}
      {detail && (
        <PlanDetail
          plan={detail}
          tags={tags}
          onClose={() => setDetail(null)}
          disabled={!!busy}
          chooseLabel="この行き先で事業者を招く"
          onChoose={
            circle.can_manage && open && !invitation && !detailBlocked
              ? () => {
                  if (!circle.requirements) {
                    setDetail(null);
                    updateConditions();
                  } else {
                    setChosen(detail);
                    setDetail(null);
                  }
                }
              : undefined
          }
        />
      )}
      {chosen && (
        <InviteProvider
          circle={circle}
          plan={chosen}
          onClose={() => setChosen(null)}
          onSaved={() => {
            setChosen(null);
            void load();
          }}
        />
      )}
      {addMembers && community && (
        <CreateCircle
          community={community}
          user={user}
          tags={tags}
          mode="manual"
          circle={circle}
          onClose={() => setAddMembers(false)}
          onSaved={() => {
            setAddMembers(false);
            void load();
          }}
        />
      )}
      {room && (
        <SharedCircleRoom
          invitation={room}
          user={user}
          onClose={() => {
            setRoom(null);
            void load();
          }}
        />
      )}
      {help && (
        <Modal title="旅の案内役について" onClose={() => setHelp(null)}>
          <p>{help.description}</p>
          <ul>
            {help.limitations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
          <p className="circle-note">
            外部AIサービスには接続していません。写真や会話を外部へ送信しません。
          </p>
        </Modal>
      )}
      {confirmAction && (
        <Modal
          title={
            confirmAction === "leave"
              ? "この講から退出しますか？"
              : confirmAction === "close"
                ? "この講を終了しますか？"
                : "事業者との共有を終了しますか？"
          }
          onClose={() => setConfirmAction(null)}
          busy={!!busy}
        >
          <p>
            {confirmAction === "leave"
              ? "退出すると、この講の内輪と共有の会話は見られなくなります。"
              : confirmAction === "close"
                ? "返事待ちの招待と事業者との共有相談を閉じ、新しい投稿を終了します。"
                : "この事業者の参加を取り消し、共有の会話を閉じます。再び招く場合は新しい会話になります。"}
          </p>
          <ErrorBox message={error} />
          <div className="dialog-actions">
            <button
              className="button secondary"
              disabled={!!busy}
              onClick={() => setConfirmAction(null)}
            >
              戻る
            </button>
            <button
              className="button danger-button"
              disabled={!!busy}
              onClick={() => void finalAction()}
            >
              {busy
                ? "処理しています…"
                : confirmAction === "leave"
                  ? "退出する"
                  : "終了する"}
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}

export default function Circles({
  community,
  communities,
  user,
  tags,
  onLegacy,
  initialCircleId = "",
}: {
  community: Community | null;
  communities: Community[];
  user: User;
  tags: Tag[];
  onLegacy: () => void;
  initialCircleId?: string;
}) {
  const [data, setData] = useState<CircleList | null>(null);
  const [circleId, setCircleId] = useState(initialCircleId);
  const [createMode, setCreateMode] = useState<"recommended" | "manual" | null>(
    null,
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [loading, setLoading] = useState(true);
  const alive = useAlive();
  const key = useRequestKey();
  async function load() {
    setError("");
    try {
      const result = await api<CircleList>("/circles");
      if (alive.current) setData(result);
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [user.id]);
  async function respond(
    invitation: CircleInvitation,
    decision: "accepted" | "declined",
  ) {
    setBusy(invitation.id);
    setError("");
    const body = { decision, version: invitation.version };
    try {
      await api(`/circle-invitations/${invitation.id}/respond`, "POST", {
        ...body,
        client_request_id: key({ invitation: invitation.id, ...body }),
      });
      if (alive.current) await load();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy("");
    }
  }
  async function connect(groupId: string) {
    setBusy(groupId);
    setError("");
    const body = { group_id: groupId };
    try {
      const result = await api<CircleDetail>("/circles/from-group", "POST", {
        ...body,
        client_request_id: key(body),
      });
      if (alive.current) {
        setCircleId(result.id);
        await load();
      }
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy("");
    }
  }
  if (circleId)
    return (
      <CircleWorkspace
        key={`${user.id}-${circleId}`}
        id={circleId}
        communities={communities}
        user={user}
        tags={tags}
        onOpenCircle={setCircleId}
        onBack={() => {
          setCircleId("");
          void load();
        }}
      />
    );
  return (
    <section className="circles-page">
      <header className="page-heading">
        <h1>講を見つける</h1>
        <p>
          関心が共通する候補から、または知っている会員を選んで招待できます。
        </p>
      </header>
      <div className="circle-create-options">
        <button
          disabled={!community}
          onClick={() => setCreateMode("recommended")}
        >
          <span className="round-icon">
            <Icon name="leaf" />
          </span>
          <strong>関心から仲間を探す</strong>
          <small>関心が共通する候補から招待する人を選ぶ</small>
          <Icon name="arrow" />
        </button>
        <button disabled={!community} onClick={() => setCreateMode("manual")}>
          <span className="round-icon">
            <Icon name="people" />
          </span>
          <strong>仲間を選んでつくる</strong>
          <small>家族・同期・友人に、自分から声をかける</small>
          <Icon name="arrow" />
        </button>
      </div>
      <ErrorBox message={error} />
      <div className="section-title">
        <h2>自分の講と招待</h2>
        <button
          className="text-button"
          disabled={!!busy}
          onClick={() => void load()}
        >
          <Icon name="refresh" />
          更新
        </button>
      </div>
      {loading ? (
        <p role="status">講と招待を読み込んでいます…</p>
      ) : (
        <>
          {data?.invitations.map((invitation) => (
            <article className="circle-invitation-card" key={invitation.id}>
              <p className="eyebrow">{invitation.inviter.name}さんからの招待</p>
              <h3>{invitation.circle_title}</h3>
              <p>自分で参加を選ぶまで、講のメンバーにはなりません。</p>
              <div className="circle-actions">
                <button
                  className="button primary"
                  disabled={!!busy}
                  onClick={() => void respond(invitation, "accepted")}
                >
                  この講に参加する
                </button>
                <button
                  className="button secondary"
                  disabled={!!busy}
                  onClick={() => void respond(invitation, "declined")}
                >
                  今回は見送る
                </button>
              </div>
            </article>
          ))}
          <div className="circle-list">
            {data?.items
              .filter((circle) => circle.status === "open")
              .map((circle) => (
                <button
                  key={circle.id}
                  className="circle-list-card"
                  onClick={() => setCircleId(circle.id)}
                >
                  <span className="circle-card-mark">講</span>
                  <span>
                    <strong>{circle.title}</strong>
                    <small>
                      {circle.accepted_count}人が参加 · {circle.pending_count}
                      人が返事待ち{circle.status !== "open" && " · 終了"}
                    </small>
                    {circle.active_provider_invitation && (
                      <small>
                        {circle.active_provider_invitation.provider.name} ·{" "}
                        {statusLabel(circle.active_provider_invitation.status)}
                      </small>
                    )}
                  </span>
                  <Icon name="arrow" />
                </button>
              ))}
          </div>
          {!data?.items.some((circle) => circle.status === "open") &&
            !data?.invitations.length && (
              <Empty title="参加中の講はありません">
                <p>仲間を選んで招待し、旅の希望を話す場所をつくれます。</p>
              </Empty>
            )}
          {!!data?.items.some((circle) => circle.status !== "open") && (
            <details className="circle-closed-list">
              <summary>
                終了した講（
                {data.items.filter((circle) => circle.status !== "open").length}
                件）
              </summary>
              <div className="circle-list">
                {data.items
                  .filter((circle) => circle.status !== "open")
                  .map((circle) => (
                    <button
                      className="circle-list-card"
                      key={circle.id}
                      onClick={() => setCircleId(circle.id)}
                    >
                      <span className="circle-card-mark">講</span>
                      <span>
                        <strong>{circle.title}</strong>
                        <small>{circle.accepted_count}人の講 · 終了</small>
                      </span>
                      <Icon name="arrow" />
                    </button>
                  ))}
              </div>
            </details>
          )}
          {!!data?.groups.filter((group) => !group.circle_id).length && (
            <section className="circle-existing-groups">
              <h3>これまでに集まった講</h3>
              {data.groups
                .filter((group) => !group.circle_id)
                .map((group) => (
                  <button
                    key={group.id}
                    className="circle-list-card"
                    disabled={!!busy}
                    onClick={() => void connect(group.id)}
                  >
                    <span>
                      <strong>{group.purpose}</strong>
                      <small>
                        参加済み {group.member_count}人で、旅の相談を始める
                      </small>
                    </span>
                    <Icon name="arrow" />
                  </button>
                ))}
            </section>
          )}
          <button className="text-button" onClick={onLegacy}>
            これまでの提案・協力を見る
            <Icon name="arrow" />
          </button>
        </>
      )}
      {createMode && community && (
        <CreateCircle
          community={community}
          user={user}
          tags={tags}
          mode={createMode}
          onClose={() => setCreateMode(null)}
          onSaved={(circle) => {
            setCreateMode(null);
            setCircleId(circle.id);
            void load();
          }}
        />
      )}
    </section>
  );
}

export function ProviderCircleInvites({ user }: { user: User }) {
  const [items, setItems] = useState<ProviderInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [room, setRoom] = useState<ProviderInvitation | null>(null);
  const alive = useAlive();
  const key = useRequestKey();
  async function load() {
    setError("");
    try {
      const result = await api<{ items: ProviderInvitation[] }>(
        "/circle-provider-invitations",
      );
      if (alive.current) setItems(result.items);
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [user.id]);
  async function respond(
    invitation: ProviderInvitation,
    decision: "accepted" | "declined",
  ) {
    setBusy(invitation.id);
    setError("");
    const body = { decision, version: invitation.version };
    try {
      const result = await api<ProviderInvitation>(
        `/circle-provider-invitations/${invitation.id}/respond`,
        "POST",
        {
          ...body,
          client_request_id: key({ invitation: invitation.id, ...body }),
        },
      );
      if (!alive.current) return;
      await load();
      if (result.status === "accepted") setRoom(result);
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy("");
    }
  }
  return (
    <section className="circle-provider-inbox">
      <div className="section-title">
        <h2>講への招待</h2>
        <button
          className="text-button"
          disabled={!!busy}
          onClick={() => void load()}
        >
          <Icon name="refresh" />
          招待を更新
        </button>
      </div>
      <p className="circle-note">
        旅行者が行き先と共有内容を決めて送った招待です。参加を承諾した後、同じ旅の共有相談に入れます。
      </p>
      <ErrorBox message={error} />
      {loading ? (
        <p role="status">講への招待を読み込んでいます…</p>
      ) : !items.length ? (
        <Empty title="まだ講への招待はありません">
          <p>公開プランを選んだ旅行者から、ここへ招待が届きます。</p>
        </Empty>
      ) : (
        items.map((invitation) => (
          <article className="circle-invitation-card" key={invitation.id}>
            <p className="eyebrow">
              {invitation.inviter_name}さんから ·{" "}
              {statusLabel(invitation.status)}
            </p>
            <h3>{invitation.snapshot.plan.title}</h3>
            <RequirementsSummary
              value={invitation.snapshot.shared_conditions}
            />
            <p className="circle-share-note">
              {invitation.snapshot.share_note}
            </p>
            <p className="circle-note">
              内輪の会話、写真、個人の関心は共有されません。
            </p>
            {invitation.status === "pending" ? (
              <div className="circle-actions">
                <button
                  className="button primary"
                  disabled={!!busy}
                  onClick={() => void respond(invitation, "accepted")}
                >
                  招待を承諾して参加
                </button>
                <button
                  className="button secondary"
                  disabled={!!busy}
                  onClick={() => void respond(invitation, "declined")}
                >
                  今回は見送る
                </button>
              </div>
            ) : (
              invitation.status === "accepted" && (
                <button
                  className="button primary full"
                  onClick={() => setRoom(invitation)}
                >
                  この講の共有相談へ
                  <Icon name="arrow" />
                </button>
              )
            )}
          </article>
        ))
      )}
      {room && (
        <SharedCircleRoom
          invitation={room}
          user={user}
          onClose={() => {
            setRoom(null);
            void load();
          }}
        />
      )}
    </section>
  );
}
