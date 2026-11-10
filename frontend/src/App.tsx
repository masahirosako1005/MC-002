import { errorMessage } from "./validation";
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
import Login from "./Login";
import Preferences from "./Preferences";
import KoPage, { tripCover } from "./KoPage";
import Marketplace from "./Marketplace";
import ProviderWorkspace from "./ProviderWorkspace";
import type { Capabilities } from "./marketplace-types";
import { useCommunityFeed } from "./useCommunityFeed";
import { useNavigationMotion } from "./useNavigationMotion";
import type { MotionTrigger } from "./useNavigationMotion";
import type { CircleDetail } from "./circle-types";
import { emptyDiscoveryFilters, useResumeState } from "./useResumeState";
import type { DiscoveryFilters, ResumeContent, ResumeState } from "./useResumeState";
const Journal = lazy(() => import("./Journal"));
const Daytrip = lazy(() => import("./Daytrip"));
const Composer = lazy(() => import("./Composer"));
const ResidenceProfile = lazy(() => import("./ResidenceProfile"));
const Circles = lazy(() => import("./Circles"));
const VisitDialog = lazy(() =>
  import("./Journal").then((module) => ({ default: module.VisitDialog })),
);
const TravelProfile = lazy(() =>
  import("./Journal").then((module) => ({ default: module.TravelProfile })),
);

