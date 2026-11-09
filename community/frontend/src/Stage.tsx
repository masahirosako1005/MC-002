import { useEffect, useRef, useState } from "react";
import { Icon } from "./ui";
import "./stage.css";
const eventLabels = {
  session: "ログインしました",
  photo: "写真を受け取りました",
  conditions: "会話から条件候補を整理",
  requirements: "旅行条件を確認",
  recommendations: "条件に合うプランを比較",
  selection: "選んだ事業者に相談が届く",
  reply: "相談のメッセージを送信",
  "consultation-read": "相談の内容を確認",
  "provider-plan": "事業者のプランを保存",
  conversation: "講の会話に希望を追加",
} as const;
type Activity = {
  id: number;
  actor: "visitor" | "provider";
  type: keyof typeof eventLabels;
  status: "success" | "failure";
  time: string;
};
export default function Stage() {
  const visitor = useRef<HTMLIFrameElement>(null);
  const provider = useRef<HTMLIFrameElement>(null);
  const [count, setCount] = useState(0);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [paused, setPaused] = useState(false);
  const [large, setLarge] = useState<"visitor" | "provider" | null>(null);
  const sequence = useRef(0);
  useEffect(() => {
    function receive(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      const actor =
        event.source === visitor.current?.contentWindow
          ? "visitor"
          : event.source === provider.current?.contentWindow
            ? "provider"
            : null;
      if (!actor) return;
      const value = event.data;
      if (
        !value ||
        typeof value !== "object" ||
        value.source !== "ko-stage" ||
        typeof value.type !== "string" ||
        !Object.hasOwn(eventLabels, value.type) ||
        !["success", "failure"].includes(value.status)
      )
        return;
      const item: Activity = {
        id: ++sequence.current,
        actor,
        type: value.type,
        status: value.status,
        time: new Intl.DateTimeFormat("ja-JP", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }).format(new Date()),
      };
      setActivities((items) => [item, ...items].slice(0, 18));
    }
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, []);
  const latest = activities[0];
  return (
    <main
      className={`stage ${paused ? "motion-paused" : ""} ${large ? `expanded-${large}` : ""}`}
    >
      <header className="stage-header">
        <div className="brand">
          <span className="brand-mark">講</span>
          <div>
            <h1>旅の希望が、地域につながる。</h1>
            <p>話す → 条件を確かめる → 選ぶ → 相談する</p>
          </div>
        </div>
        <div className="stage-controls">
          <a href="/" className="button secondary">
            アプリをひらく
          </a>
          <button
            className="button secondary"
            onClick={() => setPaused(!paused)}
          >
            {paused ? "動きを再開" : "動きを止める"}
          </button>
          <button
            className="text-button"
            onClick={() => {
              setCount((v) => v + 1);
              setActivities([]);
            }}
          >
            両画面を読み直す
          </button>
        </div>
      </header>
      <div className="stage-floor">
        <section className="stage-device visitor-device">
          <div className="device-label">
            <div>
              <span className="small-label">旅行者</span>
              <h2>仲間と旅を考える</h2>
            </div>
            <button
              className="text-button"
              onClick={() => setLarge(large === "visitor" ? null : "visitor")}
            >
              {large === "visitor" ? "元の大きさ" : "大きく見る"}
            </button>
          </div>
          <div className="phone-frame">
            <div className="phone-camera" aria-hidden="true" />
            <iframe
              key={`visitor-${count}`}
              ref={visitor}
              src="/stage/visitor"
              title="旅行者の操作画面"
            />
          </div>
        </section>
        <section className="stage-hub" aria-label="案内役の働き">
          <div
            className={`hub-symbol ${latest?.status === "success" ? "connected" : ""}`}
            aria-hidden="true"
          >
            <span />
            <Icon name="leaf" />
            <span />
          </div>
          <p className="eyebrow">旅をつなぐ案内役</p>
          <h2>
            みんなの希望を、
            <br />
            相談できる形へ。
          </h2>
          <p className="hub-intro">
            人数・泊数・予算と、選んだ関心。
            <br />
            確認した情報から候補を見つけ、
            <br />
            選んだ相手へつなぎます。
          </p>
          <div className="hub-steps">
            <span>条件を整理</span>
            <Icon name="arrow" />
            <span>候補を比較</span>
            <Icon name="arrow" />
            <span>相談が届く</span>
          </div>
          <div className="stage-latest" aria-live="polite">
            <span className="small-label">いまの動き</span>
            <p>
              {latest
                ? `${latest.actor === "visitor" ? "旅行者" : "事業者"}：${latest.status === "failure" ? "操作を完了できませんでした" : eventLabels[latest.type]}`
                : "左右の画面から操作を始めてください。"}
            </p>
          </div>
          <ol className="stage-activity" aria-label="操作の履歴">
            {activities.slice(0, 8).map((item) => (
              <li
                key={item.id}
                className={item.status === "failure" ? "failed" : ""}
              >
                <span className="activity-dot" />
                <div>
                  <strong>
                    {item.status === "success"
                      ? eventLabels[item.type]
                      : "操作を完了できませんでした"}
                  </strong>
                  <small>
                    {item.actor === "visitor" ? "旅行者" : "事業者"} ·{" "}
                    {item.time}
                  </small>
                </div>
              </li>
            ))}
          </ol>
        </section>
        <section className="stage-device provider-device">
          <div className="device-label">
            <div>
              <span className="small-label">事業者</span>
              <h2>地域の旅を案内する</h2>
            </div>
            <button
              className="text-button"
              onClick={() => setLarge(large === "provider" ? null : "provider")}
            >
              {large === "provider" ? "元の大きさ" : "大きく見る"}
            </button>
          </div>
          <div className="phone-frame">
            <div className="phone-camera" aria-hidden="true" />
            <iframe
              key={`provider-${count}`}
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
