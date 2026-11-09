import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, errorMessage } from './api';
import type {
  ActiveAttempt,
  Catalog,
  Difficulty,
  Game,
  Journal,
  Plan,
  Season,
  Spot,
} from './types';
import { difficultyName, seasonName, seasons } from './types';
import { CityMap, Empty, ErrorNotice, Icon, Scene, SeasonSeal } from './ui';
import { SaveButton } from './SaveButton';

export function Guide({
  catalog,
  journal,
  onSpot,
  onNext,
}: {
  catalog: Catalog;
  journal: Journal;
  onSpot: (spot: Spot) => void;
  onNext: () => void;
}) {
  const gate = catalog.spots.find((s) => s.kind === 'gate');
  return (
    <div className="guide-page">
      <div className="page-meta">
        <span>
          {catalog.city} ／ {seasonName[catalog.season]}のしおり
        </span>
        <span>四季をめぐる旅</span>
      </div>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="red-dot" />
            {seasonName[catalog.season]}の章、ひらく。
          </p>
          <h1>
            ひとつの街を、
            <br />
            何度でも。
          </h1>
          <p className="hero-description">
            水門の謎を解く。海辺の季節を知る。
            <br />
            今日の発見を、次の旅につなげよう。
          </p>
          {gate && (
            <button className="button" onClick={() => onSpot(gate)}>
              四季の謎をひらく <Icon name="arrow" />
            </button>
          )}
        </div>
        <div className="hero-picture">
          <Scene season={catalog.season} priority />
          <div className="hero-seal">
            <SeasonSeal season={catalog.season} earned />
            <span>{seasonName[catalog.season]}の水門</span>
          </div>
          <span className="picture-caption">水の流れを、あなたの手で。</span>
        </div>
      </section>
      <div className="guide-summary">
        <div>
          <Icon name="book" />
          <span>あなたの旅の手帳</span>
        </div>
        <p>
          <strong>{journal.visits.length}</strong> 訪問<span>／</span>
          <strong>{journal.achievements.length}</strong> 実績
        </p>
      </div>
      <section className="section-spots">
        <div className="section-heading">
          <div>
            <p className="eyebrow">街を歩く</p>
            <h2>今日の寄り道</h2>
          </div>
          <span className="section-number">01 — 04</span>
        </div>
        <div className="spot-grid">
          {catalog.spots.map((spot, i) => (
            <button
              className={`spot-card spot-${spot.kind}`}
              key={spot.id}
              onClick={() => onSpot(spot)}
            >
              <div className="spot-art">
                <Scene
                  kind={spot.kind}
                  season={catalog.season}
                  sizes="(max-width: 760px) 45vw, 320px"
                />
                <span className="spot-index">0{i + 1}</span>
              </div>
              <div className="spot-copy">
                <span className="eyebrow">{spot.area}</span>
                <h3>
                  {spot.name}
                  <Icon name="arrow" />
                </h3>
                <p>{spot.description}</p>
                <span className="spot-meta">
                  <Icon name="clock" />
                  滞在 {spot.dwell_minutes}分
                </span>
              </div>
            </button>
          ))}
        </div>
      </section>
      <section className="next-teaser">
        <span className="small-seal">
          <Icon name="bookmark" />
        </span>
        <div>
          <p className="eyebrow">今度は、どの季節に。</p>
          <h2>まだ知らない、この街へ。</h2>
          <p>使える時間と関心から、次に会いたい風景を選ぶ。</p>
        </div>
        <button className="round-button" onClick={onNext} aria-label="次の旅を探す">
          <Icon name="arrow" />
        </button>
      </section>
      <details className="map-details">
        <summary>
          街の見取り図をひらく <Icon name="plus" />
        </summary>
        <CityMap />
        <p>場所のつながりを知るための見取り図です。移動時間は各体験の案内で確認できます。</p>
      </details>
    </div>
  );
}

