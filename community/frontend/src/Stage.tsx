import { useCallback, useEffect, useRef, useState } from "react";
import "./stage.css";

const captions = {
  "post-published": "コミュニティに投稿を公開した。",
  "outing-created": "日帰りの開催を保存し、仲間に参加を依頼した。",
  "outing-accepted": "開催への参加を承諾した。",
  "outing-claimed": "今回の実参加を申告した。",
  "outing-confirmed": "他の参加者が実施を確認し、ポイントを記録した。",
  "outing-provider-confirmed": "事業者が利用を確認し、特典の資格に反映した。",
  "outing-cancelled": "開催・参加の取消を保存した。",
  "benefit-published": "事業者が条件と負担を決め、ランク特典を公開した。",
  "benefit-reserved": "次の開催で使う特典を確保した。",
  "benefit-redeemed": "事業者が特典の利用を記録した。",
  conversation: "仲間と希望を話し、旅の条件を考える。",
  conditions: "会話から見つけた条件を、自分たちで確かめる。",
  requirements: "人数・泊数・予算を決めて、旅を具体的にする。",
  recommendations: "確認した条件に合う、地域のプランを比較する。",
  selection: "共有する内容を確かめ、選んだ事業者に相談する。",
  reply: "地域の人と、旅の相談をやり取りする。",
  "provider-plan": "地域の人が、自分たちの旅を提案する。",
  "circle-invite": "行き先と共有内容を決め、事業者を講へ招く。",
  "circle-joined": "事業者が招待を受け、同じ旅の相談に加わる。",
  "circle-reply": "講の仲間と地域の人が、旅の相談を交わす。",
} as const;
type Caption = { event: keyof typeof captions | "initial"; text: string };
function isCaptionType(value: unknown): value is keyof typeof captions {
  return typeof value === "string" && Object.hasOwn(captions, value);
}
type Transfer = {
  sequence: number;
  event:
    "selection" | "reply" | "circle-invite" | "circle-joined" | "circle-reply";
  direction: "visitor-to-provider" | "provider-to-visitor";
};

