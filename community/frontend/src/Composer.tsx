import { errorMessage } from "./validation";
import { useState } from "react";
import { api, mediaUrl } from "./api";
import type { Community, Media, Post, Tag } from "./types";
import { ErrorBox, Icon, LocalPhoto, Modal, TagPicker } from "./ui";

export default function Composer({
  community,
  tags,
  post,
  onClose,
  onSaved,
}: {
  community: Community;
  tags: Tag[];
  post?: Post;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [media, setMedia] = useState<Media[]>(post?.media || []);
  const [body, setBody] = useState(post?.body || "");
  const [selected, setSelected] = useState(post?.tags || []);
  const [place, setPlace] = useState(post?.place_label || "");
  const [date, setDate] = useState(post?.taken_on || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<Post | undefined>(post);
  const [confirmed, setConfirmed] = useState(false);
  const [readLocation, setReadLocation] = useState(false);
  async function upload(files: FileList | null) {
    if (!files) return;
    setError("");
    if (media.length + files.length > 5) {
      setError("写真は1回の投稿につき5枚まで選べます。");
      return;
    }
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        if (
          !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
          file.size > 12 * 1024 * 1024
        )
          throw new Error("12MB以下のJPEG・PNG・WebPを選んでください。");
        const data = new FormData();
        data.append("file", file);
        const item = await api<Media>(readLocation ? "/media?read_location=true" : "/media", "POST", data);
        setMedia((previous) => [...previous, item]);
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function save(publish: boolean) {
    setBusy(true);
    setError("");
    try {
      let current = draft;
      if (!current) {
        current = await api<Post>("/posts", "POST", {
          community_id: community.id,
          body,
          media_ids: media.map((m) => m.id),
          tags: selected,
          place_label: place,
          taken_on: date || null,
        });
        setDraft(current);
      }
      await api<Post>(`/posts/${current.id}`, "PATCH", {
        body,
        tags: selected,
        status: publish ? "published" : "draft",
        place_label: place,
        taken_on: date || null,
      });
      await onSaved();
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  const candidates = [
    ...new Set(media.flatMap((m) => m.analysis.tags.map((t) => t.id))),
  ];
  return (
    <Modal
      title={post ? "記録を編集する" : "旅の写真を残す"}
      onClose={onClose}
      busy={busy}
      wide
    >
      <div className="composer-community">
        <Icon name="people" />
        <span>
          公開先 <strong>{community.name}</strong>
        </span>
      </div>
      <p className="muted">
        このコミュニティのメンバーだけが見ることができます。
      </p>
      <ErrorBox message={error} />
      {!draft && <label className="check-row">
        <input type="checkbox" checked={readLocation} disabled={busy} onChange={(event) => setReadLocation(event.target.checked)} />
        <span>これから選ぶ写真の位置情報を読み取る<span className="optional">任意</span><small className="journal-location-note">場所は「旅の地図に残す」で確認してから保存できます。写真自体の位置情報は除いて共有します。</small></span>
      </label>}
      <div className="upload-grid">
        {media.map((m) => (
          <div className="upload-item" key={m.id}>
            <LocalPhoto src={mediaUrl(m.url)} alt="選択した旅の写真" />
            <span className="image-status">
              {m.analysis.message ||
                (m.analysis.method === "predefined-photo-tags-v1"
                  ? "この写真に登録されたタグ候補があります"
                  : m.analysis.tags.length
                    ? "以前のタグ候補を確認できます"
                    : "写真のタグを自分で選べます")}
            </span>
            {!draft && (
              <button
                className="remove-image"
                aria-label="この写真を投稿から外す"
                disabled={busy}
                onClick={() => setMedia(media.filter((i) => i.id !== m.id))}
              >
                <Icon name="close" />
              </button>
            )}
          </div>
        ))}
      </div>
      {!draft && media.length < 5 && (
        <label className={`upload-zone ${busy ? "disabled" : ""}`}>
          <Icon name="photo" />
          <strong>{busy ? "写真を準備しています…" : "写真を選ぶ"}</strong>
          <span>JPEG・PNG・WebP / 1〜5枚 / 1枚12MBまで</span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            disabled={busy}
            onChange={(e) => {
              void upload(e.target.files);
              e.target.value = "";
            }}
          />
        </label>
      )}
      <label className="field">
        旅のひとこと
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="歩いた道、食べたもの。また行きたい場所。"
          maxLength={2000}
          rows={3}
          disabled={busy}
        />
      </label>
      <div className="field-row">
        <label className="field">
          場所 <span className="optional">任意</span>
          <input
            value={place}
            onChange={(e) => setPlace(e.target.value)}
            maxLength={100}
            placeholder="例：軽井沢・旧道のカフェ"
            disabled={busy}
          />
        </label>
        <label className="field">
          訪れた日 <span className="optional">任意</span>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            disabled={busy}
          />
        </label>
      </div>
      {candidates.length > 0 && (
        <div className="hint-box">
          <strong>タグの候補</strong>
          <p>
            使うタグだけ選んでください。好みには自動で設定しません。
          </p>
          <div className="tag-options">
            {candidates.map((id) => (
              <button
                type="button"
                className={`chip ${selected.includes(id) ? "selected" : ""}`}
                key={id}
                disabled={busy}
                aria-pressed={selected.includes(id)}
                onClick={() =>
                  setSelected(
                    selected.includes(id)
                      ? selected.filter((x) => x !== id)
                      : [...selected, id],
                  )
                }
              >
                {tags.find((t) => t.id === id)?.label || id}
                <Icon name={selected.includes(id) ? "check" : "plus"} />
              </button>
            ))}
          </div>
        </div>
      )}
      <TagPicker
        tags={tags}
        value={selected}
        onChange={setSelected}
        disabled={busy}
        label="写真のタグを選ぶ"
      />
      <label className="check-row">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
          disabled={busy}
        />
        <span>
          写真とタグを確認しました。写っている人の公開許可も確認しています。
        </span>
      </label>
      <div className="dialog-actions">
        <button
          className="button secondary"
          disabled={busy || !media.length}
          onClick={() => void save(false)}
        >
          下書きに保存
        </button>
        <button
          className="button primary"
          disabled={busy || !media.length || !confirmed}
          onClick={() => void save(true)}
        >
          {busy ? "保存しています…" : "このコミュニティに公開"}
          <Icon name="arrow" />
        </button>
      </div>
    </Modal>
  );
}
