import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { ErrorBox, Icon } from "./ui";
import { errorMessage } from "./validation";
import type { OmikujiData, OmikujiDraw } from "./omikuji-types";
import JizoCamera from "./JizoCamera";
import "./omikuji.css";

const yen = (amount: number) => `${amount.toLocaleString("ja-JP")}円`;
const dateLabel = (value: string) =>
  new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tokyo",
  }).format(new Date(value));

function ResultSlip({
  draw,
  opened = false,
}: {
  draw: OmikujiDraw;
  opened?: boolean;
}) {
  return (
    <article className={`omikuji-result ${opened ? "just-opened" : ""}`}>
      <p className="omikuji-slip-label">
        {draw.month.replace("-", "年")}月の御籤
      </p>
      <h2 className="wa-title-script">
        {draw.amount_yen > 0 ? "当たり" : "特典なし"}
      </h2>
      {draw.amount_yen > 0 ? (
        <p className="omikuji-prize">
          <strong>{yen(draw.amount_yen)}</strong>
          <span>割引券</span>
        </p>
      ) : (
        <p>今月の抽選は終了しました。</p>
      )}
      <p className="omikuji-provider-name">{draw.provider_name}</p>
      {draw.reward && (
        <>
          <span className="omikuji-reward-status">
            {draw.reward.status === "available"
              ? "未使用"
              : draw.reward.status === "redeemed"
                ? "利用済み"
                : "期限切れ"}
          </span>
          <p className="omikuji-help">
            有効期限 {dateLabel(draw.reward.expires_at)}
          </p>
          {draw.reward.status === "available" && (
            <p className="omikuji-help">
              この画面をお店で提示してください。利用の確定はお店が行います。
            </p>
          )}
          <code className="omikuji-reward-id">券番号 {draw.reward.id}</code>
        </>
      )}
    </article>
  );
}

