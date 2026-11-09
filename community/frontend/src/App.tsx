import Choice from "./Choice";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api, ApiError, mediaUrl, setCsrf } from "./api";
import type {
  Bootstrap,
  Community,
  Group,
  Post,
  Preferences as PreferenceData,
  Proposal,
  Trip,
  User,
} from "./types";
import {
  Avatar,
  dateLabel,
  Empty,
  ErrorBox,
  Icon,
  LocalPhoto,
  Modal,
  Tags,
} from "./ui";
import Composer from "./Composer";
import Login from "./Login";
import Preferences from "./Preferences";
import KoPage, { tripCover } from "./KoPage";
import Marketplace from "./Marketplace";
import ProviderWorkspace from "./ProviderWorkspace";
import type { Capabilities } from "./marketplace-types";
import { useNavigationMotion } from "./useNavigationMotion";
import type { MotionTrigger } from "./useNavigationMotion";
const Journal = lazy(() => import("./Journal"));
const Circles = lazy(() => import("./Circles"));
const VisitDialog = lazy(() =>
  import("./Journal").then((module) => ({ default: module.VisitDialog })),
);
const TravelProfile = lazy(() =>
  import("./Journal").then((module) => ({ default: module.TravelProfile })),
);

type Page =
  | "feed"
  | "ko"
  | "ko-legacy"
  | "preferences"
  | "market"
  | "provider"
  | "journal";
