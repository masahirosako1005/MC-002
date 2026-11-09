import { useEffect, useRef, useState } from "react";
import { api, mediaUrl } from "./api";
import Choice from "./Choice";
import { Avatar, Empty, ErrorBox, Icon, LocalPhoto, Modal } from "./ui";
import type { Community, Post, User } from "./types";
import type { BadgeProgress, JournalCatalog, JournalPhoto, JournalProfile, Journey, Prefecture, Visit } from "./journal-types";
import "./journal.css";

const today = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" }).format(new Date());
const project = (latitude: number, longitude: number) => ({ x: 25 + (longitude - 127) * 19, y: 24 + (46 - latitude) * 17 });
const land = [
  [[141.6,45.5],[143.4,44.3],[145.6,44.3],[145.3,43.4],[144.4,42.9],[143.2,42],[141.7,42.6],[140.8,41.4],[139.9,41.5],[140.3,42.5],[141.1,43.2],[141.6,45.5]],
  [[140.5,41.5],[141.4,41.3],[141.4,40.5],[142,39.5],[141.8,38.7],[141.1,38.1],[140.9,36.7],[140.7,35.7],[140,35],[139.5,35.3],[139.1,34.7],[138.6,34.6],[138.4,35],[137.1,34.6],[136.8,34.7],[136.9,34.2],[135.8,33.4],[135,33.9],[135.1,34.6],[134.4,34.7],[133.3,34.3],[132.5,34.1],[131,33.9],[130.9,34.4],[132,34.5],[133.2,35.5],[134.7,35.6],[135.7,35.5],[136,35.8],[136.7,36.1],[136.7,37.4],[137.3,37.5],[137.2,36.8],[138.2,37.3],[139.4,38.2],[139.9,39],[140,40],[140.5,41.5]],
  [[134.6,34.3],[134.7,33.8],[134.2,33.3],[133.7,33.6],[133,32.8],[132.5,32.9],[132.4,33.5],[133.2,34],[134.6,34.3]],
  [[131,33.9],[131.8,33.6],[131.9,32.9],[131.4,31.5],[130.8,31],[130.5,31.6],[130.2,31.3],[130,32.3],[129.6,32.6],[129.6,33.3],[130.3,33.9],[131,33.9]],
  [[127.7,26.1],[128.3,26.8],[128,26.7],[127.6,26.2],[127.7,26.1]],
];
const landPath = land.map((island) => island.map(([longitude, latitude], index) => { const p = project(latitude, longitude); return `${index ? "L" : "M"}${p.x},${p.y}`; }).join(" ") + " Z").join(" ");
function Pager({ page, count, size, onChange, label }: { page: number; count: number; size: number; onChange: (page: number) => void; label: string }) {
  if (count <= size) return null;
  return <nav className="journal-pager" aria-label={`${label}のページ`}><button className="button secondary" disabled={page === 0} onClick={() => onChange(page - 1)}>前へ</button><span>{page * size + 1}〜{Math.min((page + 1) * size, count)} / {count}件</span><button className="button secondary" disabled={(page + 1) * size >= count} onClick={() => onChange(page + 1)}>次へ</button></nav>;
}

