import { lazy, Suspense, useState } from "react";
import { api } from "./api";
import type {
  Community,
  Grant,
  Preferences as PreferenceData,
  Tag,
} from "./types";
import { ErrorBox, Icon, TagPicker, Tags } from "./ui";
const Occasions = lazy(() => import("./Occasions"));
export default function Preferences({
  initial,
  communities,
  tags,
  onSaved,
  onOpenCircle,
}: {
  initial: PreferenceData;
  communities: Community[];
  tags: Tag[];
  onSaved: () => Promise<void>;
  onOpenCircle: (id: string) => void;
}) {
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [showOccasions, setShowOccasions] = useState(false);
  function grant(
    id: string,
    key: keyof Omit<Grant, "community_id">,
    checked: boolean,
  ) {
    setSaved(false);
    setValue((v) => {
      const existing = v.grants.find((g) => g.community_id === id) || {
        community_id: id,
        use_for_matching: false,
        display_in_matches: false,
        participate: false,
      };
      return {
        ...v,
        grants: [
          ...v.grants.filter((g) => g.community_id !== id),
          { ...existing, [key]: checked },
        ],
      };
    });
  }
  async function save() {
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const updated = await api<PreferenceData>("/me/preferences", "PUT", {
        tags: value.tags,
        learn_from_posts: value.learn_from_posts,
        grants: value.grants,
      });
      setValue(updated);
      await onSaved();
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (showOccasions)
    return (
      <section className="preferences">
        <button className="text-button" onClick={() => setShowOccasions(false)}>
          ← 自分の好みへ
        </button>
        <Suspense
          fallback={<p role="status">誕生日・記念日をひらいています…</p>}
        >
          <Occasions tags={tags} onOpenCircle={onOpenCircle} />
        </Suspense>
      </section>
    );
  return (
    <section className="preferences">
      <div className="page-heading">
        <h1>自分の好み</h1>
        <p>旅行の関心と、コミュニティごとの利用許可を設定します。</p>
        <button
          className="button secondary"
          onClick={() => setShowOccasions(true)}
        >
          <Icon name="calendar" />
          誕生日・記念日
        </button>
      </div>
      <ErrorBox message={error} />
      <section className="surface">
        <div className="section-kicker">
          <Icon name="leaf" />
          <span>旅行の関心</span>
        </div>
        <h2>旅で楽しみたいこと</h2>
        <TagPicker
          tags={tags}
          value={value.tags}
          onChange={(v) => {
            setValue({ ...value, tags: v });
            setSaved(false);
          }}
          disabled={busy}
          label="自分の好みとして選ぶ"
        />
        <p className="muted">
          ここで選んだ好みを、あなたが許可したコミュニティで仲間探しに使います。
        </p>
        <label className="check-row separated">
          <input
            type="checkbox"
            checked={value.learn_from_posts}
            disabled={busy}
            onChange={(e) => {
              setValue({ ...value, learn_from_posts: e.target.checked });
              setSaved(false);
            }}
          />
          <span>
            <strong>自分の公開投稿からも、好みの候補を見つける</strong>
            <small>写真のタグを、そのまま本人の好みと決めつけません。</small>
          </span>
        </label>
        {value.evidence.length > 0 && (
          <div className="hint-box">
            <strong>投稿にあるタグ</strong>
            <Tags
              ids={[...new Set(value.evidence.map((e) => e.tag_id))]}
              tags={tags}
            />
            <p>好みに合うものだけ、上で選んでください。</p>
          </div>
        )}
      </section>
      <section className="surface">
        <h2>コミュニティごとの許可</h2>
        <p className="muted">
          元の投稿や所属名は、別のコミュニティには共有しません。変更すると、確認中の提案が取り下げられることがあります。
        </p>
        {communities.map((c) => {
          const g = value.grants.find((x) => x.community_id === c.id);
          return (
            <fieldset className="permission-group" disabled={busy} key={c.id}>
              <legend>{c.name}</legend>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={g?.use_for_matching || false}
                  onChange={(e) =>
                    grant(c.id, "use_for_matching", e.target.checked)
                  }
                />
                <span>自分の好みを仲間探しに使う</span>
              </label>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={g?.display_in_matches || false}
                  onChange={(e) =>
                    grant(c.id, "display_in_matches", e.target.checked)
                  }
                />
                <span>候補になった相手に名前と共通の好みを見せる</span>
              </label>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={g?.participate || false}
                  onChange={(e) => grant(c.id, "participate", e.target.checked)}
                />
                <span>
                  このコミュニティの旅行候補に入る
                  <small>旅行への参加は、提案のたびに自分で決めます。</small>
                </span>
              </label>
            </fieldset>
          );
        })}
      </section>
      <div className="save-bar">
        <p role="status">
          {saved ? "好みと共有範囲を保存しました。" : "いつでも変更できます。"}
        </p>
        <button
          className="button primary"
          disabled={busy}
          onClick={() => void save()}
        >
          {busy ? "保存しています…" : "好みと許可を保存"}
          <Icon name="check" />
        </button>
      </div>
    </section>
  );
}
