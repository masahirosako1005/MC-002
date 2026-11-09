import { useRef, useState } from 'react';
import { api, errorMessage } from './api';
import type { ActiveAttempt, Answer, Catalog, Game, Leaderboard, Plan } from './types';
import { difficultyName, seasonName, seasons } from './types';
import { Empty, ErrorNotice, Icon, SeasonSeal } from './ui';
import { SaveButton } from './SaveButton';

export function PuzzlePage({
  game,
  attempt,
  catalog,
  plans,
  onSaved,
  onChanged,
  onBack,
  onNext,
}: {
  game: Game;
  attempt: ActiveAttempt;
  catalog: Catalog;
  plans: Plan[];
  onSaved: (plan: Plan) => void;
  onChanged: () => Promise<void>;
  onBack: () => void;
  onNext: () => void;
}) {
  const [values, setValues] = useState(() => attempt.puzzle.labels.map(() => 0));
  const [hint, setHint] = useState('');
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null);
  const [showScores, setShowScores] = useState(false);
  const [scoreError, setScoreError] = useState('');
  const [hintsUsed, setHintsUsed] = useState(attempt.hints_used);
  const lock = useRef(false);
  const nextSeason = seasons[(seasons.indexOf(game.season) + 1) % seasons.length];
  const nextExperience =
    catalog.experiences.find((e) => e.spot_id === game.spot_id && e.season === nextSeason) ??
    catalog.experiences.find((e) => e.spot_id === game.spot_id && e.season !== game.season);
  const change = (index: number, value: number) => {
    setAnswer(null);
    setValues((v) =>
      v.map((old, i) =>
        i === index ? Math.min(attempt.puzzle.max_value, Math.max(0, value)) : old,
      ),
    );
  };
  const getHint = async () => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await api.hint(attempt.id);
      setHint(result.hint);
      setHintsUsed(result.hints_used);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  const submit = async () => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await api.answer(attempt.id, values);
      setAnswer(result);
      if (result.correct) await onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  const loadScores = async () => {
    setShowScores(true);
    setScoreError('');
    try {
      setLeaderboard(await api.leaderboard(game.id));
    } catch (e) {
      setScoreError(errorMessage(e));
    }
  };

  return (
    <article className="puzzle-page">
      <button className="back-button" onClick={onBack}>
        <Icon name="back" />
        場所の案内へ戻る
      </button>
      <div className="puzzle-title">
        <p className="eyebrow">
          {seasonName[game.season]}の章 ／ {difficultyName[game.difficulty]}
        </p>
        <h1>{attempt.puzzle.title}</h1>
        <p>{attempt.puzzle.instruction}</p>
      </div>
      {answer?.correct ? (
        <>
          <section className="completion" aria-live="polite">
            <SeasonSeal season={game.season} earned />
            <p className="eyebrow">水路に、流れが戻った。</p>
            <h2>{answer.achievement?.title ?? '謎を解きました'}</h2>
            <p>{answer.message}</p>
            <div className="result-score">
              <strong>{answer.score}</strong>
              <span>点</span>
            </div>
            <p>{answer.achievement?.description}</p>
            <span className="achievement-confirm">
              <Icon name="check" />
              旅の手帳に実績を記しました
            </span>
          </section>
          {nextExperience && (
            <section className="return-invitation">
              <p className="eyebrow">この水門の、次の物語。</p>
              <h2>
                {seasonName[nextExperience.season]}になったら、
                <br />
                もう一度ここへ。
              </h2>
              <p>
                {nextExperience.title}。{nextExperience.description}
              </p>
              <div className="tag-row">
                <span>{nextExperience.month_label}</span>
                <span>滞在 {nextExperience.duration_minutes}分</span>
              </div>
              <SaveButton
                experience={nextExperience}
                plans={plans}
                onSaved={onSaved}
                reason={`${seasonName[game.season]}の謎を解いた続きを、${seasonName[nextExperience.season]}に楽しむため`}
              />
            </section>
          )}
          <button className="text-button" onClick={onNext}>
            次の旅をひらく <Icon name="arrow" />
          </button>
        </>
      ) : (
        <>
          <section className="clue-card">
            <div>
              <Icon name="book" />
              <h2>水辺の手掛かり</h2>
            </div>
            <p>{attempt.puzzle.clue}</p>
          </section>
          <div className="water-machine" aria-hidden="true">
            <div className="machine-label">
              <span>水路の見取り図</span>
              <span>流れを合わせる</span>
            </div>
            <div className="water-source">
              <span>上流</span>
              <div className="water-source-line" />
            </div>
            <div className="machine-gates">
              {values.map((v, i) => (
                <div className="machine-gate" key={i}>
                  <span className="gate-number">{String(i + 1).padStart(2, '0')}</span>
                  <div className="gate-frame">
                    <div
                      className={`gate-shutter gate-level-${Math.round((v / Math.max(1, attempt.puzzle.max_value)) * 5)}`}
                    />
                    <div className="gate-flow" />
                  </div>
                  <span className="gate-value">{v}</span>
                </div>
              ))}
            </div>
            <div className="water-pool">
              <span>下流</span>
            </div>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void submit();
            }}
            className="puzzle-form"
          >
            <fieldset disabled={busy}>
              <legend>水門を操作する</legend>
              <p className="small-note">つまみを動かすか、＋・−で水量を変えてください。</p>
              {attempt.puzzle.labels.map((label, i) => (
                <div className="gate-control" key={i}>
                  <div className="gate-control-label">
                    <label htmlFor={`gate-${i}`}>
                      <span>{String(i + 1).padStart(2, '0')}</span>
                      {label}
                    </label>
                    <output htmlFor={`gate-${i}`}>
                      {values[i]}
                      <small> / {attempt.puzzle.max_value}</small>
                    </output>
                  </div>
                  <div className="range-row">
                    <button
                      type="button"
                      className="round-button"
                      onClick={() => change(i, values[i] - 1)}
                      disabled={values[i] === 0}
                      aria-label={`${label}を減らす`}
                    >
                      <Icon name="minus" />
                    </button>
                    <input
                      id={`gate-${i}`}
                      type="range"
                      min="0"
                      max={attempt.puzzle.max_value}
                      step="1"
                      value={values[i]}
                      onChange={(e) => change(i, Number(e.target.value))}
                    />
                    <button
                      type="button"
                      className="round-button"
                      onClick={() => change(i, values[i] + 1)}
                      disabled={values[i] === attempt.puzzle.max_value}
                      aria-label={`${label}を増やす`}
                    >
                      <Icon name="plus" />
                    </button>
                  </div>
                </div>
              ))}
            </fieldset>
            {answer && !answer.correct && (
              <div className="answer-feedback" role="status">
                <Icon name="hint" />
                <p>{answer.message}</p>
              </div>
            )}
            <button type="submit" className="button full-width" disabled={busy}>
              {busy ? '確かめています…' : '水の流れを確かめる'}
              <Icon name="arrow" />
            </button>
            <div className="puzzle-utilities">
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  setValues(values.map(() => 0));
                  setAnswer(null);
                }}
                disabled={busy}
              >
                操作前に戻す
              </button>
              <button
                type="button"
                className="text-button"
                disabled={busy}
                onClick={() => void getHint()}
              >
                <Icon name="hint" />
                {hint ? 'ヒントをもう一度読む' : 'ヒントを読む'}
              </button>
            </div>
          </form>
          {hint && (
            <aside className="hint-card" role="status">
              <p className="eyebrow">考える手掛かり</p>
              <p>{hint}</p>
            </aside>
          )}
          <p className="small-note">
            {hintsUsed
              ? 'ヒントを使った挑戦として記録します。'
              : 'ヒントを読むと、ヒント利用として得点に反映されます。'}
          </p>
        </>
      )}
      {error && <ErrorNotice message={error} />}
      <section className="score-section">
        <button
          className="text-button"
          aria-expanded={showScores}
          onClick={() => (showScores ? setShowScores(false) : void loadScores())}
        >
          <Icon name="trophy" />
          同じ謎に挑んだ人の記録
          <Icon name={showScores ? 'minus' : 'plus'} />
        </button>
        {showScores && (
          <div className="score-panel">
            <p className="small-note">同じ季節・難易度・問題の記録です。</p>
            {scoreError ? (
              <ErrorNotice message={scoreError} retry={() => void loadScores()} />
            ) : !leaderboard ? (
              <p role="status">記録を開いています…</p>
            ) : leaderboard.entries.length ? (
              <ol className="score-list">
                {leaderboard.entries.map((entry, i) => (
                  <li key={i}>
                    <span>{entry.rank}</span>
                    <span>{entry.nickname}</span>
                    <strong>
                      {entry.score}
                      <small>点</small>
                    </strong>
                  </li>
                ))}
              </ol>
            ) : (
              <Empty title="最初の記録を残そう">この謎を解いた人の得点が、ここに並びます。</Empty>
            )}
          </div>
        )}
      </section>
    </article>
  );
}