function JourneyMap({ prefectures, visits, selected, onSelect, visited = [] }: { prefectures: Prefecture[]; visits: Visit[]; selected?: string; onSelect?: (id: string) => void; visited?: Prefecture[] }) {
  const visitedIds = new Set([...visited.map((p) => p.id), ...visits.map((v) => v.prefecture_id)]);
  return <figure className="journey-map">
    <div className="journey-map-caption"><span><Icon name="pin" />旅の足あと</span><small>日本の概略図</small></div>
    <svg viewBox="0 0 420 390" role="img" aria-label={`日本の旅の地図。${visitedIds.size}都道府県、${visits.length}件の訪問記録。下の一覧で場所を選べます。`}>
      <path d={landPath} className="journal-land" />
      {prefectures.map((prefecture) => { const p = project(prefecture.latitude, prefecture.longitude); return <circle key={prefecture.id} cx={p.x} cy={p.y} r={visitedIds.has(prefecture.id) ? 4.5 : 2} className={visitedIds.has(prefecture.id) ? "journal-prefecture visited" : "journal-prefecture"}><title>{prefecture.name}{visitedIds.has(prefecture.id) ? "・訪問記録あり" : ""}</title></circle>; })}
      {visits.map((visit, index) => {
        const prefecture = prefectures.find((p) => p.id === visit.prefecture_id);
        if (!prefecture) return null;
        const p = project(visit.latitude ?? prefecture.latitude, visit.longitude ?? prefecture.longitude);
        return <g key={visit.id} className={selected === visit.id ? "journal-map-pin selected" : "journal-map-pin"} onClick={() => onSelect?.(visit.id)}>
          <title>{visit.place_label}・{visit.visited_on}{visit.latitude === null ? "・県の代表点" : "・本人確認した位置"}</title>
          <circle cx={p.x} cy={p.y} r={selected === visit.id ? 13 : 10} />
          <text x={p.x} y={p.y + 3.5} textAnchor="middle">{index + 1}</text>
        </g>;
      })}
      <text x="28" y="314" className="journal-map-label">沖縄</text>
      <text x="295" y="90" className="journal-map-label">北海道</text>
      <text x="33" y="30" className="journal-map-word">TRAVEL NOTES</text>
    </svg>
    <figcaption>座標がない記録は県の代表点に表示します。境界や道路の案内図ではありません。</figcaption>
  </figure>;
}

function BadgeCard({ badge, prefectures }: { badge: BadgeProgress; prefectures: Prefecture[] }) {
  return <article className={`journal-badge ${badge.earned ? "earned" : ""}`}>
    <span className="journal-medal" aria-hidden="true"><Icon name={badge.earned ? "check" : "compass"} /></span>
    <div className="journal-badge-copy"><p className="eyebrow">{badge.earned ? "獲得したバッジ" : "次の足あと"}</p><h3>{badge.title}</h3><p>{badge.description}</p>
      <div className="journal-progress"><progress value={badge.achieved_count} max={badge.total_count} aria-label={`${badge.title}の達成状況`} /><strong>{badge.achieved_count} / {badge.total_count}県</strong></div>
      <div className="journal-region-chips">{badge.prefecture_ids.map((id) => <span className={badge.visited_prefecture_ids.includes(id) ? "visited" : ""} key={id}>{badge.visited_prefecture_ids.includes(id) && <Icon name="check" />}{prefectures.find((p) => p.id === id)?.name || id}</span>)}</div>
      <p className="journal-badge-condition">{badge.earned ? "4県の訪問記録がそろいました。" : `あと${badge.remaining_prefecture_ids.length}県：${badge.remaining_prefecture_ids.map((id) => prefectures.find((p) => p.id === id)?.name || id).join("・")}`}</p>
    </div>
  </article>;
}

function VisitCard({ visit, index, selected, onSelect, onEdit, onDelete, journeyTitle }: { visit: Visit; index: number; selected?: boolean; onSelect?: () => void; onEdit?: () => void; onDelete?: () => void; journeyTitle?: string }) {
  return <article className={`journal-visit ${selected ? "selected" : ""}`}>
    {visit.media_url && <LocalPhoto src={mediaUrl(visit.media_url)} alt={`${visit.place_label}の旅の写真`} />}
    <div className="journal-visit-copy"><small>{visit.visited_on} · {visit.prefecture_name}</small>
      <button className="journal-place-button" onClick={onSelect} disabled={!onSelect}><span>{index + 1}</span><h3>{visit.place_label}</h3></button>
      {journeyTitle && <p>{journeyTitle}</p>}
      <p className="journal-visit-meta">{visit.latitude === null ? "県の代表点に表示" : "本人が位置を確認"} · {visit.visibility === "private" ? "自分だけ" : "選んだコミュニティで共有"}</p>
      {onEdit && <div className="journal-card-actions"><button className="text-button" onClick={onEdit}>記録を編集</button><button className="text-button danger" onClick={onDelete}>削除</button></div>}
    </div>
  </article>;
}

