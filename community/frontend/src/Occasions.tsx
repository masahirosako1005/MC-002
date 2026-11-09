import { choiceValue, errorMessage } from "./validation";
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
import { ExperienceReference } from "./ExperienceReference";
import type { ProviderPlan } from "./marketplace-types";
import type { Tag } from "./types";
import type {
  MyOccasions,
  Occasion,
  OccasionCircle,
  OccasionDate,
  OccasionSharing,
  OccasionSuggestion,
  SharedOccasion,
} from "./occasion-types";
import "./occasions.css";

function useAlive() {
  const ref = useRef(true);
  useEffect(() => {
    ref.current = true;
    return () => {
      ref.current = false;
    };
  }, []);
  return ref;
}
function dateLabel(value: OccasionDate) {
  return `${value.repeats_annually ? "毎年 " : `${value.year}年 `}${value.month}月${value.day}日`;
}
function candidateNotice() {
  return "記念日の削除・編集、共有や提案の取消で、この提案だけから保存した候補は講の一覧から非表示になります。同じプランを通常の候補として別に保存している場合は残ります。すでに送った事業者への招待は取り消されません。";
}

function OccasionEditor({
  initial,
  hasBirthday,
  onClose,
  onSaved,
}: {
  initial: Occasion | null;
  hasBirthday: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [kind, setKind] = useState<OccasionDate["kind"]>(
    initial?.kind || (hasBirthday ? "anniversary" : "birthday"),
  );
  const [name, setName] = useState(
    initial?.kind === "anniversary" ? initial.name : "",
  );
  const [month, setMonth] = useState(initial ? String(initial.month) : "");
  const [day, setDay] = useState(initial ? String(initial.day) : "");
  const [annual, setAnnual] = useState(initial?.repeats_annually ?? true);
  const [year, setYear] = useState(initial?.year ? String(initial.year) : "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const alive = useAlive();
  const key = useRequestKey();
  const repeats = kind === "birthday" || annual;
  const yearNumber = repeats ? 2000 : Number(year);
  const probe = new Date(0);
  probe.setUTCFullYear(yearNumber, Number(month) - 1, Number(day));
  const validDate =
    !!month &&
    !!day &&
    yearNumber >= 1900 &&
    yearNumber <= 9999 &&
    probe.getUTCFullYear() === yearNumber &&
    probe.getUTCMonth() === Number(month) - 1 &&
    probe.getUTCDate() === Number(day);
  async function save() {
    setBusy(true);
    setError("");
    const payload = {
      kind,
      name: kind === "birthday" ? "誕生日" : name.trim(),
      month: Number(month),
      day: Number(day),
      repeats_annually: repeats,
      year: repeats ? null : Number(year),
    };
    try {
      await api(
        initial ? `/me/occasions/${initial.id}` : "/me/occasions",
        initial ? "PUT" : "POST",
        initial
          ? { ...payload, version: initial.version }
          : { ...payload, client_request_id: key(payload) },
      );
      if (alive.current) onSaved();
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <Modal
      title={initial ? "誕生日・記念日を編集" : "誕生日・記念日を登録"}
      onClose={onClose}
      busy={busy}
    >
      <form
        className="occasion-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (validDate) void save();
        }}
      >
        <ErrorBox message={error} />
        <label className="field">
          種類
          <Choice
            value={kind}
            disabled={busy || !!initial}
            onChange={(event) =>
              setKind(choiceValue(event.target.value, ["birthday", "anniversary"], kind))
            }
          >
            {(!hasBirthday || initial?.kind === "birthday") && (
              <option value="birthday">誕生日</option>
            )}
            <option value="anniversary">記念日</option>
          </Choice>
        </label>
        {kind === "anniversary" && (
          <label className="field">
            記念日の名前
            <input
              value={name}
              required
              maxLength={60}
              disabled={busy}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
        )}
        <div className="occasion-month-day">
          <label className="field">
            月
            <Choice
              value={month}
              disabled={busy}
              onChange={(event) => setMonth(event.target.value)}
            >
              <option value="">月を選ぶ</option>
              {Array.from({ length: 12 }, (_, index) => (
                <option key={index + 1} value={String(index + 1)}>
                  {index + 1}月
                </option>
              ))}
            </Choice>
          </label>
          <label className="field">
            日
            <Choice
              value={day}
              disabled={busy}
              onChange={(event) => setDay(event.target.value)}
            >
              <option value="">日を選ぶ</option>
              {Array.from({ length: 31 }, (_, index) => (
                <option key={index + 1} value={String(index + 1)}>
                  {index + 1}日
                </option>
              ))}
            </Choice>
          </label>
        </div>
        {kind === "birthday" ? (
          <p className="occasion-note">
            生年は登録しません。2月29日は、うるう年でない年の提案では2月28日として扱います。
          </p>
        ) : (
          <>
            <label className="field">
              繰り返し
              <Choice
                value={annual ? "annual" : "once"}
                disabled={busy}
                onChange={(event) => setAnnual(event.target.value === "annual")}
              >
                <option value="annual">毎年</option>
                <option value="once">一度だけ</option>
              </Choice>
            </label>
            {!annual && (
              <label className="field">
                年
                <input
                  type="number"
                  min={1900}
                  max={9999}
                  inputMode="numeric"
                  required
                  value={year}
                  disabled={busy}
                  onChange={(event) => setYear(event.target.value)}
                />
              </label>
            )}
          </>
        )}
        {!!month && !!day && (!repeats ? !!year : true) && !validDate && (
          <p className="occasion-note" role="status">
            存在する日付を選んでください。
          </p>
        )}
        <p className="occasion-privacy">
          {initial
            ? "編集した名前と日付は、現在共有している講にも反映されます。"
            : "登録時は自分だけが見られます。日付の共有と提案への利用は、保存後に別々に設定できます。"}
        </p>
        {initial && <p className="occasion-note">{candidateNotice()}</p>}
        <button
          className="button primary full"
          disabled={
            busy || !validDate || (kind === "anniversary" && !name.trim())
          }
        >
          {busy ? "保存しています…" : initial ? "変更を保存" : "自分だけに保存"}
        </button>
      </form>
    </Modal>
  );
}

function SharingEditor({
  occasion,
  circles,
  onClose,
  onSaved,
}: {
  occasion: Occasion;
  circles: OccasionCircle[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [sharing, setSharing] = useState<OccasionSharing[]>(
    circles.map((circle) => ({
      circle_id: circle.id,
      circle_title: circle.title,
      share_date:
        occasion.sharing.find((item) => item.circle_id === circle.id)
          ?.share_date || false,
      suggest:
        occasion.sharing.find((item) => item.circle_id === circle.id)
          ?.suggest || false,
    })),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const alive = useAlive();
  function change(id: string, field: "share_date" | "suggest", value: boolean) {
    setSharing((current) =>
      current.map((item) =>
        item.circle_id === id
          ? {
              ...item,
              [field]: value,
              ...(field === "share_date" && !value ? { suggest: false } : {}),
            }
          : item,
      ),
    );
  }
  async function save() {
    setBusy(true);
    setError("");
    try {
      await api(`/me/occasions/${occasion.id}/sharing`, "PUT", {
        version: occasion.version,
        sharing: sharing
          .filter((item) => item.share_date)
          .map(({ circle_id, share_date, suggest }) => ({
            circle_id,
            share_date,
            suggest,
          })),
      });
      if (alive.current) onSaved();
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <Modal title="共有と提案の設定" onClose={onClose} busy={busy}>
      <div className="occasion-settings">
        <ErrorBox message={error} />
        <h3>
          {occasion.name} · {dateLabel(occasion)}
        </h3>
        <p className="occasion-privacy">
          日付を共有すると、選んだ講の参加者に登録者名、記念日の名前、月日
          {!occasion.repeats_annually && "と年"}
          が表示されます。事業者への共有相談には送りません。
        </p>
        <p className="occasion-note">
          提案を有効にすると、今日から30日以内の日付に合う公開プランを講の中に表示します。外部への通知や、事業者への招待は行いません。
        </p>
        {sharing.length ? (
          sharing.map((item) => (
            <section className="occasion-sharing-row" key={item.circle_id}>
              <strong>{item.circle_title}</strong>
              <label className="occasion-check">
                <input
                  type="checkbox"
                  checked={item.share_date}
                  disabled={busy}
                  onChange={(event) =>
                    change(item.circle_id, "share_date", event.target.checked)
                  }
                />
                <span>この講に名前と日付を共有する</span>
              </label>
              <label className="occasion-check">
                <input
                  type="checkbox"
                  checked={item.suggest}
                  disabled={busy || !item.share_date}
                  onChange={(event) =>
                    change(item.circle_id, "suggest", event.target.checked)
                  }
                />
                <span>この記念日に合うプランを講に提案する</span>
              </label>
            </section>
          ))
        ) : (
          <p className="occasion-note">
            共有できる参加中の講はありません。保存した日付は自分だけに表示されます。
          </p>
        )}
        <p className="occasion-note">
          {candidateNotice()}{" "}
          共有を再開しても、以前の提案から保存した候補は自動で復活しません。
        </p>
        <button
          className="button primary full"
          disabled={busy}
          onClick={() => void save()}
        >
          {busy ? "保存しています…" : "共有と提案の設定を保存"}
        </button>
      </div>
    </Modal>
  );
}

function SaveOccasionCandidate({
  suggestion,
  plan,
  circleTitle,
  onClose,
  onSaved,
}: {
  suggestion: OccasionSuggestion;
  plan: ProviderPlan;
  circleTitle: string;
  onClose: () => void;
  onSaved: (circleId: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const key = useRequestKey();
  const alive = useAlive();
  async function save() {
    setBusy(true);
    setError("");
    const payload = {
      plan_id: plan.id,
      plan_version: plan.version,
      ...(suggestion.shared
        ? { occasion_version: suggestion.occasion_version }
        : {}),
    };
    try {
      await api(
        suggestion.shared
          ? `/occasion-suggestions/${suggestion.id}/candidate-cards`
          : `/circles/${suggestion.circle_id}/candidate-cards`,
        "POST",
        {
          ...payload,
          client_request_id: key({ suggestion: suggestion.id, ...payload }),
        },
      );
      if (alive.current) onSaved(suggestion.circle_id);
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <Modal title="プラン候補を講に保存" onClose={onClose} busy={busy}>
      <div className="occasion-form">
        <ErrorBox message={error} />
        <p className="small-label">保存先：{circleTitle}</p>
        <h3>{plan.title}</h3>
        <p>{scheduleLabel(plan)}</p>
        <p className="occasion-privacy">
          {suggestion.shared
            ? "講に保存するカードは公開プランの内容だけです。記念日の名前・日付・登録者や個人の関心を、カードや事業者への招待へ追加しません。"
            : "記念日を共有せず、この公開プランだけを通常の候補として講に保存します。記念日の名前・日付や、個人的なおすすめ理由は保存しません。"}
        </p>
        <p className="occasion-note">
          {suggestion.shared
            ? candidateNotice()
            : "通常の候補として保存するため、後で記念日を削除してもこのプラン候補は残ります。"}
        </p>
        <p className="occasion-note">
          候補の保存では、事業者への招待・予約・実利用にはなりません。
        </p>
        <button
          className="button primary full"
          disabled={busy}
          onClick={() => void save()}
        >
          {busy ? "候補を保存しています…" : "候補を保存して講で話す"}
          <Icon name="arrow" />
        </button>
      </div>
    </Modal>
  );
}

function SuggestedPlans({
  suggestion,
  tags,
  circleTitle,
  onSaved,
}: {
  suggestion: OccasionSuggestion;
  tags: Tag[];
  circleTitle: string;
  onSaved: (circleId: string) => void;
}) {
  const [page, setPage] = useState(0);
  const [detail, setDetail] = useState<ProviderPlan | null>(null);
  const [saving, setSaving] = useState<ProviderPlan | null>(null);
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil(suggestion.candidates.length / 4) - 1),
  );
  return (
    <div className="occasion-plan-list">
      <p className="occasion-note">{suggestion.notice}</p>
      {suggestion.occurrence && (
        <p className="occasion-date">
          対象日：{suggestion.occurrence.occurrence_date}
          {suggestion.occurrence.leap_adjusted && "（今年は2月28日として提案）"}
        </p>
      )}
      {suggestion.candidates.length ? (
        <>
          {suggestion.candidates
            .slice(currentPage * 4, (currentPage + 1) * 4)
            .map((item) => (
              <div key={item.plan.id}>
                <PlanCard
                  plan={item.plan}
                  tags={tags}
                  reason={item.reasons.join("・")}
                  onOpen={() => setDetail(item.plan)}
                  onAdd={() => setSaving(item.plan)}
                />
                <p className="occasion-note">
                  空席・予約可能日・特典は事業者への確認が必要です。
                </p>
                {item.experience_reference && (
                  <ExperienceReference summary={item.experience_reference} />
                )}
                {item.unknowns.length > 0 && (
                  <details>
                    <summary>確認が必要なこと</summary>
                    <ul>
                      {[...new Set(item.unknowns)].map((unknown) => (
                        <li key={unknown}>{unknown}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))}
          {suggestion.candidates.length > 4 && (
            <div className="occasion-pager">
              <button
                className="button secondary"
                disabled={!currentPage}
                onClick={() => setPage(currentPage - 1)}
              >
                前へ
              </button>
              <span>
                {currentPage * 4 + 1}〜
                {Math.min((currentPage + 1) * 4, suggestion.candidates.length)}{" "}
                / {suggestion.candidates.length}件
              </span>
              <button
                className="button secondary"
                disabled={(currentPage + 1) * 4 >= suggestion.candidates.length}
                onClick={() => setPage(currentPage + 1)}
              >
                次へ
              </button>
            </div>
          )}
        </>
      ) : (
        <Empty title="条件に合うプランはありません">
          <p>
            提案は今日から30日以内の日付が対象です。講で確認した日程・人数・予算や、プランの開催日時も照合します。
          </p>
        </Empty>
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
        <SaveOccasionCandidate
          suggestion={suggestion}
          plan={saving}
          circleTitle={circleTitle}
          onClose={() => setSaving(null)}
          onSaved={onSaved}
        />
      )}
    </div>
  );
}

function PrivatePreview({
  occasion,
  circles,
  tags,
  onClose,
  onSaved,
}: {
  occasion: Occasion;
  circles: OccasionCircle[];
  tags: Tag[];
  onClose: () => void;
  onSaved: (circleId: string) => void;
}) {
  const [circleId, setCircleId] = useState("");
  const [data, setData] = useState<OccasionSuggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setData(null);
    setError("");
    setLoading(!!circleId);
    if (!circleId) return undefined;
    api<OccasionSuggestion>(
      `/me/occasions/${occasion.id}/preview?circle_id=${encodeURIComponent(circleId)}`,
    )
      .then((result) => {
        if (active) setData(result);
        return undefined;
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
  }, [occasion.id, circleId]);
  return (
    <Modal title="自分だけでプラン候補を確認" onClose={onClose} wide>
      <div className="occasion-preview">
        <h3>{occasion.name}</h3>
        <p className="occasion-privacy">
          この画面は本人だけに表示します。講を選んでも、日付の共有設定は変わりません。
        </p>
        <label className="field">
          条件を確認する講
          <Choice
            value={circleId}
            onChange={(event) => setCircleId(event.target.value)}
          >
            <option value="">講を選ぶ</option>
            {circles.map((circle) => (
              <option key={circle.id} value={circle.id}>
                {circle.title}
              </option>
            ))}
          </Choice>
        </label>
        {!circles.length && (
          <p className="occasion-note">
            参加中の講がありません。講を作成または参加すると、旅行条件に合うプランを確認できます。
          </p>
        )}
        <ErrorBox message={error} />
        {loading && <p role="status">プラン候補を確認しています…</p>}
        {data && (
          <SuggestedPlans
            key={data.id}
            suggestion={data}
            tags={tags}
            circleTitle={
              circles.find((circle) => circle.id === circleId)?.title ||
              "選択した講"
            }
            onSaved={onSaved}
          />
        )}
      </div>
    </Modal>
  );
}

export default function Occasions({
  tags,
  onOpenCircle,
}: {
  tags: Tag[];
  onOpenCircle: (id: string) => void;
}) {
  const [data, setData] = useState<MyOccasions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Occasion | "new" | null>(null);
  const [sharing, setSharing] = useState<Occasion | null>(null);
  const [preview, setPreview] = useState<Occasion | null>(null);
  const [deleting, setDeleting] = useState<Occasion | null>(null);
  const alive = useAlive();
  async function load() {
    setError("");
    try {
      const result = await api<MyOccasions>("/me/occasions");
      if (alive.current) setData(result);
    } catch (e) {
      if (alive.current) {
        setData(null);
        setError(errorMessage(e));
      }
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function remove() {
    if (!deleting) return;
    setBusy(true);
    setError("");
    try {
      await api(`/me/occasions/${deleting.id}`, "DELETE", {
        version: deleting.version,
      });
      if (alive.current) {
        setDeleting(null);
        await load();
      }
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <section className="occasions">
      <header>
        <h2>誕生日・記念日</h2>
        <p className="occasion-note">
          日付は自分で登録します。共有先と提案への利用は、記念日ごとに選べます。
        </p>
      </header>
      <ErrorBox message={error} />
      <div className="occasion-actions">
        <button
          className="button secondary"
          disabled={loading || !data || data.items.length >= 20}
          onClick={() => setEditing("new")}
        >
          <Icon name="plus" />
          誕生日・記念日を登録
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
      {loading ? (
        <p role="status">誕生日・記念日を読み込んでいます…</p>
      ) : (
        data && (
          <>
            {!data.items.length && (
              <Empty title="登録した日付はありません">
                <p>
                  共有せず、本人だけで日付に合うプラン候補を確認することもできます。
                </p>
              </Empty>
            )}
            {data.items.map((item) => (
              <article className="occasion-card" key={item.id}>
                <h3>{item.name}</h3>
                <p className="occasion-date">{dateLabel(item)}</p>
                <p className="occasion-note">
                  {item.sharing.some((share) => share.share_date)
                    ? `共有先：${item.sharing
                        .filter((share) => share.share_date)
                        .map((share) => share.circle_title)
                        .join("、")}`
                    : "公開範囲：自分だけ"}
                </p>
                <p className="occasion-note">
                  {item.sharing.some((share) => share.suggest)
                    ? `提案する講：${item.sharing
                        .filter((share) => share.suggest)
                        .map((share) => share.circle_title)
                        .join("、")}`
                    : "講へのプラン提案：OFF"}
                </p>
                {item.next_occurrence && (
                  <p className="occasion-note">
                    {item.next_occurrence.days_until === 0
                      ? "今日が対象日です"
                      : `${item.next_occurrence.days_until}日後が対象日です`}
                    {item.next_occurrence.leap_adjusted &&
                      "（今年は2月28日として提案）"}
                  </p>
                )}
                <button
                  className="button secondary full"
                  onClick={() => setSharing(item)}
                >
                  共有と提案の設定
                </button>
                <button
                  className="text-button"
                  onClick={() => setPreview(item)}
                >
                  自分だけで候補を見る
                  <Icon name="arrow" />
                </button>
                <div className="occasion-actions">
                  <button
                    className="text-button"
                    onClick={() => setEditing(item)}
                  >
                    編集
                  </button>
                  <button
                    className="text-button danger"
                    onClick={() => setDeleting(item)}
                  >
                    削除
                  </button>
                </div>
              </article>
            ))}
          </>
        )
      )}
      {editing && data && (
        <OccasionEditor
          initial={editing === "new" ? null : editing}
          hasBirthday={data.items.some((item) => item.kind === "birthday")}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void load();
          }}
        />
      )}
      {sharing && data && (
        <SharingEditor
          occasion={sharing}
          circles={data.circles}
          onClose={() => setSharing(null)}
          onSaved={() => {
            setSharing(null);
            void load();
          }}
        />
      )}
      {preview && data && (
        <PrivatePreview
          occasion={preview}
          circles={data.circles}
          tags={tags}
          onClose={() => setPreview(null)}
          onSaved={(id) => {
            setPreview(null);
            onOpenCircle(id);
          }}
        />
      )}
      {deleting && (
        <Modal
          title="登録した日付を削除しますか？"
          onClose={() => setDeleting(null)}
          busy={busy}
        >
          <div className="occasion-form">
            <ErrorBox message={error} />
            <h3>
              {deleting.name} · {dateLabel(deleting)}
            </h3>
            <p>登録した日付と共有・提案を取り消します。</p>
            <p className="occasion-note">{candidateNotice()}</p>
            <button
              className="button danger-button full"
              disabled={busy}
              onClick={() => void remove()}
            >
              {busy ? "削除しています…" : "日付と共有・提案を削除"}
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}

export function CircleOccasions({
  circleId,
  circleTitle,
  tags,
  onOpenConversation,
}: {
  circleId: string;
  circleTitle: string;
  tags: Tag[];
  onOpenConversation: () => void;
}) {
  const [dates, setDates] = useState<SharedOccasion[]>([]);
  const [items, setItems] = useState<OccasionSuggestion[]>([]);
  const [selected, setSelected] = useState<OccasionSuggestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [visibleDates, setVisibleDates] = useState(8);
  const alive = useAlive();
  async function load() {
    setError("");
    try {
      const [dateResult, suggestions] = await Promise.all([
        api<{ items: SharedOccasion[] }>(`/circles/${circleId}/occasions`),
        api<{ items: OccasionSuggestion[] }>(
          `/occasion-suggestions?circle_id=${encodeURIComponent(circleId)}`,
        ),
      ]);
      if (alive.current) {
        setDates(dateResult.items);
        setItems(suggestions.items);
      }
    } catch (e) {
      if (alive.current) {
        setDates([]);
        setItems([]);
        setSelected(null);
        setError(errorMessage(e));
      }
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [circleId]);
  async function update(
    item: OccasionSuggestion,
    state: OccasionSuggestion["state"],
  ) {
    setBusy(item.id);
    setError("");
    try {
      await api(`/occasion-suggestions/${item.id}/state`, "PUT", {
        state,
        version: item.version,
      });
      if (alive.current) await load();
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setBusy("");
    }
  }
  function card(item: OccasionSuggestion) {
    return (
      <article className="occasion-card" key={item.id}>
        <h3>
          {item.owner.name}の{item.name}
        </h3>
        {item.occurrence && (
          <p className="occasion-date">
            {item.occurrence.occurrence_date}
            {item.occurrence.leap_adjusted && "（今年は2月28日として提案）"}
          </p>
        )}
        <p className="occasion-note">{item.notice}</p>
        <button
          className="button secondary full"
          disabled={!!busy}
          onClick={() => setSelected(item)}
        >
          プラン候補を見る
          <Icon name="arrow" />
        </button>
        <div className="occasion-actions">
          {item.state !== "later" && (
            <button
              className="text-button"
              disabled={!!busy}
              onClick={() => void update(item, "later")}
            >
              あとで見る
            </button>
          )}
          {item.state !== "dismissed" && (
            <button
              className="text-button"
              disabled={!!busy}
              onClick={() => void update(item, "dismissed")}
            >
              今回は見送る
            </button>
          )}
          {item.state !== "new" && (
            <button
              className="text-button"
              disabled={!!busy}
              onClick={() => void update(item, "new")}
            >
              提案一覧に戻す
            </button>
          )}
        </div>
      </article>
    );
  }
  return (
    <section className="occasions">
      <div className="section-title">
        <h2>共有された誕生日・記念日</h2>
        <button
          className="text-button"
          disabled={!!busy || loading}
          onClick={() => void load()}
        >
          <Icon name="refresh" />
          更新
        </button>
      </div>
      <p className="occasion-note">
        登録者がこの講に共有した日付だけを表示しています。事業者への共有相談には表示しません。
      </p>
      <ErrorBox message={error} />
      {loading ? (
        <p role="status">共有された日付と提案を読み込んでいます…</p>
      ) : (
        <>
          <div className="occasion-dates">
            {dates.length ? (
              dates.slice(0, visibleDates).map((item) => (
                <article className="occasion-date-row" key={item.id}>
                  <strong>
                    {item.owner.name}の{item.name}
                  </strong>
                  <p>
                    {dateLabel(item)} ·{" "}
                    {item.suggestions_enabled
                      ? "プラン提案 ON"
                      : "日付のみ共有"}
                  </p>
                </article>
              ))
            ) : (
              <p className="occasion-note">
                この講に共有された日付はありません。
              </p>
            )}
            {dates.length > visibleDates && (
              <button
                className="button secondary"
                onClick={() => setVisibleDates((value) => value + 8)}
              >
                共有日付をさらに表示
              </button>
            )}
          </div>
          <section className="occasion-suggestions">
            <h2>記念日に合うプラン</h2>
            <p className="occasion-note">
              今日から30日以内の日付が対象です。「あとで見る」「今回は見送る」は自分の表示だけに反映します。
            </p>
            {items.filter((item) => item.state === "new").length ? (
              items.filter((item) => item.state === "new").map(card)
            ) : (
              <p className="occasion-note">現在表示する提案はありません。</p>
            )}
            {(["later", "dismissed"] as const).map((state) => {
              const filtered = items.filter((item) => item.state === state);
              return filtered.length ? (
                <details className="occasion-deferred" key={state}>
                  <summary>
                    {state === "later" ? "あとで見る提案" : "見送った提案"}（
                    {filtered.length}件）
                  </summary>
                  <div className="occasion-suggestions">
                    {filtered.map(card)}
                  </div>
                </details>
              ) : null;
            })}
          </section>
        </>
      )}
      {selected && (
        <Modal
          title="記念日に合うプラン"
          onClose={() => setSelected(null)}
          wide
        >
          <div className="occasion-preview">
            <h3>
              {selected.owner.name}の{selected.name}
            </h3>
            <SuggestedPlans
              suggestion={selected}
              circleTitle={circleTitle}
              tags={tags}
              onSaved={() => {
                setSelected(null);
                onOpenConversation();
              }}
            />
          </div>
        </Modal>
      )}
    </section>
  );
}
