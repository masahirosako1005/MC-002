import { choiceValue, errorMessage } from "./validation";
import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import Choice from "./Choice";
import { Empty, ErrorBox, Icon, Modal } from "./ui";
import { useRequestKey } from "./marketplace-ui";
import { reflectionAspects, reflectionSentiments } from "./reflection-types";
import type {
  Reflection,
  ReflectionMessage,
  ReflectionOptions,
  ReflectionValue,
} from "./reflection-types";
import "./reflections.css";

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
const todayInJapan = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
const messageDate = (value: string) =>
  new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
const extractionLabel = {
  waiting: "同意・利用確認待ち",
  auto_included: "自動集計に使用中",
  author_corrected: "本人が訂正した内容を使用",
  excluded: "集計には使いません",
};

function StartReflection({
  circleId,
  options,
  onClose,
  onSaved,
}: {
  circleId: string;
  options: ReflectionOptions["items"];
  onClose: () => void;
  onSaved: (id: string) => void;
}) {
  const [invitationId, setInvitationId] = useState("");
  const [endedOn, setEndedOn] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const alive = useAlive();
  const key = useRequestKey();
  const selected = options.find((item) => item.invitation_id === invitationId);
  const today = todayInJapan();
  async function save() {
    setBusy(true);
    setError("");
    const payload = {
      invitation_id: invitationId,
      ended_on: endedOn,
      trip_finished: true,
    };
    try {
      const result = await api<Reflection>(
        `/circles/${circleId}/reflections`,
        "POST",
        { ...payload, client_request_id: key(payload) },
      );
      if (alive.current) onSaved(result.id);
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <Modal title="旅行後の振り返りをひらく" onClose={onClose} busy={busy}>
      <div className="reflection-form">
        <ErrorBox message={error} />
        <p className="reflection-note">
          実際に利用した事業者について、旅行を終えた仲間で振り返ります。参加依頼や見積の確認だけでは、利用済みにはなりません。
        </p>
        <label className="field">
          振り返る事業者
          <Choice
            value={invitationId}
            disabled={busy}
            onChange={(event) => {
              setInvitationId(event.target.value);
              setConfirmed(false);
            }}
          >
            <option value="">事業者を選ぶ</option>
            {options.map((item) => (
              <option key={item.invitation_id} value={item.invitation_id}>
                {item.provider.name} · {item.plan_title}
              </option>
            ))}
          </Choice>
        </label>
        <label className="field">
          旅行を終えた日
          <input
            type="date"
            value={endedOn}
            min={selected?.earliest_end_on}
            max={today}
            disabled={busy}
            onChange={(event) => {
              setEndedOn(event.target.value);
              setConfirmed(false);
            }}
          />
        </label>
        <label className="reflection-check">
          <input
            type="checkbox"
            checked={confirmed}
            disabled={busy || !selected}
            onChange={(event) => setConfirmed(event.target.checked)}
          />
          <span>この事業者を利用する旅行が終了したことを確認しました。</span>
        </label>
        <p className="reflection-note">
          講の旅行者全員が対象です。実際の利用と参考集計への同意は、一人ひとりが別に確認します。
        </p>
        <button
          className="button primary full"
          disabled={
            busy ||
            !selected ||
            !confirmed ||
            !endedOn ||
            endedOn > today ||
            endedOn < (selected?.earliest_end_on || "")
          }
          onClick={() => void save()}
        >
          {busy ? "振り返りをひらいています…" : "旅行終了を記録して振り返る"}
        </button>
      </div>
    </Modal>
  );
}

function MessageEditor({
  message,
  mode,
  onClose,
  onSaved,
}: {
  message: ReflectionMessage;
  mode: "body" | "review" | "delete";
  onClose: () => void;
  onSaved: () => void;
}) {
  const [body, setBody] = useState(message.body);
  const [values, setValues] = useState<ReflectionValue[]>(
    reflectionAspects.map(({ id }) => ({
      aspect_id: id,
      sentiment:
        message.extraction.effective.find((item) => item.aspect_id === id)
          ?.sentiment || "excluded",
    })),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const alive = useAlive();
  async function save(exclude = false) {
    setBusy(true);
    setError("");
    try {
      if (mode === "delete")
        await api(`/reflection-messages/${message.id}`, "DELETE", {
          version: message.version,
        });
      else if (mode === "body")
        await api(`/reflection-messages/${message.id}`, "PUT", {
          body,
          version: message.version,
        });
      else
        await api(`/reflection-messages/${message.id}/review`, "PUT", {
          version: message.version,
          source_version: message.source_version,
          values: exclude
            ? reflectionAspects.map(({ id }) => ({
                aspect_id: id,
                sentiment: "excluded",
              }))
            : values,
        });
      if (alive.current) onSaved();
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <Modal
      title={
        mode === "body"
          ? "自分の振り返りを編集する"
          : mode === "delete"
            ? "この振り返りを削除しますか？"
            : "自分の抽出結果を見直す"
      }
      onClose={onClose}
      busy={busy}
    >
      <div className="reflection-message-editor">
        <ErrorBox message={error} />
        {mode === "body" ? (
          <>
            <p className="reflection-note">
              保存すると以前の抽出結果と訂正を取り消し、編集した発言から整理し直します。
            </p>
            <label className="field">
              振り返りの内容
              <textarea
                rows={5}
                maxLength={1000}
                value={body}
                disabled={busy}
                onChange={(event) => setBody(event.target.value)}
              />
            </label>
          </>
        ) : mode === "delete" ? (
          <p>
            自分の発言と、それに基づく抽出・訂正結果を削除します。参考集計にも反映されなくなります。
          </p>
        ) : (
          <>
            <p className="reflection-message-body">{message.body}</p>
            <p className="reflection-note">
              自分の体験に合う観点だけを残してください。使わない観点は集計から除外できます。
            </p>
            {reflectionAspects.map((aspect) => (
              <label className="field" key={aspect.id}>
                {aspect.label}
                <Choice
                  value={
                    values.find((item) => item.aspect_id === aspect.id)
                      ?.sentiment || "excluded"
                  }
                  disabled={busy}
                  onChange={(event) =>
                    setValues((current) =>
                      current.map((item) =>
                        item.aspect_id === aspect.id
                          ? {
                              ...item,
                              sentiment: choiceValue(event.target.value,
                                ["positive", "negative", "mixed", "excluded"], item.sentiment),
                            }
                          : item,
                      ),
                    )
                  }
                >
                  {Object.entries(reflectionSentiments).map(
                    ([value, label]) => (
                      <option value={value} key={value}>
                        {label}
                      </option>
                    ),
                  )}
                </Choice>
              </label>
            ))}
          </>
        )}
        <button
          className={`button ${mode === "delete" ? "danger-button" : "primary"} full`}
          disabled={busy || (mode === "body" && !body.trim())}
          onClick={() => void save()}
        >
          {busy
            ? "保存しています…"
            : mode === "delete"
              ? "発言と抽出結果を削除"
              : mode === "body"
                ? "発言を保存して整理し直す"
                : "この訂正を保存"}
        </button>
        {mode === "review" && (
          <button
            className="text-button danger"
            disabled={busy}
            onClick={() => void save(true)}
          >
            この発言を参考集計から除外
          </button>
        )}
      </div>
    </Modal>
  );
}

function ReflectionChat({
  reflection,
  onClose,
  onChanged,
}: {
  reflection: Reflection;
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState<{
    message: ReflectionMessage;
    mode: "body" | "review" | "delete";
  } | null>(null);
  const alive = useAlive();
  const key = useRequestKey();
  const history = useRef<HTMLDivElement>(null);
  const latestId = reflection.messages.at(-1)?.id;
  useEffect(() => {
    if (history.current)
      history.current.scrollTop =
        latestId || error ? history.current.scrollHeight : 0;
  }, [latestId, error]);
  async function send() {
    setBusy(true);
    setError("");
    const payload = { body };
    try {
      await api(`/reflections/${reflection.id}/messages`, "POST", {
        ...payload,
        client_request_id: key(payload),
      });
      if (!alive.current) return;
      key.reset();
      setBody("");
      await onChanged();
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <Modal
      title="旅行後の振り返り"
      onClose={onClose}
      busy={busy}
      variant="conversation"
      wide
    >
      <section className="conversation" aria-label="旅行後の専用振り返り会話">
        <div
          className="conversation-history"
          ref={history}
          role="region"
          tabIndex={0}
          aria-label="振り返りの履歴と共有条件"
        >
          <div className="reflection-chat-context">
            <h3>{reflection.provider.name}を利用した旅</h3>
            <p className="reflection-note">
              この専用会話は対象の旅行者だけに見えます。事業者には原文を共有しません。通常の内輪・事業者との会話や写真は解析しません。
            </p>
            <p className="reflection-status">
              {reflection.ready_for_analysis
                ? "明確に読み取れる体験を、自動で参考集計へ反映します。"
                : "現在は集計を保留しています。全員の利用確認・同意がそろうまでは解析しません。"}
            </p>
          </div>
          {!reflection.messages.length && (
            <Empty title="振り返りの発言はありません">
              <p>
                利用した事業者の名前と、実際の案内・対応・体験・価格について書けます。健康や家族、連絡先などの私的な内容は含めないでください。
              </p>
            </Empty>
          )}
          {reflection.messages.map((message) => (
            <article className="reflection-message" key={message.id}>
              <div className="reflection-message-head">
                <strong>{message.author.name}</strong>
                <time dateTime={message.created_at}>
                  {messageDate(message.created_at)}
                </time>
              </div>
              <p className="reflection-message-body">{message.body}</p>
              <div className="reflection-extraction">
                <strong>
                  {message.extraction.status === "author_corrected" &&
                  !message.extraction.effective.some(
                    (value) => value.sentiment !== "excluded",
                  )
                    ? "本人が参考集計から除外"
                    : extractionLabel[message.extraction.status]}
                </strong>
                <p>{message.extraction.reason}</p>
                {message.extraction.effective.length > 0 && (
                  <ul className="reflection-values">
                    {message.extraction.effective
                      .filter((item) => item.sentiment !== "excluded")
                      .map((item) => (
                        <li key={item.aspect_id}>
                          <span>
                            {
                              reflectionAspects.find(
                                (aspect) => aspect.id === item.aspect_id,
                              )?.label
                            }
                          </span>
                          <span>{reflectionSentiments[item.sentiment]}</span>
                        </li>
                      ))}
                  </ul>
                )}
              </div>
              {message.is_mine && (
                <div className="reflection-actions">
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => setEditor({ message, mode: "body" })}
                  >
                    発言を編集
                  </button>
                  {message.extraction.can_correct && (
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => setEditor({ message, mode: "review" })}
                    >
                      抽出結果を見直す
                    </button>
                  )}
                  <button
                    className="text-button danger"
                    disabled={busy}
                    onClick={() => setEditor({ message, mode: "delete" })}
                  >
                    削除
                  </button>
                </div>
              )}
            </article>
          ))}
          <ErrorBox message={error} />
        </div>
        <form
          className="message-form"
          onSubmit={(event) => {
            event.preventDefault();
            void send();
          }}
        >
          <label
            className="sr-only"
            htmlFor={`reflection-body-${reflection.id}`}
          >
            振り返りに送るメッセージ
          </label>
          <textarea
            id={`reflection-body-${reflection.id}`}
            value={body}
            disabled={busy}
            maxLength={1000}
            rows={2}
            placeholder="利用した事業者での体験を振り返る"
            onChange={(event) => setBody(event.target.value)}
          />
          <button className="button primary" disabled={busy || !body.trim()}>
            {busy ? "送信中…" : "送る"}
            <Icon name="arrow" />
          </button>
        </form>
      </section>
      {editor && (
        <MessageEditor
          key={`${editor.message.id}-${editor.mode}`}
          {...editor}
          onClose={() => setEditor(null)}
          onSaved={() => {
            setEditor(null);
            void onChanged();
          }}
        />
      )}
    </Modal>
  );
}

function ReflectionDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const [data, setData] = useState<Reflection | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [chat, setChat] = useState(false);
  const [action, setAction] = useState<
    | "usage"
    | "cancel-usage"
    | "consent"
    | "revoke"
    | "refresh"
    | "completion"
    | null
  >(null);
  const [confirmed, setConfirmed] = useState(false);
  const alive = useAlive();
  async function load() {
    try {
      const result = await api<Reflection>(`/reflections/${id}`);
      if (alive.current) {
        setData(result);
        setError("");
      }
    } catch (e) {
      if (alive.current) {
        setData(null);
        setChat(false);
        setError(errorMessage(e));
      }
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [id]);
  function ask(next: typeof action) {
    setConfirmed(false);
    setError("");
    setAction(next);
  }
  async function update() {
    if (!data || !action) return;
    setBusy(true);
    setError("");
    const route =
      action === "usage" || action === "cancel-usage"
        ? "participation"
        : action === "consent" || action === "revoke"
          ? "consent"
          : action === "refresh"
            ? "participants-refresh"
            : "completion";
    const payload =
      route === "participation"
        ? { used_service: action === "usage", version: data.my_state.version }
        : route === "consent"
          ? { allowed: action === "consent", version: data.my_state.version }
          : route === "completion"
            ? { trip_finished: !data.trip_finished, version: data.version }
            : { version: data.version };
    try {
      const result = await api<Reflection>(
        `/reflections/${id}/${route}`,
        route === "participants-refresh" ? "POST" : "PUT",
        payload,
      );
      if (alive.current) {
        setData(result);
        setAction(null);
      }
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  if (loading) return <output className="page-load-status">振り返りをひらいています…</output>;
  return (
    <section className="reflection-detail">
      <button className="text-button" onClick={onBack}>
        ← 振り返りの一覧へ
      </button>
      <ErrorBox message={error} />
      {data && (
        <>
          <header>
            <p className="eyebrow">旅行後の振り返り</p>
            <h2>{data.provider.name}</h2>
            <p className="reflection-note">
              旅行終了日：{data.ended_on}（本人申告）
            </p>
          </header>
          <div className="reflection-card">
            <p className="reflection-status">
              {data.ready_for_analysis
                ? "同意がそろい、参考集計に反映しています"
                : "参考集計を保留しています"}
            </p>
            <div className="reflection-counts">
              <span>
                実利用の確認 {data.usage_confirmed_count}/{data.target_count}人
              </span>
              <span>
                用途への同意 {data.consented_count}/{data.target_count}人
              </span>
            </div>
            {!data.trip_finished && (
              <p className="reflection-note">
                旅行終了の申告が取り消されています。振り返りは参考集計に使いません。
              </p>
            )}
            {!data.participant_set_current && (
              <p className="reflection-note">
                講の参加者が変わりました。現在の全旅行者を確認し、利用と同意を一人ひとり確認し直すまで集計しません。
              </p>
            )}
            <details>
              <summary>対象となる旅行者</summary>
              <ul className="reflection-people">
                {data.participants.map((person) => (
                  <li key={person.user.id}>
                    <strong>{person.user.name}</strong>
                    <span>
                      {person.used_service ? "利用確認済み" : "利用未確認"} ·{" "}
                      {person.consented ? "同意済み" : "同意していない"}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          </div>
          <section className="reflection-card">
            <h3>自分の確認と同意</h3>
            <p className="reflection-note">
              実際の利用は自分の申告です。予約の成立や第三者による認証を表すものではありません。
            </p>
            <div className="reflection-actions">
              {data.my_state.used_service ? (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() => ask("cancel-usage")}
                >
                  自分の利用確認を取り消す
                </button>
              ) : (
                <button
                  className="button secondary"
                  disabled={
                    busy || !data.participant_set_current || !data.trip_finished
                  }
                  onClick={() => ask("usage")}
                >
                  自分が利用したことを確認
                </button>
              )}
              {data.my_state.consented ? (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() => ask("revoke")}
                >
                  参考集計への同意を撤回
                </button>
              ) : (
                <button
                  className="button primary"
                  disabled={
                    busy ||
                    !data.my_state.used_service ||
                    !data.participant_set_current ||
                    !data.trip_finished
                  }
                  onClick={() => ask("consent")}
                >
                  参考集計への同意を確認
                </button>
              )}
            </div>
            <p className="reflection-note">{data.usage_notice}</p>
          </section>
          <button className="button primary full" onClick={() => setChat(true)}>
            この旅を振り返って話す
            <Icon name="arrow" />
          </button>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void load()}
          >
            <Icon name="refresh" />
            振り返りを更新
          </button>
          {data.can_manage && (
            <div className="reflection-actions">
              {!data.participant_set_current && (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() => ask("refresh")}
                >
                  対象者を確認し直す
                </button>
              )}
              <button
                className="text-button danger"
                disabled={busy}
                onClick={() => ask("completion")}
              >
                {data.trip_finished
                  ? "旅行終了の申告を取り消す"
                  : "旅行終了を確認し直す"}
              </button>
            </div>
          )}
          {chat && (
            <ReflectionChat
              reflection={data}
              onClose={() => setChat(false)}
              onChanged={load}
            />
          )}
          {action && (
            <Modal
              title={
                action === "consent"
                  ? "参考集計への同意"
                  : action === "usage"
                    ? "実際の利用を確認"
                    : action === "revoke"
                      ? "同意を撤回しますか？"
                      : action === "cancel-usage"
                        ? "利用確認を取り消しますか？"
                        : action === "refresh"
                          ? "全員の確認をやり直しますか？"
                          : "旅行終了の申告を変更"
              }
              onClose={() => setAction(null)}
              busy={busy}
            >
              <div className="reflection-consent">
                <ErrorBox message={error} />
                {action === "consent" ? (
                  <>
                    <p>
                      この振り返りから明確に読み取れる事業者の体験を自動で参考集計へ反映し、おすすめの補助に使います。公開するのは件数と定型の匿名要点だけです。
                    </p>
                    <p className="reflection-note">
                      対象者全員が利用確認・同意を済ませた専用会話だけを使います。原文、個人名、講名、日付や位置は公開しません。発言ごとの追加承認は行わず、自動で整理した内容を使います。後から自分の結果を訂正・除外でき、同意も撤回できます。
                    </p>
                    <label className="reflection-check">
                      <input
                        type="checkbox"
                        checked={confirmed}
                        disabled={busy}
                        onChange={(event) => setConfirmed(event.target.checked)}
                      />
                      <span>
                        用途と公開範囲を確認し、この振り返りの自動参考集計に同意します。
                      </span>
                    </label>
                  </>
                ) : action === "usage" ? (
                  <label className="reflection-check">
                    <input
                      type="checkbox"
                      checked={confirmed}
                      disabled={busy}
                      onChange={(event) => setConfirmed(event.target.checked)}
                    />
                    <span>
                      {data.provider.name}
                      のサービスを、この旅行で自分が実際に利用しました。
                    </span>
                  </label>
                ) : (
                  <p>
                    {action === "revoke"
                      ? "同意を撤回すると、この旅の参考集計を保留します。振り返りの原文は対象の旅行者に引き続き見えます。"
                      : action === "cancel-usage"
                        ? "自分の利用確認と同意を取り消し、この旅の参考集計を保留します。"
                        : action === "refresh"
                          ? "現在の全旅行者を対象にし、全員の実利用確認と同意を初めからやり直します。代表が他の人の同意を代わりに行うことはできません。"
                          : data.trip_finished
                            ? "旅行終了の申告を取り消すと、この旅の参考集計を無効にします。"
                            : "旅行終了を申告し直します。全員の利用確認と同意を初めからやり直します。"}
                  </p>
                )}
                <button
                  className="button primary full"
                  disabled={
                    busy ||
                    ((action === "usage" || action === "consent") && !confirmed)
                  }
                  onClick={() => void update()}
                >
                  {busy
                    ? "保存しています…"
                    : action === "consent"
                      ? "同意を保存"
                      : action === "usage"
                        ? "自分の実利用を記録"
                        : action === "revoke"
                          ? "同意を撤回する"
                          : action === "refresh"
                            ? "全員の確認をやり直す"
                            : "変更を保存"}
                </button>
              </div>
            </Modal>
          )}
        </>
      )}
    </section>
  );
}

export default function ReflectionWorkspace({
  circleId,
  canManage,
}: {
  circleId: string;
  canManage: boolean;
}) {
  const [data, setData] = useState<ReflectionOptions | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const alive = useAlive();
  async function load() {
    setError("");
    try {
      const result = await api<ReflectionOptions>(
        `/circles/${circleId}/reflection-options`,
      );
      if (alive.current) setData(result);
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [circleId]);
  if (selectedId)
    return (
      <ReflectionDetail
        key={selectedId}
        id={selectedId}
        onBack={() => {
          setSelectedId("");
          void load();
        }}
      />
    );
  return (
    <section className="reflection-workspace">
      <header>
        <h2>旅行後の振り返り</h2>
        <p className="reflection-note">
          実際に利用した事業者での体験を、仲間と振り返ります。参考集計には一人ひとりの利用確認と同意が必要です。
        </p>
      </header>
      <ErrorBox message={error} />
      {loading ? (
        <output className="page-load-status">振り返りを読み込んでいます…</output>
      ) : (
        data && (
          <>
            {data.reflections.map((item) => (
              <article className="reflection-card" key={item.id}>
                <h3>{item.provider.name}</h3>
                <p className="reflection-note">旅行終了日：{item.ended_on}</p>
                <p className="reflection-status">
                  {item.ready_for_analysis
                    ? "参考集計に反映中"
                    : "参考集計は保留中"}
                </p>
                <p className="reflection-note">
                  利用確認 {item.usage_confirmed_count}/{item.target_count}人 ·
                  同意 {item.consented_count}/{item.target_count}人
                </p>
                <button
                  className="button secondary full"
                  onClick={() => setSelectedId(item.id)}
                >
                  この旅の振り返りをひらく
                  <Icon name="arrow" />
                </button>
              </article>
            ))}
            {canManage && data.items.length > 0 && (
              <button
                className="button primary full"
                onClick={() => setCreating(true)}
              >
                旅行を終えて振り返る
                <Icon name="plus" />
              </button>
            )}
            {!data.reflections.length && !data.items.length && (
              <Empty title="振り返りの対象はありません">
                <p>
                  事業者が講への参加を承諾し、そのサービスを実際に利用した旅行が対象です。候補保存や相談だけで利用実績にはなりません。
                </p>
              </Empty>
            )}
            {!canManage &&
              !data.reflections.length &&
              data.items.length > 0 && (
                <p className="reflection-note">
                  講の代表が旅行終了を記録すると、各自の利用確認と振り返りを始められます。
                </p>
              )}
          </>
        )
      )}
      {creating && data && (
        <StartReflection
          circleId={circleId}
          options={data.items}
          onClose={() => setCreating(false)}
          onSaved={(id) => {
            setCreating(false);
            setSelectedId(id);
          }}
        />
      )}
    </section>
  );
}
