import { useCallback, useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { api } from "./api";
import { ErrorBox, Icon } from "./ui";
import { errorMessage } from "./validation";
import type { OmikujiData, OmikujiDraw } from "./omikuji-types";
import "./omikuji.css";

const BOXES = [
  { id: "pine", name: "松", mark: "壱", position: "left" },
  { id: "bamboo", name: "竹", mark: "弐", position: "center" },
  { id: "plum", name: "梅", mark: "参", position: "right" },
] as const;
type BoxId = (typeof BOXES)[number]["id"];
type OrientationPermission = typeof DeviceOrientationEvent & {
  requestPermission?: () => Promise<string>;
};
const clamp = (value: number, min: number, max: number) =>
  Math.max(min, Math.min(max, value));

function GardenDrawing() {
  return (
    <svg className="omikuji-garden" viewBox="0 0 1000 420" aria-hidden="true">
      <path
        fill="#e6e9df"
        d="M0 180 90 140 178 168 270 90 385 164 490 104 630 172 755 80 850 150 925 113 1000 180V420H0Z"
      />
      <path
        fill="#d8dfcf"
        d="M0 220 110 180 215 220 322 169 440 200 535 170 645 224 750 184 870 206 1000 173V420H0Z"
      />
      <g fill="#83927a" opacity=".72">
        <path d="M48 255 72 68 96 255ZM112 240 142 25 172 240ZM830 255 857 43 884 255ZM902 252 928 89 954 252Z" />
        <path d="M12 260 32 125 52 260ZM190 250 209 101 228 250ZM783 270 805 132 827 270ZM959 270 979 142 999 270Z" />
      </g>
      <g fill="none" stroke="#4d5c47" strokeWidth="3">
        <path d="m140 35 4 252m-69-206 3 208m777-236 5 233m67-187 3 192" />
        <path d="M0 296Q210 268 350 285T650 285 1000 296" />
      </g>
      <path fill="#f6f0df" d="m461 274-130 146h338L537 274Z" />
      <g fill="none" stroke="#c8c6af" strokeWidth="2">
        <path d="m451 290 95 0m-110 17h126m-147 24h170m-197 31h224m-261 40h300" />
      </g>
      <g fill="#a75039" stroke="#7c3525" strokeWidth="2">
        <path d="M375 137h250v11H375zM393 176h214v8H393zM402 142h10v132h-10zM588 142h10v132h-10z" />
        <path d="M363 126q137 19 274 0l-9 15H372Z" />
      </g>
      <path
        fill="none"
        stroke="#b39868"
        strokeWidth="3"
        d="M412 171q88 24 176 0"
      />
      <g fill="#fff9e9">
        <path d="m452 180 8 6-7 10 8 6-7 10-7-7 7-9-7-7zM539 180l8 6-7 10 8 6-7 10-7-7 7-9-7-7z" />
      </g>
      <g fill="#4c5f4b">
        <path d="M290 274q-12-71 1-121l6-3q-2 81 9 124zM711 275q15-71 3-121l-6-3q2 81-11 124z" />
        <ellipse cx="294" cy="178" rx="53" ry="20" />
        <ellipse cx="277" cy="151" rx="39" ry="17" />
        <ellipse cx="712" cy="178" rx="53" ry="20" />
        <ellipse cx="730" cy="151" rx="39" ry="17" />
      </g>
    </svg>
  );
}

function GardenStage({
  selected,
  onSelect,
  decorative = false,
}: {
  selected: BoxId;
  onSelect: (id: BoxId) => void;
  decorative?: boolean;
}) {
  return (
    <div
      className="omikuji-stage"
      aria-hidden={decorative || undefined}
      inert={decorative}
    >
      <GardenDrawing />
      <div className="omikuji-ground" />
      <div className="omikuji-rope" />
      {BOXES.map((box) => (
        <button
          key={box.id}
          className={`omikuji-box ${box.position} ${selected === box.id ? "chosen" : ""}`}
          aria-pressed={selected === box.id}
          aria-label={`${box.name}の御籤箱を選ぶ`}
          tabIndex={decorative ? -1 : 0}
          onClick={() => onSelect(box.id)}
          type="button"
        >
          <span className="omikuji-box-front">
            <small>{box.mark}</small>
            <b>御籤</b>
            <span>{box.name}</span>
          </span>
          <span className="omikuji-box-side" aria-hidden="true" />
          <span className="omikuji-box-top" aria-hidden="true">
            <i />
          </span>
          <span className="omikuji-box-foot" aria-hidden="true" />
        </button>
      ))}
      <div className="omikuji-foreground" />
    </div>
  );
}

function Garden({
  selected,
  onSelect,
}: {
  selected: BoxId;
  onSelect: (id: BoxId) => void;
}) {
  const [motion, setMotion] = useState(false);
  const [motionNote, setMotionNote] = useState("");
  const [goggles, setGoggles] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);
  const slider = useRef<HTMLInputElement>(null);
  const view = useRef({ yaw: 0, pitch: 0 });
  const drag = useRef<{
    id: number;
    x: number;
    y: number;
    yaw: number;
    pitch: number;
  } | null>(null);
  const pendingFrame = useRef(0);
  const live = useRef(true);

  const look = useCallback((yaw: number, pitch: number) => {
    view.current = { yaw: clamp(yaw, -30, 30), pitch: clamp(pitch, -9, 9) };
    if (pendingFrame.current) return;
    pendingFrame.current = requestAnimationFrame(() => {
      pendingFrame.current = 0;
      const value = view.current;
      viewport.current?.style.setProperty("--look-yaw", `${value.yaw}deg`);
      viewport.current?.style.setProperty("--look-pitch", `${value.pitch}deg`);
      if (slider.current) slider.current.value = String(Math.round(value.yaw));
    });
  }, []);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
      cancelAnimationFrame(pendingFrame.current);
    };
  }, []);
  useEffect(() => {
    if (!motion) return undefined;
    let baseline: { gamma: number; beta: number } | null = null;
    const orient = (event: DeviceOrientationEvent) => {
      if (event.gamma === null || event.beta === null || document.hidden)
        return;
      baseline ??= { gamma: event.gamma, beta: event.beta };
      look(
        (event.gamma - baseline.gamma) * 0.7,
        (event.beta - baseline.beta) * -0.35,
      );
    };
    const timeout = window.setTimeout(() => {
      if (!baseline) {
        setMotion(false);
        setMotionNote(
          "傾きの情報を受け取れません。指や左右のボタンで見回せます。",
        );
      }
    }, 2500);
    window.addEventListener("deviceorientation", orient, { passive: true });
    return () => {
      window.clearTimeout(timeout);
      window.removeEventListener("deviceorientation", orient);
    };
  }, [motion, look]);

  async function enableMotion() {
    if (motion) {
      setMotion(false);
      setMotionNote("傾き操作を止めました。");
      return;
    }
    if (
      !window.isSecureContext ||
      typeof DeviceOrientationEvent === "undefined"
    ) {
      setMotionNote(
        "この環境では傾き操作を使えません。指や左右のボタンで見回せます。",
      );
      return;
    }
    try {
      const sensor = DeviceOrientationEvent as OrientationPermission;
      const permission = sensor.requestPermission
        ? await sensor.requestPermission()
        : "granted";
      if (!live.current) return;
      if (permission !== "granted") {
        setMotionNote(
          "傾き操作は許可されていません。指や左右のボタンを使えます。",
        );
        return;
      }
      look(0, 0);
      setMotion(true);
      setMotionNote(
        "今の持ち方を正面にしました。座ったまま、ゆっくり傾けてください。",
      );
    } catch {
      if (live.current)
        setMotionNote("傾き操作を開始できません。指や左右のボタンを使えます。");
    }
  }
  function startDrag(event: ReactPointerEvent<HTMLInputElement>) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.focus({ preventScroll: true });
    setMotion(false);
    drag.current = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      ...view.current,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function moveDrag(event: ReactPointerEvent<HTMLInputElement>) {
    const start = drag.current;
    if (!start || start.id !== event.pointerId) return;
    look(
      start.yaw + (event.clientX - start.x) * 0.18,
      start.pitch - (event.clientY - start.y) * 0.08,
    );
  }
  function endDrag() {
    drag.current = null;
  }
  return (
    <section className="omikuji-garden-section" aria-label="御籤箱を選ぶ境内">
      <div
        className={`omikuji-viewport ${goggles ? "goggles" : ""}`}
        ref={viewport}
      >
        <input
          ref={slider}
          className="omikuji-look"
          type="range"
          aria-label="境内を見回す。左右の矢印キーで向きを変更"
          min={-30}
          max={30}
          defaultValue={0}
          onChange={(event) => {
            setMotion(false);
            look(Number(event.target.value), 0);
          }}
          onPointerDown={startDrag}
          onPointerMove={moveDrag}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onLostPointerCapture={endDrag}
          onKeyDown={(event) => {
            if (!["ArrowLeft", "ArrowRight", "Home"].includes(event.key))
              return;
            event.preventDefault();
            setMotion(false);
            look(
              event.key === "Home"
                ? 0
                : view.current.yaw + (event.key === "ArrowLeft" ? 7 : -7),
              0,
            );
          }}
        />
        {goggles ? (
          <>
            <div className="omikuji-eye first">
              <GardenStage selected={selected} onSelect={onSelect} decorative />
            </div>
            <div className="omikuji-eye second">
              <GardenStage selected={selected} onSelect={onSelect} decorative />
            </div>
          </>
        ) : (
          <GardenStage selected={selected} onSelect={onSelect} />
        )}
        <span className="omikuji-view-caption" aria-hidden="true">
          {goggles ? "二眼で見回す" : "御籤処"}
        </span>
      </div>
      <div className="omikuji-view-controls">
        <button
          type="button"
          onClick={() => {
            setMotion(false);
            look(view.current.yaw + 10, 0);
          }}
          aria-label="左を見る"
        >
          ←
        </button>
        <button
          type="button"
          onClick={() => {
            setMotion(false);
            look(0, 0);
          }}
        >
          正面へ
        </button>
        <button
          type="button"
          onClick={() => {
            setMotion(false);
            look(view.current.yaw - 10, 0);
          }}
          aria-label="右を見る"
        >
          →
        </button>
        <button
          type="button"
          aria-pressed={motion}
          onClick={() => {
            void enableMotion();
          }}
        >
          {motion ? "傾きを止める" : "傾きで見る"}
        </button>
        <button
          type="button"
          aria-pressed={goggles}
          onClick={() => setGoggles(!goggles)}
        >
          {goggles ? "通常表示へ" : "二眼表示"}
        </button>
      </div>
      <p className="omikuji-help">
        {goggles
          ? "箱を選ぶ時は通常表示に戻ってください。"
          : "背景を指で動かして周りを見る。箱を押して選びます。"}
      </p>
      {motionNote && <output className="omikuji-help">{motionNote}</output>}
    </section>
  );
}

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
  const [selected, setSelected] = useState<BoxId>("bamboo");
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
        参加店の現地で確認番号を受け取り、箱を一つ選びます。
      </p>
      <Garden
        key={current?.id || "choose"}
        selected={selected}
        onSelect={setSelected}
      />
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
              <p className="omikuji-selected">
                選んだ箱：
                <strong>
                  {BOXES.find((box) => box.id === selected)?.name}
                </strong>
                <span>箱による当選確率の違いはありません。</span>
              </p>
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
                お店が発行してから10分以内に入力してください。GPSやカメラは使いません。
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
                {busy ? "結果を保存しています…" : "この箱で今月のくじを引く"}
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