type Page =
  | "daytrip"
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
    if (!community) return undefined;
    let active = true;
    api<{ invite_code: string | null }>(`/communities/${community.id}`)
      .then((r) => {
        if (active) setInvite(r.invite_code);
        return undefined;
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
      setError(errorMessage(e));
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
      setError(errorMessage(e));
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
    window.location.pathname === "/stage/provider" ? "provider" : "daytrip",
  );
  const [communityId, setCommunityId] = useState("");
  const [composer, setComposer] = useState<Post | true | null>(null);
  const [postAfterCommunity, setPostAfterCommunity] = useState(false);
  const [communityDialog, setCommunityDialog] = useState<
    "new" | "current" | null
  >(null);
  const [switching, setSwitching] = useState(false);
  const [deletePost, setDeletePost] = useState<Post | null>(null);
  const [recordPost, setRecordPost] = useState<Post | null>(null);
  const [profileUser, setProfileUser] = useState<User | null>(null);
  const [residenceOpen, setResidenceOpen] = useState(false);
  const [circleTarget, setCircleTarget] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [loadKey, setLoadKey] = useState(0);
  const { items: feed, loading: feedBusy, error: feedError, nextCursor: feedNextCursor, loadMore: loadMoreFeed } = useCommunityFeed(user?.id || null, communityId, loadKey);
  const generation = useRef(0);
  const resume = useResumeState(user?.id || null);
  const [appliedResume, setAppliedResume] = useState<{ userId: string; state: ResumeState } | null>(null);
  const [discoveryFilters, setDiscoveryFilters] = useState<DiscoveryFilters>(emptyDiscoveryFilters);
  const resumeReady = !!resume.restore && appliedResume === resume.restore;
  const motion = useNavigationMotion(page, !!user, !!user && !!data && resumeReady);
  function clearSession(text: string) {
    motion.reset();
    resume.reset();
    setAppliedResume(null);
    setDiscoveryFilters(emptyDiscoveryFilters);
    generation.current++;
    setUser(null);
    setData(null);
    setComposer(null);
    setPostAfterCommunity(false);
    setCommunityDialog(null);
    setDeletePost(null);
    setRecordPost(null);
    setProfileUser(null);
    setResidenceOpen(false);
    setCircleTarget("");
    setSwitching(false);
    setCsrf("");
    setMessage(text);
    setCommunityId("");
    setPage(window.location.pathname === "/stage/provider" ? "provider" : "daytrip");
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
    setCommunityId((current) =>
      results[0].items.some((c) => c.id === current)
        ? current
        : "",
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
      setError(errorMessage(e));
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
    if (!user) return undefined;
    let active = true;
    refresh().catch((e) => {
      if (active) setError(e.message);
    });
    return () => {
      active = false;
    };
  }, [user, loadKey]);
  useEffect(() => {
    if (!data || !resume.restore || appliedResume === resume.restore) return;
    const saved = resume.restore.state;
    setPage(saved.version === 0 ? (data.capabilities.providers.length ? "provider" : "daytrip") : saved.page === "circles" ? "ko" : saved.page);
    setCommunityId(saved.community_id || (saved.version === 0 ? data.communities[0]?.id || "" : ""));
    setCircleTarget(saved.circle_id || "");
    setDiscoveryFilters(saved.filters);
    setAppliedResume(resume.restore);
  }, [data, resume.restore, appliedResume]);
  useEffect(() => {
    if (!resumeReady || !resume.restore) return;
    resume.applied(resume.restore.state);
    let persistedPage: ResumeContent["page"];
    if (page === "ko") persistedPage = "circles";
    else if (page === "feed" || page === "market" || page === "journal" || page === "provider" || page === "daytrip") persistedPage = page;
    else return;
    resume.queue({ page: persistedPage, community_id: communityId || null,
      circle_id: communityId ? circleTarget || null : null, filters: discoveryFilters });
  }, [resumeReady, resume.restore, page, communityId, circleTarget, discoveryFilters, resume.queue, resume.applied]);
  function chooseCommunity(id: string) {
    setCommunityId(id);
    setCircleTarget("");
    setDiscoveryFilters(emptyDiscoveryFilters);
  }
  async function openCircle(id: string) {
    const epoch = generation.current;
    try {
      const selected = await api<CircleDetail>(`/circles/${encodeURIComponent(id)}`);
      if (epoch !== generation.current) return;
      setCommunityId(selected.community_id);
      setCircleTarget(selected.status === "open" ? selected.id : "");
      navigate("ko");
    } catch (cause: unknown) {
      if (epoch === generation.current) setError(errorMessage(cause));
    }
  }
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
      setError(errorMessage(e));
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
      setError(errorMessage(e));
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
        { id: "provider" as Page, label: "事業者管理", icon: "home" },
        { id: "market" as Page, label: "旅のプラン", icon: "compass" },
      ]
    : [
        { id: "daytrip" as Page, label: "日帰りの講", icon: "compass" },
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
  if (!data || !resumeReady)
    return (
      <main className="loading-page">
        <p>コミュニティを読み込んでいます…</p>
        <ErrorBox message={error || resume.error} />
        {(error || resume.error) && (
          <button
            className="button primary"
            onClick={() => { setLoadKey((v) => v + 1); resume.retry(); }}
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
        className={`app-shell ${page === "market" || page === "provider" ? "market-wide" : ""} ${data.capabilities.providers.length ? "provider-shell" : ""}`}
      >
        <aside className="sidebar">
          <button
            className="brand brand-button"
            onClick={(event) =>
              navigate(data.capabilities.providers.length ? "provider" : "daytrip", event.detail ? "pointer" : "keyboard")
            }
            aria-label="講 ホームへ"
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
            {!communityId && data.communities.length > 0 && <p className="quiet-note">コミュニティを選んでください。</p>}
            {data.communities.map((c, i) => (
              <button
                key={c.id}
                className={`community-button ${communityId === c.id ? "selected" : ""}`}
                onClick={() => {
                  chooseCommunity(c.id);
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
            onClick={() => setComposer(true)}
          >
            <Icon name="plus" />
            写真・文章を投稿
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
            aria-label="講 ホームへ"
            onClick={(event) =>
              navigate(data.capabilities.providers.length ? "provider" : "daytrip", event.detail ? "pointer" : "keyboard")
            }
          >
            講
          </button>
          {data.capabilities.providers.length > 0 ? (
            <>
              <span className="provider-masthead-name">{data.capabilities.providers.map((provider) => provider.name).join("・")}<small>事業者管理</small></span>
              <nav className="provider-masthead-nav" aria-label="事業者の画面">
                <button className="text-button" aria-current={page === "provider" ? "page" : undefined} onClick={() => navigate("provider")}>管理画面</button>
                <button className="text-button" aria-current={page === "market" ? "page" : undefined} onClick={() => navigate("market")}>旅のプラン</button>
              </nav>
            </>
          ) : data.communities.length > 0 ? (
            <>
              <label className="sr-only" htmlFor="mobile-community">
                コミュニティ
              </label>
              <Choice
                id="mobile-community"
                ariaLabel="コミュニティ"
                ariaDescribedBy={!communityId ? "community-selection-help" : undefined}
                value={communityId}
                onChange={(e) => chooseCommunity(e.target.value)}
              >
                <option value="">コミュニティを選ぶ</option>
                {data.communities.map((c) => (
                  <option value={c.id} key={c.id}>
                    {c.name}
                  </option>
                ))}
              </Choice>
              {!communityId && <span id="community-selection-help" className="sr-only">講の作成や写真の投稿には、コミュニティの選択が必要です。</span>}
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
          className={`main-column ${data.capabilities.providers.length ? "provider-main" : "notebook-page"}`}
          tabIndex={-1}
          data-motion-state="idle"
        >
          <ErrorBox message={error} />
          <ErrorBox message={resume.error} />
          {resume.error && <button className="text-button" onClick={resume.retry}>保存状態を再確認</button>}
          {resume.notice && <p className="quiet-note" role="status">{resume.notice}</p>}
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
          {page === "daytrip" ? (
            <Suspense fallback={<output className="page-load-status">日帰りの講をひらいています…</output>}>
              <Daytrip key={user.id} user={user} initialCircleId={circleTarget}
                onOpenCircle={(id) => void openCircle(id)} onFindCircles={() => navigate("ko")}
                onExplore={() => navigate("market")} />
            </Suspense>
          ) : page === "feed" ? (
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
                onClick={() => setComposer(true)}
              >
                <Avatar user={user} />
                <span>写真・文章を投稿する</span>
                <Icon name="photo" />
              </button>
              {!feed.length && <ErrorBox message={feedError} />}
              {feedError && !feed.length && (
                <button
                  className="button secondary"
                  onClick={() => setLoadKey((v) => v + 1)}
                >
                  記録を読み直す
                </button>
              )}
              {feedBusy && !feed.length ? (
                <output className="loading-inline">
                  みんなの記録を読んでいます…
                </output>
              ) : feed.length === 0 && !feedError ? (
                <Empty title="投稿はありません">
                  <p>写真や文章を、参加しているコミュニティに共有できます。</p>
                  <button
                    className="button primary"
                    onClick={() => setComposer(true)}
                  >
                    写真・文章を投稿する
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
                    {post.media.length > 0 && <div className={`post-images count-${post.media.length}`}>
                      {post.media.map((m, i) => (
                        <LocalPhoto
                          key={m.id}
                          src={mediaUrl(m.url)}
                          alt={`${post.place_label || "旅の記録"}の写真 ${i + 1}`}
                          priority={index === 0 && i === 0}
                        />
                      ))}
                    </div>}
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
                      {post.can_edit && post.media.length > 0 && (
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
              {feed.length > 0 && <div className="feed-pagination"><output aria-live="polite">{feed.length}件を表示しています</output><ErrorBox message={feedError} />{feedError && <button className="text-button" disabled={feedBusy} onClick={() => setLoadKey((value) => value + 1)}>最新の記録から読み直す</button>}{feedNextCursor ? <button className="button secondary full" disabled={feedBusy} onClick={() => void loadMoreFeed()}>{feedBusy ? "続きを読み込んでいます…" : feedError ? "続きをもう一度読み込む" : "続きを読み込む"}</button> : <p>このコミュニティの記録はここまでです。</p>}</div>}
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
              key={`${user.id}-${communityId}`}
              community={community}
              groups={data.groups}
              tags={bootstrap.tags}
              user={user}
              resume={{ filters: discoveryFilters, onFiltersChange: setDiscoveryFilters,
                selectedCircleId: circleTarget, onCircleChange: setCircleTarget }}
              interestTags={bootstrap.tags.filter((tag) => data.preferences.tags.includes(tag.id))}
              interestsAllowed={data.preferences.grants.some((grant) => grant.community_id === communityId && grant.use_for_matching)}
              onEditInterests={() => navigate("preferences")}
              onOpenCircle={(id) => void openCircle(id)}
            />
          ) : page === "provider" ? (
            <ProviderWorkspace
              key={user.id}
              providers={data.capabilities.providers}
              tags={bootstrap.tags}
              user={user}
            />
          ) : page === "ko" ? (
            <Suspense fallback={<p role="status">講をひらいています…</p>}>
              <Circles
                key={`${user.id}-${communityId}`}
                community={community}
                communities={data.communities}
                user={user}
                tags={bootstrap.tags}
                initialCircleId={communityId ? circleTarget : ""}
                discoveryResume={{ filters: discoveryFilters, onFiltersChange: setDiscoveryFilters,
                  selectedCircleId: circleTarget, onCircleChange: setCircleTarget }}
                onSelectedCircle={(id, selectedCommunity) => {
                  setCircleTarget(id);
                  if (selectedCommunity) setCommunityId(selectedCommunity);
                }}
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
              onOpenCircle={(id) => void openCircle(id)}
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
              {n.id === "daytrip" ? "日帰り" : n.id === "feed"
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
          <button onClick={() => setComposer(true)}>
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
      {composer && (
        <Suspense fallback={<output className="page-load-status">投稿をひらいています…</output>}>
        <Composer
          key={`${user.id}-${composer === true ? "new" : composer.id}`}
          communities={data.communities}
          initialCommunityId={communityId}
          tags={bootstrap.tags}
          post={composer === true ? undefined : composer}
          onClose={() => setComposer(null)}
          onJoinCommunity={() => { setComposer(null); setPostAfterCommunity(true); setCommunityDialog("new"); }}
          onSaved={(saved) => {
            chooseCommunity(saved.community_id);
            navigate("feed");
            setMessage(saved.status === "published" ? "コミュニティに投稿を公開しました。" : "下書きを保存しました（自分のみ）。");
            setLoadKey((value) => value + 1);
          }}
        />
        </Suspense>
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
      {residenceOpen && <Suspense fallback={<output className="page-load-status">地域の設定をひらいています…</output>}><ResidenceProfile key={user.id} onClose={() => setResidenceOpen(false)} onSaved={() => { setResidenceOpen(false); setMessage("居住地域と共有設定を保存しました。"); }} /></Suspense>}
      {communityDialog && (
        <CommunityDialog
          community={communityDialog === "current" ? community : null}
          onClose={() => { setCommunityDialog(null); setPostAfterCommunity(false); }}
          onChange={async (c) => {
            await changed();
            if (c) {
              chooseCommunity(c.id);
              if (postAfterCommunity) { setPostAfterCommunity(false); setComposer(true); }
            }
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
          {!data.capabilities.providers.length && <button
            className="button secondary full"
            onClick={() => {
              setSwitching(false);
              setResidenceOpen(true);
            }}
          >
            <Icon name="home" />
            居住地域と共有設定
          </button>}
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