type VisitDialogProps = { post?: Post; visit?: Visit; initialJourney?: string; communities: Community[]; onClose: () => void; onSaved: () => void };
export function VisitDialog({ post, visit, initialJourney = "", communities, onClose, onSaved }: VisitDialogProps) {
  const [catalog, setCatalog] = useState<JournalCatalog | null>(null);
  const [journeys, setJourneys] = useState<Journey[]>([]);
  const [photos, setPhotos] = useState<JournalPhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [photoPage, setPhotoPage] = useState(0);
  const [loadKey, setLoadKey] = useState(0);
  const [journeyId, setJourneyId] = useState(visit?.journey_id || initialJourney);
  const [newTitle, setNewTitle] = useState("");
  const [prefectureId, setPrefectureId] = useState(visit?.prefecture_id || "");
  const [place, setPlace] = useState(visit?.place_label || post?.place_label || "");
  const [date, setDate] = useState(visit?.visited_on || post?.taken_on || today());
  const [mediaId, setMediaId] = useState(visit?.media_id || post?.media[0]?.id || "");
  const [mode, setMode] = useState<"prefecture" | "exif" | "precise">(visit?.source === "exif" ? "exif" : visit?.latitude != null ? "precise" : "prefecture");
  const [latitude, setLatitude] = useState(visit?.latitude?.toString() || "");
  const [longitude, setLongitude] = useState(visit?.longitude?.toString() || "");
  const [visibility, setVisibility] = useState<"private" | "community">(visit?.visibility || "private");
  const [communityId, setCommunityId] = useState(visit?.community_id || post?.community_id || communities[0]?.id || "");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const keys = useRef(new Map<string, string>());
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  useEffect(() => {
    let alive = true;
    setLoading(true); setError("");
    Promise.all([api<JournalCatalog>("/journal/catalog"), api<{ items: Journey[] }>("/journal/journeys"), api<{ items: JournalPhoto[] }>("/journal/media")]).then(([c, j, p]) => {
      if (!alive) return;
      setCatalog(c); setJourneys(j.items); setPhotos(p.items);
      const selectablePhotos = post ? p.items.filter((photo) => post.media.some((m) => m.id === photo.id)) : p.items;
      setPhotoPage(Math.max(0, Math.floor(selectablePhotos.findIndex((photo) => photo.id === mediaId) / 12)));
    }).catch((e) => { if (alive) setError(e.message); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [loadKey]);
  const storedCandidate = photos.find((photo) => photo.id === mediaId)?.location_candidate;
  const candidate = storedCandidate || (visit?.source === "exif" && mediaId === visit.media_id && visit.latitude != null && visit.longitude != null ? { latitude: visit.latitude, longitude: visit.longitude } : null);
  const availablePhotos = post ? photos.filter((photo) => post.media.some((m) => m.id === photo.id)) : photos;
  const shownPhotos = availablePhotos.slice(photoPage * 12, (photoPage + 1) * 12);
  function requestKey(payload: unknown) { const key = JSON.stringify(payload); if (!keys.current.has(key)) keys.current.set(key, crypto.randomUUID()); return keys.current.get(key)!; }
  async function save() {
    setError(""); setBusy(true);
    try {
      let selectedJourney = journeyId;
      if (!selectedJourney) {
        const payload = { title: newTitle.trim() };
        const created = await api<Journey>("/journal/journeys", "POST", { ...payload, request_key: requestKey(payload) });
        if (!active.current) return;
        selectedJourney = created.id; setJourneyId(created.id); setJourneys((old) => [...old, created]);
      }
      const payload = { journey_id: selectedJourney, prefecture_id: prefectureId, visited_on: date, place_label: place.trim(), latitude: mode === "exif" ? candidate?.latitude ?? null : mode === "precise" ? Number(latitude) : null, longitude: mode === "exif" ? candidate?.longitude ?? null : mode === "precise" ? Number(longitude) : null, media_id: mediaId || null, source: mode === "exif" ? "exif" : "manual", visibility, community_id: visibility === "community" ? communityId : null, confirmed: true };
      await api(visit ? `/journal/visits/${visit.id}` : "/journal/visits", visit ? "PUT" : "POST", { ...payload, ...(visit ? { version: visit.version } : { request_key: requestKey(payload) }) });
      if (active.current) onSaved();
    } catch (e) { if (active.current) setError((e as Error).message); }
    finally { if (active.current) setBusy(false); }
  }
  async function discardCandidate() {
    setBusy(true); setError("");
    try { await api(`/journal/media/${mediaId}/location-candidate`, "DELETE", {}); if (!active.current) return; setPhotos((old) => old.map((photo) => photo.id === mediaId ? { ...photo, location_candidate: null } : photo)); if (mode === "exif" && visit?.source !== "exif") setMode("prefecture"); setConfirmed(false); }
    catch (e) { if (active.current) setError((e as Error).message); }
    finally { if (active.current) setBusy(false); }
  }
  const validCoordinates = mode !== "precise" || (latitude.trim() !== "" && longitude.trim() !== "" && Number.isFinite(Number(latitude)) && Number.isFinite(Number(longitude)) && Math.abs(Number(latitude)) <= 90 && Math.abs(Number(longitude)) <= 180);
  const canSave = !loading && catalog && confirmed && prefectureId && place.trim() && date && date <= today() && (journeyId || newTitle.trim()) && validCoordinates && (mode !== "exif" || candidate) && (visibility !== "community" || communityId);
  return <Modal title={visit ? "訪問記録を編集" : "旅の地図に残す"} onClose={onClose} busy={busy} wide>
    <div className="journal-form">
      <p className="muted">訪れた場所を、写真と一緒に振り返る記録です。行きたい場所の保存とは分けて残します。</p>
      <ErrorBox message={error} />
      {loading ? <p role="status">旅と写真を読み込んでいます…</p> : !catalog ? <button className="button secondary" onClick={() => setLoadKey((v) => v + 1)}>もう一度読み込む</button> : <>
        <label className="field">残す旅<Choice value={journeyId} disabled={busy} onChange={(e) => { setJourneyId(e.target.value); setConfirmed(false); }}><option value="">新しい旅をつくる</option>{journeys.map((journey) => <option value={journey.id} key={journey.id}>{journey.title}</option>)}</Choice></label>
        {!journeyId && <label className="field">旅の名前<input value={newTitle} maxLength={100} placeholder="例：秋の東海をめぐる旅" disabled={busy} onChange={(e) => setNewTitle(e.target.value)} /></label>}
        {availablePhotos.length > 0 && <fieldset className="journal-photo-picker" disabled={busy}><legend>記録に添える写真</legend><div><button type="button" className={!mediaId ? "selected" : ""} aria-pressed={!mediaId} onClick={() => { setMediaId(""); setMode("prefecture"); setConfirmed(false); }}>写真なし</button>{shownPhotos.map((photo, index) => <button type="button" key={photo.id} className={mediaId === photo.id ? "selected" : ""} aria-label={`写真${photoPage * 12 + index + 1}を訪問記録に添える`} aria-pressed={mediaId === photo.id} onClick={() => { setMediaId(photo.id); setMode("prefecture"); setConfirmed(false); }}><LocalPhoto src={mediaUrl(photo.url)} alt={`旅の写真 ${photoPage * 12 + index + 1}`} /></button>)}</div><Pager page={photoPage} count={availablePhotos.length} size={12} onChange={setPhotoPage} label="写真" /></fieldset>}
        <div className="field-row"><label className="field">訪れた都道府県<Choice value={prefectureId} disabled={busy} onChange={(e) => { setPrefectureId(e.target.value); setConfirmed(false); }}><option value="">都道府県を選ぶ</option>{catalog.prefectures.map((prefecture) => <option value={prefecture.id} key={prefecture.id}>{prefecture.name}</option>)}</Choice></label><label className="field">訪れた日<input type="date" value={date} max={today()} disabled={busy} onChange={(e) => { setDate(e.target.value); setConfirmed(false); }} /></label></div>
        <label className="field">訪れた場所<input value={place} maxLength={100} disabled={busy} placeholder="例：名古屋城の庭園" onChange={(e) => { setPlace(e.target.value); setConfirmed(false); }} /></label>
        <fieldset className="journal-location-options" disabled={busy}><legend>地図に残す位置</legend><div className="journal-option-row">{([['prefecture', '県の目安'], ...(candidate ? [['exif', '写真に記録された位置']] : []), ['precise', '座標を指定']] as [typeof mode, string][]).map(([value, label]) => <button type="button" key={value} aria-pressed={mode === value} className={`chip ${mode === value ? "selected" : ""}`} onClick={() => { setMode(value); setConfirmed(false); }}>{label}</button>)}</div></fieldset>
        {mode === "prefecture" && <p className="journal-note">県の代表点に表示します。実際に訪れた地点の座標は保存しません。</p>}
        {candidate && <div className="journal-candidate"><strong>{storedCandidate ? "写真に位置情報がありました" : "この訪問で確認済みの写真の位置"}</strong><p>緯度 {candidate.latitude.toFixed(5)} / 経度 {candidate.longitude.toFixed(5)}</p><p>場所と都道府県を確かめてから使ってください。</p>{storedCandidate && <button className="text-button" disabled={busy} onClick={() => void discardCandidate()}>読み取った位置候補を破棄する</button>}</div>}
        {mediaId && !candidate && <p className="journal-note">この写真に読み取り済みの位置候補はありません。場所を自分で指定できます。</p>}
        {mode === "precise" && <div className="field-row"><label className="field">緯度<input type="number" inputMode="decimal" step="any" min="-90" max="90" value={latitude} disabled={busy} onChange={(e) => { setLatitude(e.target.value); setConfirmed(false); }} placeholder="35.1856" /></label><label className="field">経度<input type="number" inputMode="decimal" step="any" min="-180" max="180" value={longitude} disabled={busy} onChange={(e) => { setLongitude(e.target.value); setConfirmed(false); }} placeholder="136.8990" /></label></div>}
        <fieldset className="journal-location-options" disabled={busy}><legend>場所名・訪問日・写真の共有先</legend><div className="journal-option-row"><button type="button" className={`chip ${visibility === "private" ? "selected" : ""}`} aria-pressed={visibility === "private"} onClick={() => { setVisibility("private"); setConfirmed(false); }}>自分だけ</button><button type="button" className={`chip ${visibility === "community" ? "selected" : ""}`} aria-pressed={visibility === "community"} disabled={!communities.length} onClick={() => { setVisibility("community"); setConfirmed(false); }}>コミュニティ</button></div></fieldset>
        {visibility === "community" && <label className="field">共有するコミュニティ<Choice value={communityId} disabled={busy} onChange={(e) => { setCommunityId(e.target.value); setConfirmed(false); }}>{communities.map((community) => <option value={community.id} key={community.id}>{community.name}</option>)}</Choice></label>}
        <div className="journal-share-preview"><Icon name="people" /><p>{visibility === "private" ? "この訪問記録は自分だけに表示します。" : `${communities.find((community) => community.id === communityId)?.name || "選んだコミュニティ"}のメンバーへ、県・場所名・訪問日を共有します。写真は同じ共有先に公開済みの場合だけ表示されます。`}<small>詳細な座標は本人だけに表示します。県別の実績・バッジの公開は、プロフィールで別に選べます。</small></p></div>
        <label className="check-row"><input type="checkbox" checked={confirmed} disabled={busy} onChange={(e) => setConfirmed(e.target.checked)} /><span>この日に自分が訪れた場所で、位置と共有先を確認しました。</span></label>
        <p className="journal-note">本人の確認による記録です。位置情報だけで実際の訪問を認証するものではありません。</p>
        <div className="dialog-actions"><button className="button secondary" disabled={busy} onClick={onClose}>閉じる</button><button className="button primary" disabled={busy || !canSave} onClick={() => void save()}>{busy ? "保存しています…" : visit ? "変更を保存" : "訪問記録を保存"}<Icon name="check" /></button></div>
      </>}
    </div>
  </Modal>;
}

export function TravelProfile({ person, owner, onClose }: { person: User; owner: boolean; onClose: () => void }) {
  const [profile, setProfile] = useState<JournalProfile | null>(null);
  const [catalog, setCatalog] = useState<JournalCatalog | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadKey, setLoadKey] = useState(0);
  const [selected, setSelected] = useState("");
  const [visitPage, setVisitPage] = useState(0);
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  useEffect(() => {
    let alive = true; setLoading(true); setError(""); setProfile(null);
    Promise.all([api<JournalProfile>(`/journal/profile/${person.id}`), api<JournalCatalog>("/journal/catalog")]).then(([p, c]) => { if (alive) { setProfile(p); setCatalog(c); } }).catch((e) => { if (alive) setError(e.message); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [person.id, loadKey]);
  async function share(value: boolean) {
    if (!profile) return; setBusy(true); setError("");
    try { const p = await api<JournalProfile>("/journal/profile", "PUT", { share_achievements: value, version: profile.version }); if (active.current) setProfile(p); }
    catch (e) { if (active.current) setError((e as Error).message); }
    finally { if (active.current) setBusy(false); }
  }
  const profilePage = Math.min(visitPage, Math.max(0, Math.ceil((profile?.shared_visits.length || 0) / 8) - 1));
  const shownVisits = profile?.shared_visits.slice(profilePage * 8, (profilePage + 1) * 8) || [];
  return <Modal title="旅のプロフィール" onClose={onClose} busy={busy} wide><div className="journal-profile">
    <header className="journal-profile-head"><Avatar user={person} /><div><p className="eyebrow">旅の足あと</p><h2>{person.name}</h2></div></header>
    <ErrorBox message={error} />
    {loading ? <p role="status">旅の足あとを読み込んでいます…</p> : profile && catalog ? <>
      {owner && <div className="journal-sharing"><h3>実績の見せ方</h3><p>同じコミュニティのメンバーに、訪問した県とバッジを見せられます。</p><label className="check-row"><input type="checkbox" checked={profile.share_achievements} disabled={busy} onChange={(e) => void share(e.target.checked)} /><span>{busy ? "保存しています…" : "県別の実績とバッジを共有する"}</span></label><small>県の一覧とバッジのみ。場所名・訪問日・写真の共有は訪問記録ごとに選びます。</small><p className="journal-sharing-state" role="status">現在：{profile.share_achievements ? "同じコミュニティに公開" : "実績は自分だけ"}</p></div>}
      {(owner || profile.share_achievements) ? <><p className="journal-profile-total"><strong>{profile.visited_prefectures.length}</strong>都道府県の旅の記録</p>{profile.badges.map((badge) => <BadgeCard key={badge.id} badge={badge} prefectures={catalog.prefectures} />)}<div className="journal-region-chips">{profile.visited_prefectures.map((prefecture) => <span className="visited" key={prefecture.id}><Icon name="check" />{prefecture.name}</span>)}</div></> : <p className="journal-private">県別の実績とバッジは公開されていません。</p>}
      <p className="journal-note">{profile.evidence_note}</p>
      <h3>{owner ? "自分の訪問記録" : "共有されている訪問記録"}</h3>
      {profile.shared_visits.length ? <><JourneyMap prefectures={catalog.prefectures} visited={profile.visited_prefectures} visits={shownVisits} selected={selected} onSelect={setSelected} />{!owner && <p className="journal-note">この地図は県の代表点を表示しています。詳細な座標は共有されません。</p>}<div className="journal-visits">{shownVisits.map((visit, index) => <VisitCard key={visit.id} visit={visit} index={index} selected={selected === visit.id} onSelect={() => setSelected(visit.id)} />)}</div><Pager page={profilePage} count={profile.shared_visits.length} size={8} onChange={setVisitPage} label="訪問記録" /></> : <p className="muted">{owner ? "訪問記録を残すと、地図と写真がここに並びます。" : "共有されている訪問記録はまだありません。"}</p>}
    </> : <button className="button secondary" onClick={() => setLoadKey((v) => v + 1)}>もう一度読み込む</button>}
  </div></Modal>;
}

export default function Journal({ user, communities, onProfile }: { user: User; communities: Community[]; onProfile: () => void }) {
  const [catalog, setCatalog] = useState<JournalCatalog | null>(null);
  const [journeys, setJourneys] = useState<Journey[]>([]);
  const [profile, setProfile] = useState<JournalProfile | null>(null);
  const [journeyId, setJourneyId] = useState("");
  const [selected, setSelected] = useState("");
  const [visitPage, setVisitPage] = useState(0);
  const [editing, setEditing] = useState<Visit | "new" | null>(null);
  const [deleting, setDeleting] = useState<Visit | Journey | null>(null);
  const [rename, setRename] = useState<Journey | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loadKey, setLoadKey] = useState(0);
  const [people, setPeople] = useState<User[] | null>(null);
  const [peopleCommunity, setPeopleCommunity] = useState(communities[0]?.id || "");
  const [person, setPerson] = useState<User | null>(null);
  const [peopleOpen, setPeopleOpen] = useState(false);
  const [peopleError, setPeopleError] = useState("");
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  useEffect(() => {
    let alive = true; setLoading(true); setError("");
    Promise.all([api<JournalCatalog>("/journal/catalog"), api<{ items: Journey[] }>("/journal/journeys"), api<JournalProfile>(`/journal/profile/${user.id}`)]).then(([c, j, p]) => { if (alive) { setCatalog(c); setJourneys(j.items); setProfile(p); setJourneyId((id) => j.items.some((journey) => journey.id === id) ? id : ""); } }).catch((e) => { if (alive) setError(e.message); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [user.id, loadKey]);
  useEffect(() => {
    if (!peopleOpen || !peopleCommunity) return;
    let alive = true; setPeople(null); setPeopleError("");
    api<{ items: User[] }>(`/journal/people?community_id=${encodeURIComponent(peopleCommunity)}`).then((r) => { if (alive) setPeople(r.items); }).catch((e) => { if (alive) setPeopleError(e.message); });
    return () => { alive = false; };
  }, [peopleOpen, peopleCommunity]);
  const visits = (profile?.shared_visits || []).filter((visit) => !journeyId || visit.journey_id === journeyId);
  const currentPage = Math.min(visitPage, Math.max(0, Math.ceil(visits.length / 8) - 1));
  const shownVisits = visits.slice(currentPage * 8, (currentPage + 1) * 8);
  const currentJourney = journeys.find((journey) => journey.id === journeyId);
  function refresh() { setLoadKey((key) => key + 1); }
  async function remove() {
    if (!deleting) return; setBusy(true); setError("");
    try { await api(`/journal/${"visited_on" in deleting ? "visits" : "journeys"}/${deleting.id}`, "DELETE", { version: deleting.version }); if (active.current) { setDeleting(null); setSelected(""); refresh(); } }
    catch (e) { if (active.current) setError((e as Error).message); }
    finally { if (active.current) setBusy(false); }
  }
  async function renameJourney() {
    if (!rename) return; setBusy(true); setError("");
    try { await api(`/journal/journeys/${rename.id}`, "PUT", { title: title.trim(), version: rename.version }); if (active.current) { setRename(null); refresh(); } }
    catch (e) { if (active.current) setError((e as Error).message); }
    finally { if (active.current) setBusy(false); }
  }
  return <section className="journal-page">
    <header className="journal-heading"><p className="eyebrow">写真から、旅の足あとへ</p><h1>旅の地図</h1><p>歩いたまちと、心に残った一枚を。</p><div className="journal-toolbar"><button className="button primary" disabled={loading} onClick={() => setEditing("new")}><Icon name="plus" />訪問記録を残す</button><button className="text-button" disabled={loading} onClick={refresh}><Icon name="refresh" />更新</button></div></header>
    <ErrorBox message={error} />
    {loading ? <p className="loading-inline" role="status">旅の記録を読み込んでいます…</p> : catalog && profile ? <>
      <div className="journal-summary"><div><strong>{profile.visited_prefectures.length}</strong><span>都道府県</span></div><div><strong>{journeys.length}</strong><span>旅の記録</span></div><button onClick={onProfile}>旅のプロフィール<Icon name="arrow" /></button></div>
      {journeys.length > 0 && <div className="journal-journey-filter"><label className="field">振り返る旅<Choice value={journeyId} onChange={(e) => { setJourneyId(e.target.value); setSelected(""); setVisitPage(0); }}><option value="">すべての旅</option>{journeys.map((journey) => <option value={journey.id} key={journey.id}>{journey.title}（{journey.visit_count}件）</option>)}</Choice></label>{currentJourney && <div className="journal-card-actions"><button className="text-button" onClick={() => { setRename(currentJourney); setTitle(currentJourney.title); }}>旅の名前を変更</button><button className="text-button danger" onClick={() => setDeleting(currentJourney)}>旅を削除</button></div>}</div>}
      <JourneyMap prefectures={catalog.prefectures} visits={shownVisits} selected={selected} onSelect={setSelected} />
      {visits.length ? <><div className="journal-visits">{shownVisits.map((visit, index) => <VisitCard key={visit.id} visit={visit} index={index} selected={selected === visit.id} onSelect={() => setSelected(visit.id)} onEdit={() => setEditing(visit)} onDelete={() => setDeleting(visit)} journeyTitle={journeys.find((journey) => journey.id === visit.journey_id)?.title} />)}</div><Pager page={currentPage} count={visits.length} size={8} onChange={setVisitPage} label="訪問記録" /></> : <Empty title="最初の足あとを、地図に。"><p>投稿した写真や、覚えている場所から訪問記録を残せます。</p><button className="button secondary" onClick={() => setEditing("new")}>訪れた場所を残す</button></Empty>}
      <div className="journal-achievements"><h2>旅を重ねたしるし</h2>{profile.badges.map((badge) => <BadgeCard key={badge.id} badge={badge} prefectures={catalog.prefectures} />)}<p className="journal-note">本人が確定した訪問記録で数えます。同じ県は何度訪れても1県。記録の訂正・削除に合わせて実績も変わります。</p><button className="text-button" onClick={onProfile}>実績の見せ方を選ぶ<Icon name="arrow" /></button></div>
      {communities.length > 0 && <section className="journal-people"><button className="button secondary full" aria-expanded={peopleOpen} onClick={() => setPeopleOpen(!peopleOpen)}><Icon name="people" />仲間の旅を見てみる</button>{peopleOpen && <><label className="field">仲間のコミュニティ<Choice value={peopleCommunity} onChange={(e) => setPeopleCommunity(e.target.value)}>{communities.map((community) => <option value={community.id} key={community.id}>{community.name}</option>)}</Choice></label><ErrorBox message={peopleError} />{people === null && !peopleError ? <p role="status">仲間を読み込んでいます…</p> : people?.map((member) => <button key={member.id} className="journal-person" onClick={() => setPerson(member)}><Avatar user={member} small /><span>{member.name}</span><Icon name="arrow" /></button>)}</>}</section>}
    </> : <button className="button secondary" onClick={refresh}>もう一度読み込む</button>}
    {editing && <VisitDialog visit={editing === "new" ? undefined : editing} initialJourney={journeyId} communities={communities} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); refresh(); }} />}
    {person && <TravelProfile person={person} owner={person.id === user.id} onClose={() => { setPerson(null); refresh(); }} />}
    {deleting && <Modal title={"visited_on" in deleting ? "訪問記録を削除しますか？" : "この旅を削除しますか？"} busy={busy} onClose={() => setDeleting(null)}><p>{"visited_on" in deleting ? `${deleting.place_label}の訪問記録を削除します。` : `${deleting.title}と、その旅に残した訪問記録を削除します。`}写真投稿自体は残ります。県別の実績とバッジも再計算されます。</p><ErrorBox message={error} /><div className="dialog-actions"><button className="button secondary" disabled={busy} onClick={() => setDeleting(null)}>残しておく</button><button className="button danger-button" disabled={busy} onClick={() => void remove()}>{busy ? "削除しています…" : "削除する"}</button></div></Modal>}
    {rename && <Modal title="旅の名前を変更" busy={busy} onClose={() => setRename(null)}><label className="field">旅の名前<input value={title} maxLength={100} disabled={busy} onChange={(e) => setTitle(e.target.value)} /></label><ErrorBox message={error} /><button className="button primary full" disabled={busy || !title.trim()} onClick={() => void renameJourney()}>{busy ? "保存しています…" : "名前を保存"}</button></Modal>}
  </section>;
}
