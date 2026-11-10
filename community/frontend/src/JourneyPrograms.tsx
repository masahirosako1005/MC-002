import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import Choice from "./Choice";
import type { Outing } from "./daytrip-types";
import type {
  JourneyProgram,
  ProgramCatalog,
  ProgramEnrollment,
  ProgramOuting,
  ProgramProgress,
  ProgramStep,
} from "./journey-program-types";
import { Empty, ErrorBox, Icon, Modal } from "./ui";
import { SealMark } from "./WaArt";
import { errorMessage } from "./validation";
import "./journey-programs.css";

const yen = (value: number) => `${value.toLocaleString("ja-JP")}円`;
const date = (value: string) =>
  new Intl.DateTimeFormat("ja-JP", {
    month: "long",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tokyo",
  }).format(new Date(value));
const statusLabels = {
  unplanned: "開催未選択",
  planned: "開催を選択済み",
  awaiting_confirmation: "実施確認待ち",
  completed: "利用確認済み",
  invalid: "開催の再確認が必要",
};

function StepDialog({
  program,
  step,
  onClose,
  onSaved,
  onRefresh,
  onCreate,
  onFindCircles,
}: {
  program: JourneyProgram;
  step: ProgramStep;
  onClose: () => void;
  onSaved: (enrollment: ProgramEnrollment, removed: boolean) => void;
  onRefresh: () => void;
  onCreate: () => void;
  onFindCircles: () => void;
}) {
  const progress = program.enrollment?.steps.find(
    (item) => item.step_id === step.id,
  );
  const [outings, setOutings] = useState<ProgramOuting[] | null>(
    program.available ? null : [],
  );
  const [selected, setSelected] = useState(progress?.outing_id || "");
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const lock = useRef(false);
  useEffect(() => {
    const request = new AbortController();
    controller.current = request;
    if (!program.available) return () => request.abort();
    void api<{ items: ProgramOuting[] }>(
      `/daytrip/programs/${encodeURIComponent(program.id)}/outings`,
      "GET",
      undefined,
      { signal: request.signal },
    )
      .then((result) => {
        if (!request.signal.aborted)
          setOutings(
            result.items.filter((item) => item.plan_id === step.plan_id),
          );
        return undefined;
      })
      .catch((cause: unknown) => {
        if (!request.signal.aborted) setError(errorMessage(cause));
      });
    return () => request.abort();
  }, [program.id, program.available, step.plan_id]);
  async function save(outingId: string | null) {
    if (
      (outingId !== null && !program.available) ||
      !program.enrollment ||
      lock.current ||
      !controller.current ||
      controller.current.signal.aborted
    )
      return;
    lock.current = true;
    setBusy(true);
    setError("");
    const request = controller.current;
    try {
      const enrollment = await api<ProgramEnrollment>(
        `/daytrip/programs/${encodeURIComponent(program.id)}/steps/${encodeURIComponent(step.id)}`,
        "PUT",
        { version: program.enrollment.version, outing_id: outingId },
        { signal: request.signal },
      );
      if (!request.signal.aborted) onSaved(enrollment, outingId === null);
    } catch (cause) {
      if (!request.signal.aborted) {
        setError(errorMessage(cause));
        setConflict(cause instanceof ApiError && cause.status === 409);
      }
    } finally {
      lock.current = false;
      if (!request.signal.aborted) setBusy(false);
    }
  }
  return (
    <Modal
      title={`第${step.order}回の開催を選ぶ`}
      onClose={onClose}
      busy={busy}
    >
      <div className="program-step-dialog">
        <p className="small-label">
          {program.provider.name} · {program.area}
        </p>
        <h3>{step.title}</h3>
        <p>{step.purpose}</p>
        <p className="program-plan-name">対象プラン：{step.plan_title}</p>
        <ErrorBox message={error} />
        {!program.available && (
          <p className="program-evidence-note">
            {program.unavailable_reason ||
              "現在、新しい開催を紐付けられません。既存の紐付けは外せます。"}
          </p>
        )}
        {outings === null && !error ? (
          <output className="loading-inline">
            参加承諾済みの開催を確認しています…
          </output>
        ) : outings && outings.length > 0 ? (
          <>
            <label className="field" htmlFor="program-step-outing">
              この回で利用する開催
              <Choice
                id="program-step-outing"
                disabled={busy || conflict}
                value={selected}
                onChange={(event) => setSelected(event.target.value)}
              >
                <option value="">開催を選ぶ</option>
                {outings.map((outing) => (
                  <option key={outing.id} value={outing.id}>
                    {date(outing.starts_at)} · {outing.title}
                    {outing.status === "cancelled" ? "（取消済み）" : ""}
                  </option>
                ))}
              </Choice>
            </label>
            <p className="quiet-note">
              本人が参加承諾した、対象プランの開催だけを表示しています。各回の順序と利用確認を確認して進捗を反映します。
            </p>
            <button
              className="button primary full"
              disabled={
                busy ||
                conflict ||
                !outings.some((outing) => outing.id === selected)
              }
              onClick={() => void save(selected)}
            >
              {busy ? "保存しています…" : "この開催を紐付ける"}
            </button>
          </>
        ) : (
          outings &&
          program.available && (
            <div className="program-no-outings">
              <h4>対象プランの開催がありません</h4>
              <p>
                講でこのプランを相談し、事業者の招待承諾を受けて開催を作ります。本人の参加承諾後に、ここで選べます。
              </p>
              <button
                className="button secondary full"
                disabled={busy}
                onClick={onCreate}
              >
                この回の開催をつくる
                <Icon name="arrow" />
              </button>
              <button
                className="text-button"
                disabled={busy}
                onClick={onFindCircles}
              >
                講でプランを相談する
              </button>
            </div>
          )
        )}
        {(conflict || (error && outings === null)) && (
          <button
            className="button secondary full"
            disabled={busy}
            onClick={onRefresh}
          >
            最新の進捗を読み直す
          </button>
        )}
        {progress?.has_link && (
          <button
            className="text-button danger"
            disabled={busy || conflict}
            onClick={() => void save(null)}
          >
            この回との紐付けを外す
          </button>
        )}
        <p className="quiet-note">
          紐付けを外しても、開催・参加記録・ポイントは削除されません。
        </p>
      </div>
    </Modal>
  );
}

