import { useEffect, useRef, useState } from "react";
import "./stage.css";

const captions = {
  conversation: "仲間と希望を話し、旅の条件を考える。",
  conditions: "会話から見つけた条件を、自分たちで確かめる。",
  requirements: "人数・泊数・予算を決めて、旅を具体的にする。",
  recommendations: "確認した条件に合う、地域のプランを比較する。",
  selection: "共有する内容を確かめ、選んだ事業者に相談する。",
  reply: "地域の人と、旅の相談をやり取りする。",
  "provider-plan": "地域の人が、自分たちの旅を提案する。",
} as const;
type Caption = { event: keyof typeof captions | "initial"; text: string };

export default function Stage() {
  const visitor = useRef<HTMLIFrameElement>(null);
  const provider = useRef<HTMLIFrameElement>(null);
  const [caption, setCaption] = useState<Caption>({
    event: "initial",
    text: "仲間と旅を探し、地域の人に相談する。",
  });

  useEffect(() => {
    function receive(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (
        event.source !== visitor.current?.contentWindow &&
        event.source !== provider.current?.contentWindow
      )
        return;
      const value = event.data;
      if (
        !value ||
        typeof value !== "object" ||
        value.source !== "ko-stage" ||
        value.status !== "success" ||
        typeof value.type !== "string" ||
        !Object.hasOwn(captions, value.type)
      )
        return;
      // Only completed, meaningful operations change the scene caption.
      // Login, read requests, failure events, and private message bodies are ignored.
      const type = value.type as keyof typeof captions;
      setCaption({ event: type, text: captions[type] });
    }
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
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
        <section className="stage-device visitor-device" aria-label="旅行者">
          <h2 className="device-label">旅行者</h2>
          <div className="phone-frame">
            <div className="phone-camera" aria-hidden="true" />
            <iframe
              ref={visitor}
              src="/stage/visitor"
              title="旅行者の操作画面"
            />
          </div>
        </section>
        <section className="stage-device provider-device" aria-label="事業者">
          <h2 className="device-label">事業者</h2>
          <div className="phone-frame">
            <div className="phone-camera" aria-hidden="true" />
            <iframe
              ref={provider}
              src="/stage/provider"
              title="事業者の操作画面"
            />
          </div>
        </section>
      </div>
    </main>
  );
}
