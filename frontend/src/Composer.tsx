import { useEffect, useRef, useState } from "react";
import { api, mediaUrl } from "./api";
import Choice from "./Choice";
import type { Community, Media, Post, Tag } from "./types";
import {
  Empty,
  ErrorBox,
  Icon,
  LocalPhoto,
  Modal,
  TagPicker,
  Tags,
} from "./ui";
import { SealMark } from "./WaArt";
import { errorMessage } from "./validation";
import "./composer.css";

export default function Composer({
  communities,
  initialCommunityId,
  tags,
  post,
  onClose,
  onSaved,
  onJoinCommunity,
}: {
  communities: Community[];
  initialCommunityId: string;
  tags: Tag[];
  post?: Post;
  onClose: () => void;
  onSaved: (saved: Post) => void;
  onJoinCommunity: () => void;
}) {
  const [communityId, setCommunityId] = useState(
    post?.community_id ||
      initialCommunityId ||
      (communities.length === 1 ? communities[0].id : ""),
  );
  const [media, setMedia] = useState<Media[]>(post?.media || []);
  const [body, setBody] = useState(post?.body || "");
  const [selected, setSelected] = useState(post?.tags || []);
  const [place, setPlace] = useState(post?.place_label || "");
  const [date, setDate] = useState(post?.taken_on || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<Post | undefined>(post);
  const [destinationLocked, setDestinationLocked] = useState(!!post);
  const [confirmed, setConfirmed] = useState(false);
  const [readLocation, setReadLocation] = useState(false);
  const [preview, setPreview] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const lock = useRef(false);
  const activeRequest = useRef<AbortController | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const alive = useRef(true);
  const uploaded = useRef(new Set<string>());
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      activeRequest.current?.abort();
    };
  }, []);
  const community = communities.find((item) => item.id === communityId);
  const hasContent = !!body.trim() || media.length > 0;
  const valid = !!community && hasContent;
  const dirty = post
    ? JSON.stringify([
        body,
        selected,
        place,
        date,
        media.map((item) => item.id),
      ]) !==
      JSON.stringify([
        post.body,
        post.tags,
        post.place_label,
        post.taken_on || "",
        post.media.map((item) => item.id),
      ])
    : hasContent || !!place || !!date || selected.length > 0;
  const candidates = [
    ...new Set(
      media.flatMap((item) => item.analysis.tags.map((tag) => tag.id)),
    ),
  ];
  function edited() {
    setConfirmed(false);
    setError("");
  }
  function showPreview(value: boolean) {
    setPreview(value);
    setConfirmed(false);
    requestAnimationFrame(() => {
      if (alive.current)
        contentRef.current?.closest("dialog")?.scrollTo({ top: 0 });
    });
  }
  function requestClose() {
    if (dirty) setDiscarding(true);
    else onClose();
  }
  function discard() {
    // Only temporary images from this editor are attempted; the server rejects attached images.
    void Promise.allSettled(
      [...uploaded.current].map((id) =>
        api(`/media/${encodeURIComponent(id)}`, "DELETE", {}),
      ),
    );
    onClose();
  }
  function removePhoto(id: string) {
    setMedia((current) => current.filter((item) => item.id !== id));
    edited();
    if (uploaded.current.has(id))
      void api(`/media/${encodeURIComponent(id)}`, "DELETE", {})
        .then(() => {
          uploaded.current.delete(id);
          return undefined;
        })
        .catch(() => undefined);
  }
  async function upload(files: FileList | null) {
    if (!files?.length || lock.current) return;
    const chosen = Array.from(files);
    if (media.length + chosen.length > 5) {
      setError("写真は1回の投稿につき5枚まで選べます。");
      return;
    }
    if (
      chosen.some(
        (file) =>
          !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
          file.size > 12 * 1024 * 1024,
      )
    ) {
      setError("12MB以下のJPEG・PNG・WebPを選んでください。");
      return;
    }
    lock.current = true;
    setBusy(true);
    edited();
    const controller = new AbortController();
    activeRequest.current = controller;
    try {
      // Serialize large uploads to keep memory use bounded on the local machine.
      await chosen.reduce(
        (queue, file) =>
          queue.then(async () => {
            if (!alive.current) return undefined;
            const data = new FormData();
            data.append("file", file);
            const item = await api<Media>(
              readLocation ? "/media?read_location=true" : "/media",
              "POST",
              data,
              { signal: controller.signal },
            );
            uploaded.current.add(item.id);
            if (alive.current) setMedia((current) => [...current, item]);
            return undefined;
          }),
        Promise.resolve(),
      );
    } catch (cause) {
      if (alive.current)
        setError(
          `写真を追加できませんでした。追加済みの写真と文章は残っています。${errorMessage(cause)}`,
        );
    } finally {
      lock.current = false;
      if (alive.current) setBusy(false);
    }
  }
  async function save(publish: boolean) {
    if (lock.current || !valid || (publish && !confirmed)) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setDestinationLocked(true);
    const controller = new AbortController();
    activeRequest.current = controller;
    const payload = {
      body: body.trim(),
      media_ids: media.map((item) => item.id),
      tags: selected,
      place_label: place.trim(),
      taken_on: date || null,
    };
    try {
      let current = draft;
      if (!current) {
        current = await api<Post>(
          "/posts",
          "POST",
          {
            ...payload,
            community_id: communityId,
            client_request_id: requestId,
          },
          { signal: controller.signal },
        );
        if (!alive.current) return;
        setDraft(current);
      }
      const saved = await api<Post>(
        `/posts/${encodeURIComponent(current.id)}`,
        "PATCH",
        { ...payload, status: publish ? "published" : "draft" },
        { signal: controller.signal },
      );
      if (!alive.current) return;
      const savedMediaIds = new Set(saved.media.map((item) => item.id));
      // A failed earlier save may have kept removed uploads attached to its draft.
      // Retry only newly uploaded photos absent from the successfully saved post.
      void Promise.allSettled(
        [...uploaded.current]
          .filter((id) => !savedMediaIds.has(id))
          .map(async (id) => {
            await api(`/media/${encodeURIComponent(id)}`, "DELETE", {});
            uploaded.current.delete(id);
          }),
      );
      setDraft(saved);
      onSaved(saved);
      onClose();
    } catch (cause) {
      if (alive.current)
        setError(
          `保存を完了できませんでした。入力内容は残っています。もう一度保存できます。${errorMessage(cause)}`,
        );
    } finally {
      lock.current = false;
      if (alive.current) setBusy(false);
    }
  }
  const [today] = useState(() =>
    new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" }).format(
      new Date(),
    ),
  );
  return (
    <Modal
      title={post ? "投稿を編集する" : "写真・文章を投稿する"}
      onClose={requestClose}
      busy={busy}
      wide
    >
      <div className="post-composer" ref={contentRef}>
        {discarding ? (
          <section className="composer-discard">
            <h3>保存せずに閉じますか？</h3>
            <p>未保存の変更は失われます。保存済みの下書きは残ります。</p>
            <div className="dialog-actions">
              <button
                className="button secondary"
                onClick={() => setDiscarding(false)}
              >
                編集に戻る
              </button>
              <button className="button danger-button" onClick={discard}>
                保存せず閉じる
              </button>
            </div>
          </section>
        ) : !communities.length ? (
          <Empty title="投稿先のコミュニティに参加してください">
            <p>招待から参加するか、新しいコミュニティを作成できます。</p>
            <button className="button primary" onClick={onJoinCommunity}>
              コミュニティを選ぶ
            </button>
          </Empty>
        ) : (
          <>
            <div className="composer-index" aria-label="投稿の手順">
              <span className={!preview ? "current" : ""}>一　内容を記入</span>
              <span className={preview ? "current" : ""}>二　確認して公開</span>
            </div>
            <ErrorBox message={error} />
            {preview ? (
              <>
                <div className="composer-preview-heading">
                  <SealMark className="composer-seal">投稿</SealMark>
                  <div>
                    <p className="small-label">公開先</p>
                    <h3>{community?.name}</h3>
                    <p className="composer-note">
                      このコミュニティのメンバーだけに公開します。
                    </p>
                  </div>
                </div>
                <article className="composer-preview">
                  {media.length > 0 && (
                    <div className={`composer-photos count-${media.length}`}>
                      {media.map((item, index) => (
                        <LocalPhoto
                          key={item.id}
                          src={mediaUrl(item.url)}
                          alt={`投稿する写真 ${index + 1}`}
                        />
                      ))}
                    </div>
                  )}
                  {body.trim() && (
                    <p className="composer-preview-body">{body.trim()}</p>
                  )}
                  {(place.trim() || date) && (
                    <p className="composer-place">
                      <Icon name="pin" />
                      {place.trim()}
                      {place.trim() && date ? " · " : ""}
                      {date}
                    </p>
                  )}
                  {selected.length > 0 ? (
                    <Tags ids={selected} tags={tags} />
                  ) : (
                    <p className="composer-note">タグなし</p>
                  )}
                </article>
                <label className="composer-confirm">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    disabled={busy}
                    onChange={(event) => setConfirmed(event.target.checked)}
                  />
                  <span>
                    内容・タグ・公開先を確認しました。
                    {media.length > 0
                      ? "写っている人の公開許可も確認しています。"
                      : ""}
                  </span>
                </label>
                <p className="composer-note">
                  投稿だけで訪問実績やポイントは増えません。写真の位置情報は除いて共有します。
                </p>
                <div className="composer-actions">
                  <button
                    className="button secondary"
                    disabled={busy}
                    onClick={() => showPreview(false)}
                  >
                    内容を直す
                  </button>
                  <button
                    className="button primary"
                    disabled={busy || !confirmed || !valid}
                    onClick={() => void save(true)}
                  >
                    {busy ? "保存しています…" : "このコミュニティに公開"}
                    <Icon name="arrow" />
                  </button>
                </div>
                <button
                  className="text-button"
                  disabled={busy || !valid}
                  onClick={() => void save(false)}
                >
                  {post?.status === "published"
                    ? "非公開の下書きに戻す"
                    : "公開せず下書きに保存"}
                </button>
              </>
            ) : (
              <>
                <label className="field" htmlFor="post-community">
                  投稿先
                  <Choice
                    id="post-community"
                    value={communityId}
                    disabled={busy || destinationLocked}
                    onChange={(event) => {
                      if (event.target.value === communityId) return;
                      setCommunityId(event.target.value);
                      setRequestId(crypto.randomUUID());
                      edited();
                    }}
                  >
                    <option value="">コミュニティを選ぶ</option>
                    {communities.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </Choice>
                </label>
                <p className="composer-note">
                  公開先は選んだコミュニティのメンバー。下書きは自分だけに表示します。
                </p>
                <section className="composer-writing">
                  <label className="field">
                    投稿する文章
                    <textarea
                      value={body}
                      onChange={(event) => {
                        setBody(event.target.value);
                        edited();
                      }}
                      placeholder="訪れた場所や、そこで過ごしたことを書いてください。"
                      maxLength={2000}
                      rows={3}
                      disabled={busy}
                    />
                  </label>
                  <small className="composer-count">
                    {body.length} / 2,000文字
                  </small>
                </section>
                {media.length > 0 && (
                  <div className="composer-uploads">
                    {media.map((item, index) => (
                      <div className="composer-photo" key={item.id}>
                        <LocalPhoto
                          src={mediaUrl(item.url)}
                          alt={`選んだ写真 ${index + 1}`}
                        />
                        <button
                          className="remove-image"
                          aria-label={`写真${index + 1}を投稿から外す`}
                          disabled={busy}
                          onClick={() => removePhoto(item.id)}
                        >
                          <Icon name="close" />
                        </button>
                        <small>
                          {item.analysis.tags.length
                            ? "タグ候補あり・本人確認が必要"
                            : "写真のタグを選べます"}
                        </small>
                      </div>
                    ))}
                  </div>
                )}
                {media.length < 5 && (
                  <label
                    className={`composer-upload-button ${busy ? "disabled" : ""}`}
                  >
                    <Icon name="photo" />
                    <span>{busy ? "写真を追加しています…" : "写真を追加"}</span>
                    <input
                      type="file"
                      aria-label="投稿する写真を選ぶ"
                      accept="image/jpeg,image/png,image/webp"
                      multiple
                      disabled={busy}
                      onChange={(event) => {
                        void upload(event.target.files);
                        event.target.value = "";
                      }}
                    />
                  </label>
                )}
                <p className="composer-note">
                  写真は5枚まで・1枚12MB以下
                  <br />
                  JPEG / PNG / WebP
                </p>
                <details className="composer-options">
                  <summary>場所・訪問日・写真の位置情報</summary>
                  <div className="field-row">
                    <label className="field">
                      場所 <span className="optional">任意</span>
                      <input
                        value={place}
                        onChange={(event) => {
                          setPlace(event.target.value);
                          edited();
                        }}
                        maxLength={100}
                        placeholder="例：N西市の北山公園"
                        disabled={busy}
                      />
                    </label>
                    <label className="field">
                      訪れた日 <span className="optional">任意</span>
                      <input
                        type="date"
                        value={date}
                        max={today}
                        disabled={busy}
                        onChange={(event) => {
                          setDate(event.target.value);
                          edited();
                        }}
                      />
                    </label>
                  </div>
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={readLocation}
                      disabled={busy}
                      onChange={(event) =>
                        setReadLocation(event.target.checked)
                      }
                    />
                    <span>
                      これから選ぶ写真の位置情報を読み取る
                      <span className="optional">任意</span>
                      <small className="journal-location-note">
                        位置は自動公開しません。「旅の地図に残す」で本人が確認してから保存できます。
                      </small>
                    </span>
                  </label>
                </details>
                {candidates.length > 0 && (
                  <section className="composer-candidates">
                    <h3>写真のタグ候補</h3>
                    <p className="composer-note">
                      合うものだけ選んでください。関心や好みへ自動設定しません。
                    </p>
                    <div className="tag-options">
                      {candidates.map((id) => (
                        <button
                          type="button"
                          className={`chip ${selected.includes(id) ? "selected" : ""}`}
                          key={id}
                          disabled={busy}
                          aria-pressed={selected.includes(id)}
                          onClick={() => {
                            setSelected((current) =>
                              current.includes(id)
                                ? current.filter((value) => value !== id)
                                : [...current, id],
                            );
                            edited();
                          }}
                        >
                          {tags.find((tag) => tag.id === id)?.label || id}
                          <Icon
                            name={selected.includes(id) ? "check" : "plus"}
                          />
                        </button>
                      ))}
                    </div>
                  </section>
                )}
                <TagPicker
                  tags={tags}
                  value={selected}
                  onChange={(value) => {
                    setSelected(value);
                    edited();
                  }}
                  disabled={busy}
                  label="投稿のタグを選ぶ（任意）"
                />
                {!hasContent && (
                  <p className="composer-help">
                    文章を入力するか、写真を1枚以上追加してください。
                  </p>
                )}
                {!community && (
                  <p className="composer-help">
                    投稿先のコミュニティを選んでください。
                  </p>
                )}
                <div className="composer-actions">
                  <button
                    className="button secondary"
                    disabled={busy || !valid}
                    onClick={() => void save(false)}
                  >
                    {post?.status === "published"
                      ? "非公開の下書きに戻す"
                      : "下書きに保存"}
                  </button>
                  <button
                    className="button primary"
                    disabled={busy || !valid}
                    onClick={() => showPreview(true)}
                  >
                    公開前に確認
                    <Icon name="arrow" />
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
