import { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorMessage, sessionInvalidEvent } from './api';
import type {
  ActiveAttempt,
  Catalog,
  Collection,
  CollectionAction,
  Difficulty,
  Game,
  Journal,
  Plan,
  Season,
  Spot,
  Trophy,
} from './types';
import { emptyJournal, seasonName } from './types';
import { ErrorNotice, Icon, SeasonSeal } from './ui';
import { Guide, SpotPage } from './Guide';
import { JournalPage } from './Journal';
import { NextTrip } from './NextTrip';
import { PuzzlePage } from './Puzzle';
import { Recovery } from './Recovery';
import { TrophyArt } from './TrophyArt';

type Tab = 'guide' | 'journal' | 'next';
const tabNames: Record<Tab, string> = { guide: '旅のしおり', journal: '旅の手帳', next: '次の旅' };

export default function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [journal, setJournal] = useState<Journal>(emptyJournal);
  const [tab, setTab] = useState<Tab>('guide');
  const [spot, setSpot] = useState<Spot | null>(null);
  const [play, setPlay] = useState<{ game: Game; attempt: ActiveAttempt } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [largeText, setLargeText] = useState(false);
  const [notice, setNotice] = useState('');
  const [collection, setCollection] = useState<Collection | null>(null);
  const [collectionError, setCollectionError] = useState('');
  const [collectionLoading, setCollectionLoading] = useState(false);
  const [newTrophies, setNewTrophies] = useState<Trophy[]>([]);
  const [spotChoice, setSpotChoice] = useState<{ season?: Season; difficulty?: Difficulty }>({});
  const collectionRef = useRef<Collection | null>(null);
  const collectionRequest = useRef(0);
  const loadCollection = useCallback(async (announce = false) => {
    const request = ++collectionRequest.current;
    setCollectionLoading(true);
    setCollectionError('');
    try {
      const data = await api.collection();
      if (request !== collectionRequest.current) return;
      const old = collectionRef.current;
      if (announce && old) {
        const gained = data.trophies.filter((t) =>
          t.stages.some(
            (s) =>
              s.completed &&
              !old.trophies.find((o) => o.id === t.id)?.stages.find((o) => o.id === s.id)
                ?.completed,
          ),
        );
        setNewTrophies(gained);
      }
      collectionRef.current = data;
      setCollection(data);
    } catch (e) {
      if (request === collectionRequest.current) setCollectionError(errorMessage(e));
    } finally {
      if (request === collectionRequest.current) setCollectionLoading(false);
    }
  }, []);
  const heading = useRef<HTMLElement>(null);
  const boot = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [data] = await Promise.all([api.catalog(), api.session()]);
      const records = await api.journal();
      setCatalog(data);
      setJournal(records);
      await loadCollection();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [loadCollection]);
  useEffect(() => {
    void boot();
  }, [boot]);
  useEffect(() => {
    const invalidated = () => {
      setPlay(null);
      setSpot(null);
      setJournal(emptyJournal);
      collectionRequest.current++;
      collectionRef.current = null;
      setCollection(null);
      setNewTrophies([]);
      setNotice('');
      setError(
        '手帳の接続が変わりました。もう一度読み込んでください。以前の記録は「引き継ぎ」から開けます。',
      );
    };
    window.addEventListener(sessionInvalidEvent, invalidated);
    return () => window.removeEventListener(sessionInvalidEvent, invalidated);
  }, []);
  useEffect(() => {
    document.title = `${play ? '水門の謎' : (spot?.name ?? tabNames[tab])} · tang you chi`;
    heading.current?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [tab, spot, play]);
  const refresh = async () => {
    setJournal(await api.journal());
    await loadCollection(true);
  };
  const navigate = (value: Tab) => {
    setTab(value);
    setSpot(null);
    setPlay(null);
    setNotice('');
  };
  const openSpot = (value: Spot) => {
    setSpotChoice({});
    setTab('guide');
    setSpot(value);
    setPlay(null);
    setNotice('');
  };
  const openCollectionAction = (action: CollectionAction) => {
    const destination = catalog?.spots.find((s) => s.id === action.spot_id);
    if (!destination) return;
    openSpot(destination);
    setSpotChoice({
      season: action.season ?? undefined,
      difficulty: action.difficulty ?? undefined,
    });
  };
  const changeTarget = (targetId: string | null) => {
    if (!collectionRef.current) return;
    const updated = { ...collectionRef.current, target_id: targetId };
    collectionRef.current = updated;
    setCollection(updated);
  };
  const addPlan = (plan: Plan) => {
    setJournal((j) => ({ ...j, plans: [plan, ...j.plans.filter((p) => p.id !== plan.id)] }));
    setNotice(`「${plan.title}」を次の旅に保存しました。`);
  };
  const recovered = async () => {
    setJournal(emptyJournal);
    setTab('journal');
    setSpot(null);
    setPlay(null);
    setNotice('');
    collectionRequest.current++;
    collectionRef.current = null;
    setCollection(null);
    setNewTrophies([]);
    await boot();
  };

  return (
    <div className={`app ${largeText ? 'large-text' : ''}`}>
      <a className="skip-link" href="#main-content">
        本文へ移動
      </a>
      <aside className="desktop-intro" aria-hidden="true">
        <div className="desktop-mark">
          <Icon name="gate" />
          <span>tang you chi</span>
        </div>
        <p className="vertical-note">街をめぐる。季節をつなぐ。</p>
        <div className="desktop-intro-bottom">
          <span>平城京市　四季の旅</span>
          <div className="four-seals">
            {(['spring', 'summer', 'autumn', 'winter'] as const).map((s) => (
              <SeasonSeal key={s} season={s} />
            ))}
          </div>
          <p>
            今日の発見が、
            <br />
            次の旅のしおりになる。
          </p>
        </div>
      </aside>
      <div className="app-paper">
        <header className="topbar">
          <button
            className="brand"
            onClick={() => navigate('guide')}
            aria-label="tang you chi 旅のしおりへ"
          >
            <span className="brand-symbol">
              <Icon name="gate" />
            </span>
            <span>
              tang you chi<small>四季の旅を、手帳に。</small>
            </span>
          </button>
          <div className="header-actions">
            <Recovery onRecovered={recovered} />
            <button
              className="type-toggle"
              aria-pressed={largeText}
              onClick={() => setLargeText((v) => !v)}
            >
              <span aria-hidden="true">
                あ<span>あ</span>
              </span>
              <small>文字サイズ</small>
            </button>
          </div>
        </header>
        <main id="main-content" tabIndex={-1} ref={heading}>
          {loading ? (
            <div className="loading-state" role="status">
              <div className="loading-seal">
                <Icon name="book" />
              </div>
              <p>旅の手帳を開いています</p>
              <span>しばらくお待ちください</span>
            </div>
          ) : error ? (
            <div className="page-padding">
              <h1>手帳を開けませんでした</h1>
              <ErrorNotice message={error} retry={() => void boot()} />
            </div>
          ) : (
            catalog && (
              <>
                {newTrophies.length > 0 && (
                  <aside className="trophy-arrival" aria-label="新しく集めた記念品">
                    <TrophyArt motif={newTrophies[0].motif} earned />
                    <div>
                      <p className="eyebrow" role="status">
                        旅の収集棚に、記念品が増えました
                      </p>
                      <strong>
                        {newTrophies[0].title}
                        {newTrophies.length > 1 ? ` ほか${newTrophies.length - 1}点` : ''}
                      </strong>
                      <button
                        className="text-button"
                        onClick={() => {
                          setNewTrophies([]);
                          navigate('journal');
                        }}
                      >
                        収集棚で見る <Icon name="arrow" />
                      </button>
                    </div>
                    <button
                      className="round-button"
                      aria-label="記念品のお知らせを閉じる"
                      onClick={() => setNewTrophies([])}
                    >
                      <Icon name="close" />
                    </button>
                  </aside>
                )}
                {play ? (
                  <PuzzlePage
                    game={play.game}
                    attempt={play.attempt}
                    catalog={catalog}
                    plans={journal.plans}
                    onSaved={addPlan}
                    onChanged={refresh}
                    onBack={() => setPlay(null)}
                    onNext={() => navigate('next')}
                  />
                ) : spot ? (
                  <SpotPage
                    key={spot.id}
                    initialSeason={spotChoice.season}
                    initialDifficulty={spotChoice.difficulty}
                    spot={spot}
                    catalog={catalog}
                    journal={journal}
                    onChanged={refresh}
                    onBack={() => setSpot(null)}
                    onPlay={(game, attempt) => setPlay({ game, attempt })}
                    onSaved={addPlan}
                  />
                ) : tab === 'guide' ? (
                  <Guide
                    catalog={catalog}
                    journal={journal}
                    onSpot={openSpot}
                    onNext={() => navigate('next')}
                  />
                ) : tab === 'journal' ? (
                  <JournalPage
                    catalog={catalog}
                    journal={journal}
                    onSpot={openSpot}
                    onNext={() => navigate('next')}
                    collection={collection}
                    collectionError={collectionError}
                    collectionLoading={collectionLoading}
                    onCollectionRetry={() => void loadCollection()}
                    onTargetChanged={changeTarget}
                    onAction={openCollectionAction}
                    onSaved={addPlan}
                  />
                ) : (
                  <NextTrip
                    catalog={catalog}
                    plans={journal.plans}
                    onSaved={addPlan}
                    onRemoved={(id) => {
                      setJournal((j) => ({ ...j, plans: j.plans.filter((p) => p.id !== id) }));
                      setNotice('次の旅から外しました。');
                    }}
                    onSpot={openSpot}
                  />
                )}
              </>
            )
          )}
        </main>
        <div className="announcer" role="status" aria-live="polite">
          {notice && (
            <span>
              <Icon name="check" />
              {notice}
            </span>
          )}
        </div>
        <footer className="page-footer">
          <span>{catalog?.city ?? '平城京市'}</span>
          <span>{catalog ? `${seasonName[catalog.season]}のしおり` : '四季のしおり'}</span>
          <span>tang you chi</span>
        </footer>
        <nav className="bottom-nav" aria-label="主なメニュー">
          {(['guide', 'journal', 'next'] as Tab[]).map((value, i) => (
            <button
              key={value}
              aria-current={tab === value ? 'page' : undefined}
              onClick={() => navigate(value)}
            >
              <Icon name={(['compass', 'book', 'bookmark'] as const)[i]} />
              <span>{tabNames[value]}</span>
              {value === 'next' && journal.plans.length > 0 && (
                <span className="nav-count" aria-label={`${journal.plans.length}件保存`}>
                  {journal.plans.length}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
}