type Data = {
  communities: Community[];
  preferences: PreferenceData;
  trips: Trip[];
  proposals: Proposal[];
  groups: Group[];
  capabilities: Capabilities;
};
function CommunityDialog({
  community,
  onClose,
  onChange,
}: {
  community: Community | null;
  onClose: () => void;
  onChange: (c?: Community) => Promise<void>;
}) {
  const [mode, setMode] = useState<"create" | "join" | "detail">(
    community ? "detail" : "create",
  );
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [code, setCode] = useState("");
  const [invite, setInvite] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [leave, setLeave] = useState(false);
  useEffect(() => {
    if (!community) return;
    let active = true;
    api<{ invite_code: string | null }>(`/communities/${community.id}`)
      .then((r) => {
        if (active) setInvite(r.invite_code);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [community]);
  async function submit() {
    setBusy(true);
    setError("");
    try {
      const c = await api<Community>(
        mode === "create" ? "/communities" : "/communities/join",
        "POST",
        mode === "create" ? { name, description } : { invite_code: code },
      );
      await onChange(c);
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function exit() {
    if (!community) return;
    setBusy(true);
    setError("");
    try {
      await api(`/communities/${community.id}/leave`, "POST", {});
      await onChange();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={
        mode === "detail"
          ? community?.name || "コミュニティ"
          : "コミュニティをひらく"
      }
      onClose={onClose}
      busy={busy}
    >
      <ErrorBox message={error} />
      {mode === "detail" ? (
        <>
          <p>{community?.description}</p>
          <p className="muted">{community?.member_count}人のメンバー</p>
          {invite && (
            <div className="invite-box">
              <h3>招待コード</h3>
              <p>一緒に参加したい人に、このコードを伝えてください。</p>
              <code>{invite}</code>
            </div>
          )}
          <div className="separated">
            <button
              className="text-button danger"
              disabled={busy}
              onClick={() => setLeave(true)}
            >
              このコミュニティを退会
            </button>
            {leave && (
              <div className="hint-box">
                <p>
                  投稿は見られなくなり、確認中の旅行提案は取り下げられます。
                </p>
                <button
                  className="button danger-button"
                  disabled={busy}
                  onClick={() => void exit()}
                >
                  退会する
                </button>
              </div>
            )}
          </div>
        </>
      ) : (
        <>
          <div className="segmented">
            <button
              className={mode === "create" ? "selected" : ""}
              onClick={() => setMode("create")}
              disabled={busy}
            >
              新しくつくる
            </button>
            <button
              className={mode === "join" ? "selected" : ""}
              onClick={() => setMode("join")}
              disabled={busy}
            >
              招待から参加
            </button>
          </div>
          {mode === "create" ? (
            <>
              <label className="field">
                コミュニティの名前
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={80}
                  placeholder="例：週末さんぽの会"
                  disabled={busy}
                />
              </label>
              <label className="field">
                どんな集まり？
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  maxLength={500}
                  disabled={busy}
                />
              </label>
            </>
          ) : (
            <label className="field">
              招待コード
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                autoComplete="off"
                disabled={busy}
              />
            </label>
          )}
          <button
            className="button primary full"
            disabled={busy || (mode === "create" ? !name.trim() : !code.trim())}
            onClick={() => void submit()}
          >
            {busy
              ? "保存しています…"
              : mode === "create"
                ? "コミュニティをつくる"
                : "コミュニティに参加"}
          </button>
        </>
      )}
    </Modal>
  );
}
export default function App() {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [data, setData] = useState<Data | null>(null);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [page, setPage] = useState<Page>(
    window.location.pathname === "/stage/visitor" ? "market" : "feed",
  );
  const [communityId, setCommunityId] = useState("");
  const [feed, setFeed] = useState<Post[]>([]);
  const [feedBusy, setFeedBusy] = useState(false);
  const [feedError, setFeedError] = useState("");
  const [composer, setComposer] = useState<Post | true | null>(null);
  const [communityDialog, setCommunityDialog] = useState<
    "new" | "current" | null
  >(null);
  const [switching, setSwitching] = useState(false);
  const [deletePost, setDeletePost] = useState<Post | null>(null);
  const [recordPost, setRecordPost] = useState<Post | null>(null);
  const [profileUser, setProfileUser] = useState<User | null>(null);
  const [circleTarget, setCircleTarget] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [loadKey, setLoadKey] = useState(0);
  const generation = useRef(0);
  const motion = useNavigationMotion(page, !!user, !!user && !!data);
  function clearSession(text: string) {
    motion.reset();
    generation.current++;
    setUser(null);
    setData(null);
    setFeed([]);
    setComposer(null);
    setCommunityDialog(null);
    setDeletePost(null);
    setRecordPost(null);
    setProfileUser(null);
    setCircleTarget("");
    setSwitching(false);
    setCsrf("");
    setMessage(text);
    setCommunityId("");
    setPage(window.location.pathname === "/stage/visitor" ? "market" : "feed");
  }
  async function refresh() {
    const epoch = generation.current;
    const results = await Promise.all([
      api<{ items: Community[] }>("/communities"),
      api<PreferenceData>("/me/preferences"),
      api<{ items: Trip[] }>("/trips"),
      api<{ items: Proposal[] }>("/proposals"),
      api<{ items: Group[] }>("/groups"),
      api<Capabilities>("/marketplace/capabilities"),
    ]);
    if (epoch !== generation.current) return;
    setData({
      communities: results[0].items,
      preferences: results[1],
      trips: results[2].items,
      proposals: results[3].items,
      groups: results[4].items,
      capabilities: results[5],
    });
    if (results[5].providers.length)
      setPage((current) => (current === "feed" ? "provider" : current));
    setCommunityId((current) =>
      results[0].items.some((c) => c.id === current)
        ? current
        : results[0].items[0]?.id || "",
    );
  }
  async function boot() {
    setBooting(true);
    setError("");
    try {
      const b = await api<Bootstrap>("/bootstrap");
      setBootstrap(b);
      try {
        const session = await api<{ user: User; csrf_token: string }>("/me");
        setCsrf(session.csrf_token);
        setUser(session.user);
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 401)) throw e;
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBooting(false);
    }
  }
  useEffect(() => {
    void boot();
    const expire = () =>
      clearSession(
        "ログインの状態が変わりました。もう一度ログインしてください。",
      );
    window.addEventListener("session-invalid", expire);
    return () => window.removeEventListener("session-invalid", expire);
  }, []);
  useEffect(() => {
    if (!user) return;
    let active = true;
    refresh().catch((e) => {
      if (active) setError(e.message);
    });
    return () => {
      active = false;
    };
  }, [user, loadKey]);
  useEffect(() => {
    setFeed([]);
    setFeedError("");
    if (!communityId || !user) return;
    let active = true;
    setFeedBusy(true);
    api<{ items: Post[] }>(`/communities/${communityId}/feed`)
      .then((r) => {
        if (active) setFeed(r.items);
      })
      .catch((e) => {
        if (active) setFeedError(e.message);
      })
      .finally(() => {
        if (active) setFeedBusy(false);
      });
    return () => {
      active = false;
    };
  }, [communityId, user, loadKey]);
  async function changed() {
    await refresh();
    setLoadKey((v) => v + 1);
  }
  async function logout() {
    setActionBusy(true);
    setError("");
    try {
      await api("/logout", "POST", {});
      clearSession("別のアカウントでログインできます。");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionBusy(false);
    }
  }
  async function removePost() {
    if (!deletePost) return;
    setActionBusy(true);
    setError("");
    try {
      await api(`/posts/${deletePost.id}`, "DELETE", {});
      setDeletePost(null);
      await changed();
      setMessage("記録を削除しました。");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionBusy(false);
    }
  }
  function navigate(next: Page, trigger: MotionTrigger = "programmatic") {
    if (next === page) motion.reset();
    else motion.request("navigation", trigger);
    setPage(next);
    setMessage("");
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  const community = data?.communities.find((c) => c.id === communityId) || null;
  const nav = data?.capabilities.providers.length
    ? [
        { id: "provider" as Page, label: "事業者の仕事場", icon: "home" },
        { id: "market" as Page, label: "旅のプラン", icon: "compass" },
      ]
    : [
        { id: "feed" as Page, label: "みんなの記録", icon: "home" },
        { id: "market" as Page, label: "旅を見つける", icon: "compass" },
        { id: "ko" as Page, label: "講を見つける", icon: "compass" },
        { id: "journal" as Page, label: "旅の地図", icon: "pin" },
      ];
  if (booting)
    return (
      <main className="loading-page" aria-busy="true">
        <span className="brand-mark">講</span>
        <p>旅の記録をひらいています…</p>
      </main>
    );
  if (!bootstrap)
    return (
      <main className="loading-page">
        <h1>接続を確認してください</h1>
        <ErrorBox message={error} />
        <button className="button primary" onClick={() => void boot()}>
          もう一度読み込む
        </button>
      </main>
    );
  if (!user)
    return (
      <Login
        message={message}
        onLogin={(u, t, trigger) => {
          motion.request("login", trigger);
          setCsrf(t);
          setUser(u);
          setError("");
          setMessage("");
        }}
      />
    );
  if (!data)
    return (
      <main className="loading-page">
        <p>コミュニティを読み込んでいます…</p>
        <ErrorBox message={error} />
        {error && (
          <button
            className="button primary"
            onClick={() => setLoadKey((v) => v + 1)}
          >
            もう一度読み込む
          </button>
        )}
      </main>
    );
  return (
    <>
      <a className="skip-link" href="#main">
        本文へ移動
      </a>
      <div
        className={`app-shell ${page === "market" || page === "provider" ? "market-wide" : ""}`}
      >
        <aside className="sidebar">
          <button
            className="brand brand-button"
            onClick={(event) =>
              navigate("feed", event.detail ? "pointer" : "keyboard")
            }
            aria-label="講 みんなの記録へ"
          >
            <span className="brand-mark">講</span>
          </button>
          <nav aria-label="メインメニュー">
            {nav.map((n) => (
              <button
                key={n.id}
                className={`nav-item ${page === n.id ? "active" : ""}`}
                aria-current={page === n.id ? "page" : undefined}
                onClick={(event) =>
                  navigate(n.id, event.detail ? "pointer" : "keyboard")
                }
              >
                <Icon name={n.icon} />
                <span>{n.label}</span>
                {n.id === "ko" &&
                  data.proposals.some(
                    (p) =>
                      p.status === "pending" && p.my_response === "pending",
                  ) && <span className="nav-dot" />}
              </button>
            ))}
          </nav>
          <div className="community-list">
            <p className="eyebrow">参加しているコミュニティ</p>
            {data.communities.map((c, i) => (
              <button
                key={c.id}
                className={`community-button ${communityId === c.id ? "selected" : ""}`}
                onClick={() => {
                  setCommunityId(c.id);
                  navigate("feed");
                }}
                aria-pressed={communityId === c.id}
              >
                <span className={`community-symbol tone-${i % 3}`}>
                  <Icon name={i % 2 ? "leaf" : "people"} />
                </span>
                <span>
                  {c.name}
                  <small>{c.member_count}人</small>
                </span>
              </button>
            ))}
            <button
              className="add-community"
              onClick={() => setCommunityDialog("new")}
            >
              <Icon name="plus" />
              つくる・招待から参加
            </button>
          </div>
          <button
            className="button primary sidebar-post"
            disabled={!community}
            onClick={() => setComposer(true)}
          >
            <Icon name="plus" />
            旅の写真を投稿
          </button>
          <button
            className="text-button"
            onClick={(event) =>
              navigate("preferences", event.detail ? "pointer" : "keyboard")
            }
          >
            <Icon name="leaf" />
            自分の好み
          </button>
          <button className="profile-button" onClick={() => setSwitching(true)}>
            <Avatar user={user} />
            <span>
              <strong>{user.name}</strong>
              <small>アカウントを切り替える</small>
            </span>
            <Icon name="logout" />
          </button>
        </aside>
        <div className="mobile-top">
          <button
            className="brand-mark"
            aria-label="みんなの記録へ"
            onClick={(event) =>
              navigate("feed", event.detail ? "pointer" : "keyboard")
            }
          >
            講
          </button>
          {data.communities.length > 0 ? (
            <>
              <label className="sr-only" htmlFor="mobile-community">
                コミュニティ
              </label>
              <Choice
                id="mobile-community"
                value={communityId}
                onChange={(e) => setCommunityId(e.target.value)}
              >
                {data.communities.map((c) => (
                  <option value={c.id} key={c.id}>
                    {c.name}
                  </option>
                ))}
              </Choice>
            </>
          ) : (
            <span className="mobile-workspace-name">
              {data.capabilities.providers[0]?.name || "コミュニティ"}
            </span>
          )}
          {!data.capabilities.providers.length && (
            <button
              className="icon-button"
              aria-label="コミュニティをつくる・招待から参加"
              onClick={() => setCommunityDialog("new")}
            >
              <Icon name="plus" />
            </button>
          )}
          <button
            className="avatar-button"
            aria-label={`${user.name} アカウントを切り替える`}
            onClick={() => setSwitching(true)}
          >
            <Avatar user={user} small />
          </button>
        </div>
        <main
          id="main"
          ref={motion.target}
          className="main-column"
          tabIndex={-1}
          data-motion-state="idle"
        >
          <ErrorBox message={error} />
          {message && (
            <div className="notice" role="status">
              <span>{message}</span>
              <button
                className="icon-button"
                aria-label="お知らせを閉じる"
                onClick={() => setMessage("")}
              >
                <Icon name="close" />
              </button>
            </div>
          )}
          {page === "feed" ? (
            <>
              <header className="feed-header">
                <div>
                  <p className="eyebrow">コミュニティの旅の記録</p>
                  <h1>{community?.name || "みんなの記録"}</h1>
                  <p>
                    {community?.description ||
                      "コミュニティを作成または選択してください。"}
                  </p>
                </div>
                {community && (
                  <button
                    className="community-detail"
                    onClick={() => setCommunityDialog("current")}
                  >
                    <Icon name="people" />
                    <span>{community.member_count}人</span>
                    <Icon name="arrow" />
                  </button>
                )}
              </header>
              <div className="feed-tools">
                <h2>みんなの記録</h2>
                <button
                  className="text-button"
                  disabled={feedBusy}
                  onClick={() => setLoadKey((v) => v + 1)}
                >
                  <Icon name="refresh" />
                  更新
                </button>
              </div>
              <button
                className="quick-post"
                disabled={!community}
                onClick={() => setComposer(true)}
              >
                <Avatar user={user} />
                <span>どんな旅をしてきましたか？</span>
                <Icon name="photo" />
              </button>
              <ErrorBox message={feedError} />
              {feedError && (
                <button
                  className="button secondary"
                  onClick={() => setLoadKey((v) => v + 1)}
                >
                  記録を読み直す
                </button>
              )}
              {feedBusy ? (
                <p className="loading-inline" role="status">
                  みんなの記録を読んでいます…
                </p>
              ) : feed.length === 0 ? (
                <Empty title="投稿はありません">
                  <p>風景、ごはん、街歩き。旅のひとこまから始められます。</p>
                  <button
                    className="button primary"
                    onClick={() =>
                      community ? setComposer(true) : setCommunityDialog("new")
                    }
                  >
                    {community ? "写真を投稿する" : "コミュニティをつくる"}
                  </button>
                </Empty>
              ) : (
                feed.map((post, index) => (
                  <article className="post-card" key={post.id}>
                    <div className="post-head">
                      <Avatar user={post.author} />
                      <div>
                        <button
                          className="journal-author"
                          onClick={() => setProfileUser(post.author)}
                          aria-label={`${post.author.name}の旅のプロフィール`}
                        >
                          <strong>{post.author.name}</strong>
                        </button>
                        <small>
                          {dateLabel(post.created_at)}
                          {post.place_label && ` · ${post.place_label}`}
                        </small>
                      </div>
                      {post.status === "draft" && (
                        <span className="draft-label">下書き</span>
                      )}
                      {post.can_edit && (
                        <button
                          className="text-button"
                          onClick={() => setComposer(post)}
                        >
                          編集
                        </button>
                      )}
                    </div>
                    <div className={`post-images count-${post.media.length}`}>
                      {post.media.map((m, i) => (
                        <LocalPhoto
                          key={m.id}
                          src={mediaUrl(m.url)}
                          alt={`${post.place_label || "旅の記録"}の写真 ${i + 1}`}
                          priority={index === 0 && i === 0}
                        />
                      ))}
                    </div>
                    <div className="post-body">
                      <Tags ids={post.tags} tags={bootstrap.tags} />
                      <p>{post.body}</p>
                      {post.taken_on && (
                        <span className="post-date">
                          <Icon name="calendar" />
                          {post.taken_on}の記録
                        </span>
                      )}
                      <div className="post-footer">
                        <span>
                          <Icon name="people" />
                          {post.status === "draft"
                            ? "自分だけに表示"
                            : `${community?.name}で共有`}
                        </span>
                        {post.can_edit && (
                          <button
                            className="text-button danger"
                            onClick={() => setDeletePost(post)}
                          >
                            削除
                          </button>
                        )}
                      </div>
                      {post.can_edit && (
                        <button
                          className="text-button journal-record-link"
                          onClick={() => setRecordPost(post)}
                        >
                          <Icon name="pin" />
                          旅の地図に残す
                          <Icon name="arrow" />
                        </button>
                      )}
                    </div>
                  </article>
                ))
              )}
            </>
          ) : page === "journal" ? (
            <Suspense fallback={<p role="status">旅の地図をひらいています…</p>}>
              <Journal
                key={user.id}
                user={user}
                communities={data.communities}
                onProfile={() => setProfileUser(user)}
              />
            </Suspense>
          ) : page === "market" ? (
            <Marketplace
              community={community}
              groups={data.groups}
              tags={bootstrap.tags}
              user={user}
              onOpenCircle={(id) => {
                setCircleTarget(id);
                navigate("ko");
              }}
            />
          ) : page === "provider" ? (
            <ProviderWorkspace
              providers={data.capabilities.providers}
              tags={bootstrap.tags}
              user={user}
            />
          ) : page === "ko" ? (
            <Suspense fallback={<p role="status">講をひらいています…</p>}>
              <Circles
                key={user.id}
                community={community}
                communities={data.communities}
                user={user}
                tags={bootstrap.tags}
                initialCircleId={circleTarget}
                onLegacy={() => navigate("ko-legacy")}
              />
            </Suspense>
          ) : page === "ko-legacy" ? (
            <KoPage
              community={community}
              trips={data.trips}
              proposals={data.proposals}
              groups={data.groups}
              tags={bootstrap.tags}
              user={user}
              onRefresh={changed}
              onPreferences={() => navigate("preferences")}
            />
          ) : (
            <Preferences
              key={user.id}
              initial={data.preferences}
              onOpenCircle={(id) => {
                setCircleTarget(id);
                navigate("ko");
              }}
              communities={data.communities}
              tags={bootstrap.tags}
              onSaved={changed}
            />
          )}
        </main>
        <aside className="right-panel">
          <div className="right-heading">
            <h2>旅行案</h2>
          </div>
          {data.trips[0] && (
            <article className="trip-feature">
              <LocalPhoto
                src={tripCover(data.trips[0].cover_key)}
                alt={data.trips[0].area}
              />
              <div>
                <span className="small-label">
                  {data.trips[0].season_label} · {data.trips[0].area}
                </span>
                <h3>{data.trips[0].title}</h3>
                <Tags
                  ids={data.trips[0].tags.slice(0, 3)}
                  tags={bootstrap.tags}
                />
                <button className="text-button" onClick={() => navigate("ko")}>
                  仲間と計画する <Icon name="arrow" />
                </button>
              </div>
            </article>
          )}
          <div className="side-note">
            <span className="round-icon">
              <Icon name="people" />
            </span>
            <h3>関心の設定</h3>
            <p>
              設定した関心は、許可したコミュニティで仲間や旅行案を探すために使います。
            </p>
            <button
              className="text-button"
              onClick={() => navigate("preferences")}
            >
              自分の好みを選ぶ <Icon name="arrow" />
            </button>
          </div>
          {data.groups.length > 0 && (
            <div className="side-group">
              <span className="small-label">参加中の講</span>
              {data.groups.slice(0, 2).map((g) => (
                <button key={g.id} onClick={() => navigate("ko")}>
                  <Icon name="calendar" />
                  <span>
                    {g.purpose}
                    <small>
                      {g.members.length}人 · {g.plan.date || "日程を相談中"}
                    </small>
                  </span>
                  <Icon name="arrow" />
                </button>
              ))}
            </div>
          )}
        </aside>
      </div>
      <nav className="bottom-nav" aria-label="モバイルメニュー">
        {nav.map((n) => (
          <button
            key={n.id}
            aria-label={n.id === "market" ? "旅を探す" : n.label}
            className={page === n.id ? "active" : ""}
            onClick={(event) =>
              navigate(n.id, event.detail ? "pointer" : "keyboard")
            }
            aria-current={page === n.id ? "page" : undefined}
          >
            <Icon name={n.icon} />
            <span>
              {n.id === "feed"
                ? "記録"
                : n.id === "market"
                  ? "探す"
                  : n.id === "ko"
                    ? "講"
                    : n.id === "journal"
                      ? "地図"
                      : "仕事場"}
            </span>
          </button>
        ))}
        {!data.capabilities.providers.length ? (
          <button disabled={!community} onClick={() => setComposer(true)}>
            <Icon name="plus" />
            <span>投稿</span>
          </button>
        ) : (
          <button onClick={() => setSwitching(true)}>
            <Icon name="people" />
            <span>アカウント</span>
          </button>
        )}
      </nav>
      {composer && community && (
        <Composer
          community={community}
          tags={bootstrap.tags}
          post={composer === true ? undefined : composer}
          onClose={() => setComposer(null)}
          onSaved={changed}
        />
      )}{" "}
      {recordPost && (
        <Suspense
          fallback={
            <p className="loading-inline" role="status">
              訪問記録をひらいています…
            </p>
          }
        >
          <VisitDialog
            key={`${user.id}-${recordPost.id}`}
            post={recordPost}
            communities={data.communities}
            onClose={() => setRecordPost(null)}
            onSaved={() => {
              setRecordPost(null);
              navigate("journal");
            }}
          />
        </Suspense>
      )}
      {profileUser && (
        <Suspense
          fallback={
            <p className="loading-inline" role="status">
              旅のプロフィールをひらいています…
            </p>
          }
        >
          <TravelProfile
            key={`${user.id}-${profileUser.id}`}
            person={profileUser}
            owner={profileUser.id === user.id}
            onClose={() => setProfileUser(null)}
          />
        </Suspense>
      )}
      {communityDialog && (
        <CommunityDialog
          community={communityDialog === "current" ? community : null}
          onClose={() => setCommunityDialog(null)}
          onChange={async (c) => {
            await changed();
            if (c) setCommunityId(c.id);
          }}
        />
      )}
      {switching && (
        <Modal
          title="アカウントを切り替える"
          onClose={() => setSwitching(false)}
          busy={actionBusy}
        >
          <p>{user.name}さんとしてログインしています。</p>
          {!data.capabilities.providers.length && (
            <button
              className="button secondary full"
              onClick={() => {
                setSwitching(false);
                setProfileUser(user);
              }}
            >
              <Icon name="pin" />
              旅のプロフィール
            </button>
          )}
          <button
            className="button secondary full"
            onClick={() => {
              setSwitching(false);
              navigate("preferences");
            }}
          >
            <Icon name="leaf" />
            自分の好みを確認する
          </button>
          <p className="muted">
            一度ログアウトして、次のアカウントのパスワードでログインします。
          </p>
          <ErrorBox message={error} />
          <button
            className="button primary full"
            disabled={actionBusy}
            onClick={() => void logout()}
          >
            {actionBusy ? "ログアウトしています…" : "ログアウトして切り替える"}
          </button>
        </Modal>
      )}
      {deletePost && (
        <Modal
          title="この記録を削除しますか？"
          onClose={() => setDeletePost(null)}
          busy={actionBusy}
        >
          <p>
            写真と投稿、写真に結び付いた訪問記録を削除します。県別の実績とバッジも再計算されます。この操作は取り消せません。
          </p>
          <ErrorBox message={error} />
          <div className="dialog-actions">
            <button
              className="button secondary"
              disabled={actionBusy}
              onClick={() => setDeletePost(null)}
            >
              残しておく
            </button>
            <button
              className="button danger-button"
              disabled={actionBusy}
              onClick={() => void removePost()}
            >
              {actionBusy ? "削除中…" : "記録を削除する"}
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