function ProgramCard({
  program,
  busy,
  onEnroll,
  onStep,
  onOpenOuting,
  onCancel,
}: {
  program: JourneyProgram;
  busy: boolean;
  onEnroll: () => void;
  onStep: (step: ProgramStep) => void;
  onOpenOuting: (id: string) => void;
  onCancel: () => void;
}) {
  const enrollment = program.enrollment;
  const enrolled = enrollment !== null && enrollment.status !== "cancelled";
  return (
    <article className="program-card">
      <header className="program-card-heading">
        <div>
          <p className="program-place">
            <Icon name="pin" />
            {program.area} · {program.provider.name}
          </p>
          <h2>{program.title}</h2>
        </div>
        <span className="program-visit-count">
          全<strong>{program.steps.length}</strong>回
        </span>
      </header>
      <p className="program-goal">{program.goal}</p>
      {!program.available && (
        <p className="program-evidence-note">
          {program.unavailable_reason ||
            "現在、新しい登録や開催の紐付けはできません。"}
        </p>
      )}
      <div className="program-price">
        <span>全回合計 / 一人</span>
        <strong>{yen(program.total_price_yen)}</strong>
      </div>
      <p className="program-evidence-note">
        プラン部分の合計・割引前。交通費は別です。
      </p>
      <p className="program-interval">
        <Icon name="calendar" />
        {program.recommended_interval}
      </p>
      {enrolled && (
        <div className="program-progress">
          <span>
            {enrollment.status === "completed"
              ? "全段階の利用確認済み"
              : "あなたの実施進捗"}
          </span>
          <strong>
            {enrollment.completed_count} / {enrollment.total_steps}回
          </strong>
          <progress
            value={enrollment.completed_count}
            max={enrollment.total_steps}
            aria-label="事業者まで利用確認された段階"
          />
        </div>
      )}
      <ol className="program-steps">
        {program.steps.map((step) => {
          const progress: ProgramProgress | undefined = enrolled
            ? enrollment.steps.find((item) => item.step_id === step.id)
            : undefined;
          return (
            <li
              key={step.id}
              className={`program-step ${progress?.status || "unplanned"}`}
            >
              <span className="program-step-number">
                {progress?.status === "completed" ? (
                  <SealMark decorative>済</SealMark>
                ) : (
                  step.order
                )}
              </span>
              <div className="program-step-content">
                <div className="program-step-heading">
                  <h3>{step.title}</h3>
                  <span>{yen(step.price_yen)}</span>
                </div>
                <p>{step.purpose}</p>
                {enrolled && (
                  <>
                    <p
                      className={`program-step-status ${progress?.status || "unplanned"}`}
                    >
                      {statusLabels[progress?.status || "unplanned"]}
                    </p>
                    {progress?.reason && (
                      <p className="program-step-reason">{progress.reason}</p>
                    )}
                    <div className="program-step-actions">
                      <button
                        className="text-button"
                        disabled={
                          busy || (!program.available && !progress?.has_link)
                        }
                        onClick={() => onStep(step)}
                      >
                        {!program.available
                          ? "紐付けを確認"
                          : progress?.has_link
                            ? "開催を変更"
                            : "開催を選ぶ"}
                      </button>
                      {progress?.outing_id && (
                        <button
                          className="text-button"
                          disabled={busy}
                          onClick={() => onOpenOuting(progress.outing_id!)}
                        >
                          開催・参加の確認
                          <Icon name="arrow" />
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      <details className="program-price-note">
        <summary>費用と予約の条件</summary>
        <p>{program.price_note}</p>
      </details>
      {!enrolled ? (
        <button
          className="button primary full"
          disabled={busy || !program.available}
          onClick={onEnroll}
        >
          {!program.available
            ? "現在は登録できません"
            : busy
              ? "操作を保存しています…"
              : enrollment?.status === "cancelled"
                ? "もう一度この旅を登録"
                : "この通う旅を登録"}
          <Icon name="arrow" />
        </button>
      ) : (
        <button
          className="text-button program-cancel"
          disabled={busy}
          onClick={onCancel}
        >
          通う旅の登録を取り消す
        </button>
      )}
    </article>
  );
}

type ProgramProps = {
  onOpenOuting: (outing: Outing) => void;
  onCreateStep: (step: ProgramStep) => void;
  onFindCircles: () => void;
};
function ProgramsContent({
  onRefresh,
  onOpenOuting,
  onCreateStep,
  onFindCircles,
}: ProgramProps & { onRefresh: () => void }) {
  const [data, setData] = useState<ProgramCatalog | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [selection, setSelection] = useState<{
    programId: string;
    stepId: string;
  } | null>(null);
  const [cancelling, setCancelling] = useState<JourneyProgram | null>(null);
  const request = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const keys = useRef(new Map<string, string>());
  useEffect(() => {
    const controller = new AbortController();
    request.current = controller;
    void api<ProgramCatalog>("/daytrip/programs", "GET", undefined, {
      signal: controller.signal,
    })
      .then((result) => {
        if (!controller.signal.aborted) setData(result);
        return undefined;
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      });
    return () => controller.abort();
  }, []);
  function update(programId: string, enrollment: ProgramEnrollment) {
    setData((previous) =>
      previous
        ? {
            ...previous,
            items: previous.items.map((program) =>
              program.id === programId ? { ...program, enrollment } : program,
            ),
          }
        : previous,
    );
  }
  async function mutate(program: JourneyProgram, action: "enroll" | "cancel") {
    if (lock.current || !request.current || request.current.signal.aborted)
      return;
    const controller = request.current;
    lock.current = true;
    setBusy(program.id);
    setError("");
    setNotice("");
    const operation = `${program.id}:${action}:${program.enrollment?.version || 0}`;
    if (!keys.current.has(operation))
      keys.current.set(operation, crypto.randomUUID());
    try {
      const enrollment = await api<ProgramEnrollment>(
        `/daytrip/programs/${encodeURIComponent(program.id)}/${action}`,
        "POST",
        {
          client_request_id: keys.current.get(operation),
          ...(action === "cancel"
            ? { version: program.enrollment?.version }
            : {}),
        },
        { signal: controller.signal },
      );
      if (!controller.signal.aborted) {
        update(program.id, enrollment);
        setCancelling(null);
        setNotice(
          action === "enroll"
            ? "通う旅を登録しました。各回の開催を選んでください。予約・決済は別途確認します。"
            : "通う旅の登録を取り消しました。開催・参加記録・ポイントは残ります。",
        );
      }
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    } finally {
      lock.current = false;
      if (!controller.signal.aborted) setBusy("");
    }
  }
  async function openOuting(id: string) {
    if (lock.current || !request.current || request.current.signal.aborted)
      return;
    const controller = request.current;
    lock.current = true;
    setBusy(id);
    setError("");
    try {
      const outing = await api<Outing>(
        `/daytrip/outings/${encodeURIComponent(id)}`,
        "GET",
        undefined,
        { signal: controller.signal },
      );
      if (!controller.signal.aborted) onOpenOuting(outing);
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    } finally {
      lock.current = false;
      if (!controller.signal.aborted) setBusy("");
    }
  }
  const selectedProgram = data?.items.find(
    (program) => program.id === selection?.programId,
  );
  const selectedStep = selectedProgram?.steps.find(
    (step) => step.id === selection?.stepId,
  );
  return (
    <div className="journey-programs">
      <div className="program-toolbar">
        <p>何度か通って、一つの目的に取り組む旅</p>
        <button className="text-button" disabled={!!busy} onClick={onRefresh}>
          <Icon name="refresh" />
          更新
        </button>
      </div>
      <ErrorBox message={error} />
      {error && (
        <button className="text-button" disabled={!!busy} onClick={onRefresh}>
          一覧と進捗を読み直す
        </button>
      )}
      {notice && <output className="notice">{notice}</output>}
      {!data && !error ? (
        <output className="loading-inline">
          通う旅と実施進捗を読み込んでいます…
        </output>
      ) : (
        data && (
          <>
            {data.items.length ? (
              data.items.map((program) => (
                <ProgramCard
                  key={program.id}
                  program={program}
                  busy={!!busy}
                  onEnroll={() => void mutate(program, "enroll")}
                  onStep={(step) =>
                    setSelection({ programId: program.id, stepId: step.id })
                  }
                  onOpenOuting={(id) => void openOuting(id)}
                  onCancel={() => setCancelling(program)}
                />
              ))
            ) : (
              <Empty title="公開中の通う旅はありません">
                <p>
                  複数回の体験と各回の予定が公開されると、ここから選べます。
                </p>
              </Empty>
            )}
            <p className="program-evidence-note">{data.notice}</p>
          </>
        )
      )}
      {selectedProgram && selectedStep && (
        <StepDialog
          key={`${selectedProgram.id}-${selectedStep.id}`}
          program={selectedProgram}
          step={selectedStep}
          onClose={() => setSelection(null)}
          onSaved={(enrollment, removed) => {
            update(selectedProgram.id, enrollment);
            setSelection(null);
            setNotice(
              removed
                ? "この回との紐付けを外しました。開催そのものは残ります。"
                : "開催を紐付けました。実施進捗は利用確認に基づいて更新します。",
            );
          }}
          onRefresh={onRefresh}
          onCreate={() => {
            setSelection(null);
            onCreateStep(selectedStep);
          }}
          onFindCircles={() => {
            setSelection(null);
            onFindCircles();
          }}
        />
      )}
      {cancelling && (
        <Modal
          title="通う旅の登録を取り消しますか？"
          busy={!!busy}
          onClose={() => setCancelling(null)}
        >
          <div className="program-step-dialog">
            <p>
              {cancelling.title}
              の登録と、各回の開催との紐付けを解除します。開催の中止や返金にはなりません。参加記録とポイントは残り、後から再登録できます。
            </p>
            <ErrorBox message={error} />
            <div className="dialog-actions">
              <button
                className="button secondary"
                disabled={!!busy}
                onClick={() => setCancelling(null)}
              >
                登録を残す
              </button>
              <button
                className="button danger-button"
                disabled={!!busy}
                onClick={() => void mutate(cancelling, "cancel")}
              >
                {busy ? "取り消しています…" : "登録を取り消す"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default function JourneyPrograms(props: ProgramProps) {
  const [revision, setRevision] = useState(0);
  return (
    <ProgramsContent
      key={revision}
      {...props}
      onRefresh={() => setRevision((value) => value + 1)}
    />
  );
}