export default function Omikuji({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<OmikujiData | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uncertain, setUncertain] = useState(false);
  const [opened, setOpened] = useState(false);
  const [result, setResult] = useState<OmikujiDraw | null>(null);
  const controller = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const requestId = useRef(crypto.randomUUID());
  const sentCode = useRef("");
  const resultHeading = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const request = new AbortController();
    controller.current = request;
    void api<OmikujiData>("/omikuji", "GET", undefined, {
      signal: request.signal,
    })
      .then((overview) => {
        if (!request.signal.aborted) setData(overview);
        return undefined;
      })
      .catch((cause: unknown) => {
        if (!request.signal.aborted) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!request.signal.aborted) setLoading(false);
      });
    return () => request.abort();
  }, []);

  async function reload() {
    const request = controller.current;
    if (!request || request.signal.aborted || lock.current) return;
    lock.current = true;
    setLoading(true);
    setError("");
    try {
      const next = await api<OmikujiData>("/omikuji", "GET", undefined, {
        signal: request.signal,
      });
      if (request.signal.aborted) return;
      setData(next);
      setUncertain(false);
      const saved = next.draws.find((item) => item.month === next.month);
      if (saved) {
        setResult(saved);
        setNotice("保存された今月の結果です。");
      }
    } catch (cause) {
      if (!request.signal.aborted) setError(errorMessage(cause));
    } finally {
      lock.current = false;
      if (!request.signal.aborted) setLoading(false);
    }
  }
  async function draw(animate: boolean) {
    const request = controller.current;
    if (
      !request ||
      request.signal.aborted ||
      lock.current ||
      !data?.can_draw ||
      uncertain ||
      !/^\d{6}$/.test(code)
    )
      return;
    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    if (sentCode.current !== code) {
      requestId.current = crypto.randomUUID();
      sentCode.current = code;
    }
    try {
      const saved = await api<OmikujiDraw>(
        "/omikuji/draw",
        "POST",
        { code, client_request_id: requestId.current },
        { signal: request.signal },
      );
      if (request.signal.aborted) return;
      setResult(saved);
      setOpened(animate);
      setData({
        ...data,
        can_draw: false,
        draws: [saved, ...data.draws.filter((item) => item.id !== saved.id)],
      });
      setCode("");
      setNotice("今月の結果を保存しました。");
      requestAnimationFrame(() => {
        if (!request.signal.aborted) {
          resultHeading.current?.scrollIntoView({
            behavior: "auto",
            block: "center",
          });
          resultHeading.current?.focus({ preventScroll: true });
        }
      });
    } catch (cause) {
      if (request.signal.aborted) return;
      // A lost response may already have consumed this month's draw. Read it
      // back before allowing another POST; retries keep the same request ID.
      try {
        const restored = await api<OmikujiData>("/omikuji", "GET", undefined, {
          signal: request.signal,
        });
        if (request.signal.aborted) return;
        setData(restored);
        const saved = restored.draws.find(
          (item) => item.month === restored.month,
        );
        if (saved) {
          setResult(saved);
          setNotice("保存された今月の結果を確認しました。");
          setCode("");
        } else setError(errorMessage(cause));
      } catch {
        if (!request.signal.aborted) {
          setUncertain(true);
          setError(
            "抽選結果の保存状態を確認できません。結果を確認してから続けてください。",
          );
        }
      }
    } finally {
      lock.current = false;
      if (!request.signal.aborted) setBusy(false);
    }
  }
  const current =
    result || data?.draws.find((item) => item.month === data.month);
  const previous = data?.draws.filter((item) => item.id !== current?.id) || [];
  return (
    <section className="omikuji-page">
      <button className="text-button" onClick={onClose}>
        <Icon name="arrow" />
        旅の手帳へ
      </button>
      <header className="omikuji-heading">
        <p>月に一度・無料</p>
        <h1 className="wa-title-script">月替わりのおみくじ</h1>
      </header>
      <p className="omikuji-intro">
        参加店の現地の印をカメラで読み取ると、お地蔵さんが現れます。
      </p>
      {!current && (
        <JizoCamera
          disabled={busy || loading || uncertain || !data?.can_draw}
          onScanned={(value) => {
            setCode(value);
            setNotice(
              value
                ? "現地の印を読み取りました。お地蔵さんから特典を受け取れます。"
                : "",
            );
          }}
        />
      )}
      <ErrorBox message={error} />
      {notice && <output className="notice">{notice}</output>}
      {loading && (
        <output className="loading-inline">
          今月の抽選状況を確認しています…
        </output>
      )}
      {(error || uncertain) && (
        <button
          className="button secondary"
          disabled={busy || loading}
          onClick={() => {
            void reload();
          }}
        >
          保存された結果を確認
        </button>
      )}
      {data && (
        <>
          <div className="omikuji-rank-note">
            <span>特典対象の階級</span>
            <strong>{data.rank.name}</strong>
            <span>{data.month.replace("-", "年")}月</span>
          </div>
          {data.personal_rank.level !== data.rank.level && (
            <p className="omikuji-help">
              旅の階級は「{data.personal_rank.name}
              」。抽選は事業者の利用確認済み実績に基づく階級を使います。
            </p>
          )}
          {current ? (
            <div ref={resultHeading} tabIndex={-1}>
              <ResultSlip draw={current} opened={opened} />
            </div>
          ) : data.can_draw ? (
            <form
              className="omikuji-draw-form"
              onSubmit={(event) => {
                event.preventDefault();
                void draw(false);
              }}
            >
              <label className="field" htmlFor="omikuji-code">
                お店の確認番号（6桁）
                <input
                  id="omikuji-code"
                  value={code}
                  onChange={(event) =>
                    setCode(event.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  inputMode="numeric"
                  autoComplete="off"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                  disabled={busy || uncertain}
                  placeholder="000000"
                />
              </label>
              <p className="omikuji-help">
                読み取れない時は、お店の6桁番号を入力できます。発行から10分以内に受け取ってください。
              </p>
              <button
                className="button primary full omikuji-draw-button"
                type="submit"
                disabled={busy || loading || uncertain || !/^\d{6}$/.test(code)}
                onClick={(event) => {
                  if (event.detail > 0) {
                    event.preventDefault();
                    void draw(true);
                  }
                }}
              >
                {busy ? "結果を保存しています…" : "お地蔵さんをスキャン"}
              </button>
            </form>
          ) : (
            <p className="omikuji-help">
              今月の抽選は終了しています。保存された結果を確認してください。
            </p>
          )}
          <details className="omikuji-terms">
            <summary>当選確率・利用条件</summary>
            <p>現在の特典対象階級「{data.rank.name}」の確率です。</p>
            <dl className="omikuji-odds">
              {data.odds.map((odd) => (
                <div key={odd.amount_yen}>
                  <dt>
                    {odd.amount_yen === 0
                      ? "特典なし"
                      : `${yen(odd.amount_yen)}券`}
                  </dt>
                  <dd>{odd.probability_percent}%</dd>
                </div>
              ))}
            </dl>
            <ul>
              {data.terms.map((term) => (
                <li key={term}>{term}</li>
              ))}
            </ul>
          </details>
          <section className="omikuji-history">
            <h2>獲得した券・これまでの結果</h2>
            {previous.length ? (
              previous.map((item) => <ResultSlip key={item.id} draw={item} />)
            ) : (
              <p className="omikuji-help">
                {current
                  ? "これまでの結果は上に表示しています。"
                  : "まだ抽選の記録はありません。"}
              </p>
            )}
          </section>
        </>
      )}
    </section>
  );
}