export default function Stage() {
  const visitor = useRef<HTMLIFrameElement>(null);
  const provider = useRef<HTMLIFrameElement>(null);
  const [caption, setCaption] = useState<Caption>({
    event: "initial",
    text: "日帰りの行き先と、講の開催を決める。",
  });
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [lastTransfer, setLastTransfer] = useState<Transfer | null>(null);
  const transferSequence = useRef(0);
  const transferActive = useRef(false);
  const transferQueue = useRef<Transfer[]>([]);

  const finishTransfer = useCallback(() => {
    const next = transferQueue.current.shift() || null;
    transferActive.current = next !== null;
    setTransfer(next);
  }, []);

  useEffect(() => {
    if (!transfer) return undefined;
    // A single finite fallback releases the queue if a browser cancels CSS animation.
    const timer = window.setTimeout(finishTransfer, 1000);
    return () => window.clearTimeout(timer);
  }, [transfer, finishTransfer]);

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const stackedLayout = window.matchMedia("(max-width: 1100px)");
    const canAnimate = () =>
      document.visibilityState === "visible" &&
      !reducedMotion.matches &&
      !stackedLayout.matches;
    function stopWhenHidden() {
      if (canAnimate()) return;
      transferQueue.current = [];
      transferActive.current = false;
      setTransfer(null);
    }
    function receive(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (
        event.source !== visitor.current?.contentWindow &&
        event.source !== provider.current?.contentWindow
      )
        return;
      const value: unknown = event.data;
      if (
        !value ||
        typeof value !== "object" ||
        !("source" in value) ||
        value.source !== "ko-stage" ||
        !("status" in value) ||
        value.status !== "success" ||
        !("type" in value) ||
        !isCaptionType(value.type)
      )
        return;
      // Only completed, meaningful operations change the scene caption.
      // Login, read requests, failure events, and private message bodies are ignored.
      const type = value.type;
      const fromVisitor = event.source === visitor.current?.contentWindow;
      if (
        (type === "circle-invite" && !fromVisitor) ||
        (type === "circle-joined" && fromVisitor)
      )
        return;
      setCaption({ event: type, text: captions[type] });
      // An internal conversation, draft, or read is not a message to the other role.
      if (
        type !== "reply" &&
        type !== "circle-reply" &&
        type !== "circle-joined" &&
        !(type === "selection" && fromVisitor) &&
        !(type === "circle-invite" && fromVisitor)
      )
        return;
      const next: Transfer = {
        sequence: ++transferSequence.current,
        event: type,
        direction: fromVisitor ? "visitor-to-provider" : "provider-to-visitor",
      };
      setLastTransfer(next);
      if (!canAnimate()) return;
      if (transferActive.current) {
        // Keep a burst bounded and favour recent activity over a long stale replay.
        if (transferQueue.current.length >= 8) transferQueue.current.shift();
        transferQueue.current.push(next);
      } else {
        transferActive.current = true;
        setTransfer(next);
      }
    }
    window.addEventListener("message", receive);
    document.addEventListener("visibilitychange", stopWhenHidden);
    reducedMotion.addEventListener("change", stopWhenHidden);
    stackedLayout.addEventListener("change", stopWhenHidden);
    return () => {
      window.removeEventListener("message", receive);
      document.removeEventListener("visibilitychange", stopWhenHidden);
      reducedMotion.removeEventListener("change", stopWhenHidden);
      stackedLayout.removeEventListener("change", stopWhenHidden);
      transferQueue.current = [];
    };
  }, []);

  return (
    <main className="stage">
      <header className="stage-header">
        <span className="brand-mark" aria-hidden="true">
          講
        </span>
        <h1
          className="stage-caption"
          data-event={caption.event}
          aria-live="polite"
        >
          {caption.text}
        </h1>
      </header>
      <div className="stage-floor">
        <section className="stage-device visitor-device" aria-label="利用者">
          <h2 className="device-label">
            利用者 <span>スマートフォン</span>
          </h2>
          <div className="phone-frame">
            <div className="phone-camera" aria-hidden="true" />
            <iframe
              ref={visitor}
              src="/stage/visitor"
              title="利用者のスマートフォン画面"
            />
          </div>
        </section>
        <div
          className="stage-connection"
          aria-hidden="true"
          data-direction={lastTransfer?.direction || "none"}
          data-transfer-event={lastTransfer?.event || "none"}
          data-transfer-count={lastTransfer?.sequence || 0}
          data-active-sequence={transfer?.sequence || 0}
          data-animating={transfer !== null}
        >
          <svg
            className="stage-connection-thread"
            viewBox="0 0 100 48"
            fill="none"
          >
            <path d="M0 22H36M64 22H100M0 26H36M64 26H100" />
            <path
              className="stage-connection-knot"
              d="M50 24C41 12 31 17 38 26C45 35 53 29 62 20C69 12 57 12 50 24C43 36 33 35 38 26C45 17 55 16 62 20C70 28 60 36 50 24Z"
            />
          </svg>
          {transfer && (
            <span
              key={transfer.sequence}
              className="stage-connection-packet"
              data-direction={transfer.direction}
              onAnimationEnd={(event) => {
                if (event.target === event.currentTarget) finishTransfer();
              }}
            >
              <span />
            </span>
          )}
        </div>
        <section className="stage-device provider-device" aria-label="事業者">
          <h2 className="device-label">
            事業者 <span>パソコン</span>
          </h2>
          <div className="desktop-frame">
            <div className="desktop-windowbar" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <iframe
              ref={provider}
              src="/stage/provider"
              title="事業者のパソコン管理画面"
            />
          </div>
        </section>
      </div>
    </main>
  );
}