export function SpotPage({
  spot,
  catalog,
  journal,
  onBack,
  onPlay,
  onChanged,
  onSaved,
  initialSeason,
  initialDifficulty = 'beginner',
}: {
  spot: Spot;
  catalog: Catalog;
  journal: Journal;
  onBack: () => void;
  onPlay: (game: Game, attempt: ActiveAttempt) => void;
  onChanged: () => Promise<void>;
  onSaved: (plan: Plan) => void;
  initialSeason?: Season;
  initialDifficulty?: Difficulty;
}) {
  const [code, setCode] = useState('');
  const [season, setSeason] = useState<Season>(initialSeason ?? catalog.season);
  const [difficulty, setDifficulty] = useState<Difficulty>(initialDifficulty);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [visitMessage, setVisitMessage] = useState('');
  const lock = useRef(false);
  const games = catalog.games.filter((g) => g.spot_id === spot.id);
  const game = games.find((g) => g.season === season && g.difficulty === difficulty);
  const seasonalExperience = catalog.experiences.find(
    (e) => e.spot_id === spot.id && e.season === season,
  );
  const experiences = catalog.experiences.filter((e) => e.spot_id === spot.id);
  const visit = async (event: FormEvent) => {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      await api.visit(spot.id, code.trim());
      setVisitMessage('今日の訪問を手帳に記しました。');
      setCode('');
      await onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  const start = async () => {
    if (!game || lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      const attempt = await api.start(game.id);
      onPlay(game, attempt);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  return (
    <article className="detail-page">
      <button className="back-button" onClick={onBack}>
        <Icon name="back" />
        旅のしおりへ戻る
      </button>
      <div className="detail-title">
        <p className="eyebrow">{spot.area}</p>
        <h1>{spot.name}</h1>
        <div className="tag-row">
          <span>
            <Icon name={spot.kind} />
            {spot.kind === 'gate'
              ? '四季の謎'
              : spot.kind === 'shrine'
                ? '節目をたどる'
                : spot.kind === 'coast'
                  ? '季節を楽しむ'
                  : '会議の合間に'}
          </span>
          <span>
            <Icon name="clock" />
            滞在 {spot.dwell_minutes}分
          </span>
        </div>
      </div>
      <div className="detail-art">
        <Scene kind={spot.kind} season={season} priority />
      </div>
      <p className="detail-description">{spot.description}</p>
      <section className="visit-section" aria-labelledby="visit-heading">
        <div className="numbered-heading">
          <span>01</span>
          <div>
            <p className="eyebrow">現地に着いたら</p>
            <h2 id="visit-heading">訪問を手帳に記す</h2>
          </div>
        </div>
        <p>現地のしおりにある訪問コードを入力してください。</p>
        <form onSubmit={(e) => void visit(e)} className="code-form">
          <label htmlFor="visit-code">訪問コード</label>
          <div>
            <input
              id="visit-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              maxLength={80}
              required
              placeholder="しおりのコード"
            />
            <button className="button" disabled={busy || !code.trim()} type="submit">
              {busy ? '確認中…' : '記す'}
              <Icon name="check" />
            </button>
          </div>
        </form>
        {visitMessage && (
          <p className="success-message" role="status">
            <Icon name="check" />
            {visitMessage}
          </p>
        )}
      </section>
      {error && <ErrorNotice message={error} />}
      {games.length > 0 && (
        <section className="game-select" aria-labelledby="game-heading">
          <div className="numbered-heading">
            <span>02</span>
            <div>
              <p className="eyebrow">水辺に残された手掛かり</p>
              <h2 id="game-heading">季節の謎を選ぶ</h2>
            </div>
          </div>
          <fieldset>
            <legend>季節</legend>
            <div className="season-picker">
              {seasons.map((s) => (
                <button
                  type="button"
                  key={s}
                  aria-pressed={season === s}
                  onClick={() => setSeason(s)}
                >
                  <SeasonSeal season={s} />
                  <span>{seasonName[s]}</span>
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>難易度</legend>
            <div className="segmented">
              {(['beginner', 'advanced'] as const).map((d) => (
                <button
                  type="button"
                  key={d}
                  aria-pressed={difficulty === d}
                  onClick={() => setDifficulty(d)}
                >
                  {difficultyName[d]}
                </button>
              ))}
            </div>
          </fieldset>
          {game ? (
            <div className="game-intro">
              <p className="eyebrow">
                {seasonName[game.season]} ／ {difficultyName[game.difficulty]}
              </p>
              <h3>{game.title}</h3>
              <p>{game.description}</p>
              {season === catalog.season ? (
                <>
                  <p className="small-note">
                    今日の訪問を記してから始められます。途中の挑戦は続きから開きます。
                  </p>
                  <button
                    className="button full-width"
                    disabled={busy}
                    onClick={() => void start()}
                  >
                    {busy ? 'ひらいています…' : '水門の謎に挑む'}
                    <Icon name="arrow" />
                  </button>
                </>
              ) : (
                <>
                  <p className="season-availability">
                    <Icon name="bookmark" />
                    {seasonName[season]}になったら、現地で挑戦できます。
                  </p>
                  <button className="button full-width" disabled>
                    この季節になったら挑戦できます
                  </button>
                  {seasonalExperience && (
                    <div className="season-save">
                      <SaveButton
                        experience={seasonalExperience}
                        plans={journal.plans}
                        onSaved={onSaved}
                        reason={`${seasonName[season]}の水門の謎に挑むため`}
                      />
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <Empty title="この季節の謎は準備中です">別の季節や難易度を選んでください。</Empty>
          )}
        </section>
      )}
      <section className="season-experiences">
        <div className="section-heading">
          <div>
            <p className="eyebrow">この場所の、また来たい理由</p>
            <h2>{spot.kind === 'shrine' ? '節目に、ふたたび。' : '季節の先にある体験'}</h2>
          </div>
        </div>
        {experiences.length ? (
          <div className="experience-list">
            {experiences.map((exp) => (
              <article className="experience-row" key={exp.id}>
                <div className={`season-tag season-${exp.season}`}>{seasonName[exp.season]}</div>
                <div>
                  <p className="eyebrow">{exp.month_label}</p>
                  <h3>{exp.title}</h3>
                  <p>{exp.description}</p>
                  <SaveButton
                    experience={exp}
                    plans={journal.plans}
                    onSaved={onSaved}
                    reason={`${spot.name}で、${exp.month_label}の体験を楽しむため`}
                    compact
                  />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty title="次の体験を探す">旅のしおりから、気になる場所をひらいてみましょう。</Empty>
        )}
      </section>
    </article>
  );
}
