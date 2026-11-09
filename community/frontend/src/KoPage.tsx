import Choice from "./Choice";
import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type {
  Community,
  Contribution,
  Group,
  Proposal,
  Tag,
  Trip,
  User,
} from "./types";
import {
  Avatar,
  Empty,
  ErrorBox,
  Icon,
  LocalPhoto,
  Modal,
  Tags,
  TagPicker,
} from "./ui";
export function tripCover(key: string) {
  return /^[a-z0-9_-]+$/.test(key) ? `/api/covers/${key}` : "";
}
const roles: { id: Contribution["role"]; label: string }[] = [
  { id: "none", label: "参加を楽しむ" },
  { id: "research", label: "行き先を調べる" },
  { id: "schedule", label: "行程を考える" },
  { id: "food", label: "食べる場所を探す" },
  { id: "photos", label: "写真を撮る" },
];
function GroupPanel({
  group,
  user,
  onRefresh,
}: {
  group: Group;
  user: User;
  onRefresh: () => Promise<void>;
}) {
  const current = group.contributions.find((c) => c.user_id === user.id);
  const [role, setRole] = useState<Contribution["role"]>(
    current?.role || "none",
  );
  const [note, setNote] = useState(current?.note || "");
  const [date, setDate] = useState(group.plan.date || "");
  const [meeting, setMeeting] = useState(group.plan.meeting_point);
  const [notes, setNotes] = useState(group.plan.notes);
  const [planVersion, setPlanVersion] = useState(group.plan.version);
  const [planUpdated, setPlanUpdated] = useState(false);
  const planDirty = useRef(false);
  const contributionDirty = useRef(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  // Refresh server values without remounting the panel or replacing unsaved edits.
  useEffect(() => {
    if (planDirty.current) {
      setPlanUpdated(true);
      return;
    }
    setDate(group.plan.date || "");
    setMeeting(group.plan.meeting_point);
    setNotes(group.plan.notes);
    setPlanVersion(group.plan.version);
    setPlanUpdated(false);
  }, [
    group.plan.version,
    group.plan.date,
    group.plan.meeting_point,
    group.plan.notes,
  ]);
  useEffect(() => {
    if (contributionDirty.current) return;
    setRole(current?.role || "none");
    setNote(current?.note || "");
  }, [current?.role, current?.note]);
  function loadLatestPlan() {
    planDirty.current = false;
    setDate(group.plan.date || "");
    setMeeting(group.plan.meeting_point);
    setNotes(group.plan.notes);
    setPlanVersion(group.plan.version);
    setPlanUpdated(false);
    setError("");
  }
  async function save(part: "contribution" | "plan") {
    setBusy(part);
    setError("");
    setSaved("");
    try {
      const updated = await api<Group>(
        `/groups/${group.id}/${part}`,
        "PUT",
        part === "plan"
          ? {
              date: date || null,
              meeting_point: meeting,
              notes,
              version: planVersion,
            }
          : { role, note },
      );
      if (part === "plan") {
        planDirty.current = false;
        setDate(updated.plan.date || "");
        setMeeting(updated.plan.meeting_point);
        setNotes(updated.plan.notes);
        setPlanVersion(updated.plan.version);
        setPlanUpdated(false);
      } else {
        contributionDirty.current = false;
        const own = updated.contributions.find((c) => c.user_id === user.id);
        setRole(own?.role || "none");
        setNote(own?.note || "");
      }
      await onRefresh();
      setSaved(
        part === "plan"
          ? "旅の計画を保存しました。"
          : "できることを保存しました。",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  return (
    <article className="group-card">
      <div className="section-kicker">
        <Icon name="check" />
        <span>みんなの参加がそろいました</span>
      </div>
      <h2>{group.purpose}</h2>
      <p className="muted">
        {group.trip.area} · {group.members.length}人の講
      </p>
      <div className="people-line">
        {group.members.map((m) => (
          <div key={m.id}>
            <Avatar user={m} />
            <span>{m.name}</span>
          </div>
        ))}
      </div>
      <ErrorBox message={error} />
      <details open>
        <summary>できることを、持ち寄る</summary>
        <p className="muted">
          担当は任意です。役割を持たずに参加しても大丈夫。
        </p>
        <fieldset disabled={!!busy} className="radio-cards">
          <legend>自分ができそうなこと</legend>
          {roles.map((r) => (
            <label key={r.id} className={role === r.id ? "selected" : ""}>
              <input
                type="radio"
                name={`role-${group.id}`}
                value={r.id}
                checked={role === r.id}
                onChange={() => {
                  contributionDirty.current = true;
                  setRole(r.id);
                }}
              />
              {r.label}
            </label>
          ))}
        </fieldset>
        <label className="field">
          ひとこと <span className="optional">任意</span>
          <input
            value={note}
            onChange={(e) => {
              contributionDirty.current = true;
              setNote(e.target.value);
            }}
            maxLength={300}
            disabled={!!busy}
            placeholder="例：駅の近くのカフェを探しておきます"
          />
        </label>
        <button
          className="button secondary"
          disabled={!!busy}
          onClick={() => void save("contribution")}
        >
          {busy === "contribution" ? "保存中…" : "できることを保存"}
        </button>
        {group.contributions.length > 0 && (
          <ul className="contributions">
            {group.contributions.map((c) => (
              <li key={c.user_id}>
                <strong>{c.name}</strong>
                <span>
                  {roles.find((r) => r.id === c.role)?.label}
                  {c.note && ` · ${c.note}`}
                </span>
              </li>
            ))}
          </ul>
        )}
      </details>
      <details>
        <summary>旅の計画をひらく</summary>
        {planUpdated && (
          <div className="hint-box" role="status">
            <p>
              ほかの操作で計画が更新されています。入力中の内容は残しています。
            </p>
            <button
              className="text-button"
              disabled={!!busy}
              onClick={loadLatestPlan}
            >
              編集内容を破棄して最新の計画を読む
            </button>
          </div>
        )}
        <div className="field-row">
          <label className="field">
            出発日
            <input
              type="date"
              value={date}
              onChange={(e) => {
                planDirty.current = true;
                setDate(e.target.value);
              }}
              disabled={!!busy}
            />
          </label>
          <label className="field">
            待ち合わせ
            <input
              value={meeting}
              onChange={(e) => {
                planDirty.current = true;
                setMeeting(e.target.value);
              }}
              maxLength={200}
              placeholder="駅・改札・時間など"
              disabled={!!busy}
            />
          </label>
        </div>
        <label className="field">
          行程メモ
          <textarea
            value={notes}
            onChange={(e) => {
              planDirty.current = true;
              setNotes(e.target.value);
            }}
            rows={4}
            maxLength={2000}
            disabled={!!busy}
            placeholder="寄りたい場所や、みんなで決めたいこと"
          />
        </label>
        <button
          className="button primary"
          disabled={!!busy}
          onClick={() => void save("plan")}
        >
          {busy === "plan" ? "保存中…" : "旅の計画を保存"}
        </button>
        <p className="muted">
          料金は概算です。営業・交通・空席は、計画を進めながら確認してください。
        </p>
      </details>
      <p className="success-text" role="status">
        {saved}
      </p>
    </article>
  );
}
export default function KoPage({
  community,
  trips,
  proposals,
  groups,
  tags,
  user,
  onRefresh,
  onPreferences,
}: {
  community: Community | null;
  trips: Trip[];
  proposals: Proposal[];
  groups: Group[];
  tags: Tag[];
  user: User;
  onRefresh: () => Promise<void>;
  onPreferences: () => void;
}) {
  const [creating, setCreating] = useState(false);
  const [tripId, setTripId] = useState(trips[0]?.id || "");
  const [purpose, setPurpose] = useState("");
  const [selected, setSelected] = useState<string[]>(trips[0]?.tags || []);
  const [size, setSize] = useState(3);
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function create() {
    if (!community) return;
    setBusy("create");
    setError("");
    try {
      await api<Proposal>(`/communities/${community.id}/proposals`, "POST", {
        purpose,
        tags: selected,
        size,
        trip_id: tripId,
        date: date || null,
      });
      await onRefresh();
      setCreating(false);
      setMessage(
        "仲間候補を見つけました。それぞれの参加意思を確認しましょう。",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function respond(p: Proposal, decision: "accepted" | "declined") {
    setBusy(p.id);
    setError("");
    setMessage("");
    try {
      await api(`/proposals/${p.id}/respond`, "POST", {
        decision,
        version: p.version,
      });
      await onRefresh();
      setMessage(
        decision === "accepted"
          ? "参加する意思を伝えました。全員が参加すると講ができます。"
          : "今回は見送りました。理由はほかの人には伝えません。",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function reload() {
    setBusy("reload");
    setError("");
    try {
      await onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  const active = proposals.filter((p) => p.status !== "formed");
  return (
    <section className="ko-page">
      <div className="page-heading">
        <p className="eyebrow">仲間とつくる次の旅</p>
        <h1>講を見つける</h1>
        <p>
          行きたい場所と、好きなこと。
          <br />
          重なる仲間と、次の旅を。
        </p>
        <button
          className="text-button"
          disabled={!!busy}
          onClick={() => void reload()}
        >
          <Icon name="refresh" />
          提案と旅の計画を更新
        </button>
      </div>
      <div className="journey-invite">
        <div>
          <span className="small-label">
            {community?.name || "コミュニティを選んでください"}
          </span>
          <h2>
            「行ってみたい」を
            <br />
            持ち寄ろう。
          </h2>
          <p>同じ好みを持つ、参加に同意した仲間から候補を探します。</p>
        </div>
        <button
          className="button primary"
          disabled={!community}
          onClick={() => {
            setError("");
            setCreating(true);
          }}
        >
          <Icon name="plus" />
          仲間と旅を考える
        </button>
      </div>
      {!creating && <ErrorBox message={error} />}
      <p className="success-text" role="status">
        {message}
      </p>
      <div className="section-title">
        <h2>届いている提案</h2>
        <button className="text-button" onClick={onPreferences}>
          好みと参加の許可 <Icon name="arrow" />
        </button>
      </div>
      {active.length === 0 ? (
        <Empty title="まだ提案はありません">
          <p>好みと参加の許可を設定して、仲間と旅を考えてみましょう。</p>
        </Empty>
      ) : (
        active.map((p) => (
          <article
            className={`proposal-card ${p.status === "invalidated" ? "inactive" : ""}`}
            key={p.id}
          >
            <div className="proposal-heading">
              <span className="small-label">
                {p.status === "invalidated"
                  ? "この提案は取り下げられました"
                  : "参加を確認しています"}
              </span>
              <h2>{p.purpose}</h2>
              <p>{p.trip.title}</p>
            </div>
            <div className="proposal-photo">
              <LocalPhoto src={tripCover(p.trip.cover_key)} alt={p.trip.area} />
              <span className="photo-caption">
                <Icon name="pin" />
                {p.trip.area}
              </span>
            </div>
            <div className="proposal-content">
              <p className="reason">
                <Icon name="leaf" />
                {p.reason}
              </p>
              <div className="candidate-list">
                {p.participants.map((m) => (
                  <div className="candidate" key={m.id}>
                    <Avatar user={m} />
                    <div>
                      <strong>{m.name}</strong>
                      <Tags ids={m.common_tags} tags={tags} />
                    </div>
                    <span
                      className={`response ${m.response === "accepted" ? "yes" : ""}`}
                    >
                      {m.response === "accepted"
                        ? "参加する"
                        : m.response === "unavailable"
                          ? "確認できません"
                          : "確認中"}
                    </span>
                  </div>
                ))}
              </div>
              {p.status === "pending" && p.my_response === "pending" ? (
                <div className="action-pair">
                  <button
                    className="button secondary"
                    disabled={!!busy}
                    onClick={() => void respond(p, "declined")}
                  >
                    今回は見送る
                  </button>
                  <button
                    className="button primary"
                    disabled={!!busy}
                    onClick={() => void respond(p, "accepted")}
                  >
                    {busy === p.id ? "送信中…" : "この旅に参加する"}
                    <Icon name="check" />
                  </button>
                </div>
              ) : (
                <p className="muted">
                  {p.status === "invalidated"
                    ? "参加条件が変わりました。新しい提案から、もう一度検討できます。"
                    : p.my_response === "accepted"
                      ? "あなたは参加する意思を伝えています。ほかの仲間の回答を待っています。"
                      : "あなたは今回は見送っています。"}
                </p>
              )}
            </div>
          </article>
        ))
      )}
      <div className="section-title">
        <h2>旅じたく中の講</h2>
        <span className="count-pill">{groups.length}</span>
      </div>
      {groups.length === 0 ? (
        <div className="quiet-note">
          <Icon name="people" />
          <p>
            候補の全員が「参加する」を選ぶと、ここで行程と役割を相談できます。
          </p>
        </div>
      ) : (
        groups.map((g) => (
          <GroupPanel key={g.id} group={g} user={user} onRefresh={onRefresh} />
        ))
      )}
      {creating && (
        <Modal
          title="仲間と旅を考える"
          onClose={() => setCreating(false)}
          busy={!!busy}
          wide
        >
          <p className="muted">
            {community?.name}
            の中で探します。好みの利用・表示・候補参加を許可した人だけが対象です。
          </p>
          <ErrorBox message={error} />
          <label className="field">
            どんな旅にしたい？
            <input
              autoFocus
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              maxLength={120}
              placeholder="例：軽井沢でカフェと森を歩く"
              disabled={!!busy}
            />
          </label>
          <fieldset className="trip-choices" disabled={!!busy}>
            <legend>行き先の候補</legend>
            {trips.map((t) => (
              <label
                key={t.id}
                className={`trip-choice ${tripId === t.id ? "selected" : ""}`}
              >
                <input
                  type="radio"
                  name="trip"
                  checked={tripId === t.id}
                  onChange={() => {
                    setTripId(t.id);
                    if (!selected.length) setSelected(t.tags);
                  }}
                />
                <LocalPhoto src={tripCover(t.cover_key)} />
                <span>
                  <strong>{t.title}</strong>
                  <small>
                    {t.area} · {t.duration === "day" ? "日帰り" : "1泊"} · 目安
                    {t.budget.toLocaleString()}円
                  </small>
                </span>
              </label>
            ))}
          </fieldset>
          <TagPicker
            tags={tags}
            value={selected}
            onChange={setSelected}
            disabled={!!busy}
            label="仲間と楽しみたいこと"
          />
          <div className="field-row">
            <label className="field">
              自分を含めた人数
              <Choice
                value={size}
                onChange={(e) => setSize(Number(e.target.value))}
                disabled={!!busy}
              >
                {[3, 4, 5, 6].map((n) => (
                  <option key={n} value={n}>
                    {n}人
                  </option>
                ))}
              </Choice>
            </label>
            <label className="field">
              出発日の希望 <span className="optional">任意</span>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                disabled={!!busy}
              />
            </label>
          </div>
          <p className="muted">
            候補は参加の確約ではありません。一人ひとりが参加・見送りを選べます。費用は企画用の目安です。
          </p>
          <button
            className="button primary full"
            disabled={!!busy || !purpose.trim() || !selected.length || !tripId}
            onClick={() => void create()}
          >
            {busy ? "仲間を探しています…" : "共通の好みから仲間を探す"}
            <Icon name="arrow" />
          </button>
        </Modal>
      )}
    </section>
  );
}
