import { useEffect, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { api, errorMessage } from './api';
import type { Catalog, Collection, CollectionAction, Plan, Trophy } from './types';
import { dateLabel, seasonName } from './types';
import { ErrorNotice, Icon } from './ui';
import { TrophyArt } from './TrophyArt';
import { SaveButton } from './SaveButton';

function Progress({ trophy }: { trophy: Trophy }) {
  const { current, target, unit } = trophy.progress;
  return (
    <div className="trophy-progress">
      <div>
        <span>{trophy.completed ? 'すべての段階を達成' : '次の段階まで'}</span>
        <strong>
          {current} / {target}
          <small>{unit}</small>
        </strong>
      </div>
      <progress value={current} max={Math.max(1, target)} aria-label={`${trophy.title}の進捗`} />
    </div>
  );
}
const stateLabel = (t: Trophy) =>
  t.completed
    ? '完成'
    : t.status === 'earned'
      ? '獲得・続きあり'
      : t.status === 'progress'
        ? '集めている途中'
        : 'これから';
function actionTime(action: CollectionAction | null) {
  if (!action) return 'この記念品の条件を、すべて達成しました。';
  if (action.available_from) {
    const [y, m, d] = action.available_from.split('-');
    return `${y}年${Number(m)}月${Number(d)}日以降の訪問で進められます。`;
  }
  return action.kind === 'season' && action.season
    ? `${seasonName[action.season]}の水門で、続きを集めます。`
    : '現地の訪問と体験から、続きを集めます。';
}

export function CollectionShelf({
  data,
  error,
  loading,
  catalog,
  plans,
  onRetry,
  onTargetChanged,
  onAction,
  onSaved,
}: {
  data: Collection | null;
  error: string;
  loading: boolean;
  catalog: Catalog;
  plans: Plan[];
  onRetry: () => void;
  onTargetChanged: (id: string | null) => void;
  onAction: (action: CollectionAction) => void;
  onSaved: (plan: Plan) => void;
}) {
  const [detailId, setDetailId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [targetError, setTargetError] = useState('');
  const [message, setMessage] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const lock = useRef(false);
  const pendingTarget = useRef<string | null>(null);
  const detail = data?.trophies.find((t) => t.id === detailId);
  useEffect(() => {
    if (detailId) dialog.current?.showModal();
    else dialog.current?.close();
  }, [detailId]);
  const open = (t: Trophy, event: MouseEvent<HTMLButtonElement>) => {
    opener.current = event.currentTarget;
    setMessage('');
    setTargetError('');
    setDetailId(t.id);
  };
  const close = () => {
    if (lock.current) return;
    dialog.current?.close();
    setDetailId(null);
    setTargetError('');
    setMessage('');
    opener.current?.focus();
  };
  const choose = async (id: string | null) => {
    if (lock.current) return;
    lock.current = true;
    pendingTarget.current = id;
    setBusy(true);
    setTargetError('');
    setMessage('');
    try {
      const result = await api.target(id);
      onTargetChanged(result.target_id);
      setMessage(
        id ? 'この記念品を、収集棚のいちばん上に置きました。' : '次に狙う記念品を外しました。',
      );
    } catch (e) {
      setTargetError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  if (!data)
    return (
      <section className="collection-loading" aria-label="旅の収集棚">
        <h2>旅の収集棚</h2>
        {error ? (
          <ErrorNotice message={error} retry={onRetry} />
        ) : (
          <p role="status">収集棚を開いています…</p>
        )}
      </section>
    );
  const starter = ['place-watergate', `season-${catalog.season}`].flatMap(
    (id) => data.trophies.find((t) => t.id === id) ?? [],
  );
  const starterEarned = starter.filter((t) => t.status === 'earned').length;
  const featured =
    data.trophies.find((t) => t.id === data.target_id) ??
    starter.find((t) => !t.completed) ??
    data.trophies.find((t) => t.id === 'return-path' && !t.completed) ??
    data.trophies.find((t) => t.id === 'watergate-mastery' && !t.completed) ??
    data.trophies.find((t) => !t.completed) ??
    data.trophies[0];
  const almost = data.trophies
    .filter((t) => !t.completed && t.progress.current > 0)
    .sort((a, b) => b.progress.current / b.progress.target - a.progress.current / a.progress.target)
    .slice(0, 2);
  const detailAction = detail?.next_action;
  const detailSpot = catalog.spots.find((s) => s.id === detailAction?.spot_id);
  const saveExperience =
    detailAction &&
    catalog.experiences.find(
      (e) =>
        e.spot_id === detailAction.spot_id && e.season === (detailAction.season ?? catalog.season),
    );
  return (
    <section className="collection-shelf" aria-labelledby="shelf-title" aria-busy={loading}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">訪れた日が、かたちになる。</p>
          <h2 id="shelf-title">旅の収集棚</h2>
        </div>
        <span className="shelf-count">
          <strong>{data.summary.earned}</strong> / {data.summary.total}
          <small>獲得した記念品</small>
        </span>
      </div>
      {error && <ErrorNotice message={error} retry={onRetry} />}
      {featured && (
        <article className={`trophy-feature ${featured.status === 'earned' ? 'has-keepsake' : ''}`}>
          <button
            className="feature-object"
            onClick={(e) => open(featured, e)}
            aria-label={`${featured.title}の記念品をひらく`}
          >
            <TrophyArt motif={featured.motif} earned={featured.status === 'earned'} />
            <span>
              記念品をひらく <Icon name="plus" />
            </span>
          </button>
          <div className="feature-copy">
            <p className="eyebrow">
              {data.target_id
                ? featured.completed
                  ? '棚に飾る一品'
                  : '次に狙う一品'
                : starterEarned === 2
                  ? '次に集める一品'
                  : 'まずは、この一品から'}
            </p>
            <h3>{featured.title}</h3>
            <p>{featured.description}</p>
            <Progress trophy={featured} />
            <button className="text-button" onClick={(e) => open(featured, e)}>
              条件と次の行動を見る <Icon name="arrow" />
            </button>
          </div>
        </article>
      )}
      <section
        className={`starter-pair ${starterEarned === 2 ? 'pair-complete' : ''}`}
        aria-labelledby="starter-title"
      >
        <div>
          <p className="eyebrow">{seasonName[catalog.season]}の水門で、最初の2点</p>
          <h3 id="starter-title">最初のひと組</h3>
          <p>
            {starterEarned === 2
              ? '訪問と謎のひと組がそろいました。次は別の日、別の解き方へ。'
              : '訪問を記し、水門の謎をひとつ解く。まずはここから。'}
          </p>
        </div>
        <div className="starter-items">
          {starter.map((t) => (
            <button key={t.id} onClick={(e) => open(t, e)} aria-label={`${t.title}の条件をひらく`}>
              <TrophyArt motif={t.motif} earned={t.status === 'earned'} />
              <span>{t.title}</span>
              <small>{t.status === 'earned' ? '集めました' : 'これから'}</small>
            </button>
          ))}
        </div>
        <p className="starter-result">
          <Icon name={starterEarned === 2 ? 'check' : 'bookmark'} />
          {starterEarned} / 2 点
          {starterEarned === 2 ? ' — ひと組がそろいました' : ' — 水門の訪問と謎'}
        </p>
      </section>
      {almost.length > 0 && (
        <section className="almost-section" aria-labelledby="almost-title">
          <div className="section-heading">
            <h3 id="almost-title">あと一歩の記念品</h3>
            <span className="eyebrow">次の条件を選ぶ</span>
          </div>
          <div className="almost-list">
            {almost.map((t) => (
              <button key={t.id} className="almost-card" onClick={(e) => open(t, e)}>
                <TrophyArt motif={t.motif} earned={t.status === 'earned'} />
                <span>
                  <strong>{t.title}</strong>
                  <small>{t.missing_conditions[0] ?? '次の段階を確認する'}</small>
                  <small className="action-timing">{actionTime(t.next_action)}</small>
                </span>
                <Icon name="arrow" />
              </button>
            ))}
          </div>
        </section>
      )}
      <div className="keepsake-shelves">
        {data.sets.map((set) => (
          <section className={`keepsake-set set-${set.id}`} key={set.id} aria-label={set.title}>
            <div className="set-heading">
              <div>
                <span className="eyebrow">
                  {set.completed ? '称号を集めました' : '最後まで集めると'}
                </span>
                <h3>{set.title}</h3>
                <p>{set.reward_label}</p>
              </div>
              <span className="set-progress">
                {set.earned} / {set.total}
                <small>最後まで集めた記念品</small>
              </span>
            </div>
            <div className="keepsake-row">
              {data.trophies
                .filter((t) => t.set_id === set.id)
                .map((t) => (
                  <button
                    key={t.id}
                    className={`keepsake-slot ${t.status === 'earned' ? 'earned' : ''} ${data.target_id === t.id ? 'targeted' : ''}`}
                    onClick={(e) => open(t, e)}
                    aria-label={`${t.title}、${stateLabel(t)}、詳細をひらく`}
                  >
                    <TrophyArt motif={t.motif} earned={t.status === 'earned'} />
                    <strong>{t.title}</strong>
                    <span>{data.target_id === t.id ? '選んだ一品' : stateLabel(t)}</span>
                  </button>
                ))}
            </div>
            {set.completed && (
              <p className="set-completed">
                <Icon name="check" />「{set.reward_label}」
                {set.earned_at && <time dateTime={set.earned_at}>{dateLabel(set.earned_at)}</time>}
              </p>
            )}
          </section>
        ))}
      </div>
      <p className="shelf-note">
        記念品は、訪問や謎を達成した記録から集まります。次の旅への保存だけでは増えません。
      </p>
      <dialog
        ref={dialog}
        className="trophy-dialog"
        aria-labelledby="trophy-detail-title"
        onCancel={(e) => {
          e.preventDefault();
          close();
        }}
        onClose={() => setDetailId(null)}
      >
        {detail && (
          <>
            <div className="dialog-heading">
              <span className="eyebrow">{stateLabel(detail)}</span>
              <button
                className="round-button"
                onClick={close}
                disabled={busy}
                aria-label="記念品の詳細を閉じる"
              >
                <Icon name="close" />
              </button>
            </div>
            <div className="trophy-detail-art">
              <TrophyArt motif={detail.motif} earned={detail.status === 'earned'} />
            </div>
            <h2 id="trophy-detail-title">{detail.title}</h2>
            <p className="trophy-description">{detail.description}</p>
            {detail.earned_at && (
              <p className="keepsake-date">
                <Icon name="check" />
                最初に集めた日{' '}
                <time dateTime={detail.earned_at}>{dateLabel(detail.earned_at)}</time>
              </p>
            )}
            <Progress trophy={detail} />
            <ol className="trophy-stages">
              {detail.stages.map((s, i) => (
                <li key={s.id} className={s.completed ? 'stage-complete' : ''}>
                  <span className="stage-mark">{s.completed ? <Icon name="check" /> : i + 1}</span>
                  <div>
                    <strong>{s.title}</strong>
                    <span>
                      {s.current} / {s.target} {detail.progress.unit}
                    </span>
                    {s.earned_at && (
                      <time dateTime={s.earned_at}>{dateLabel(s.earned_at)} に達成</time>
                    )}
                  </div>
                </li>
              ))}
            </ol>
            {detail.missing_conditions.length > 0 && (
              <div className="missing-conditions">
                <h3>次に集める条件</h3>
                <ul>
                  {detail.missing_conditions.map((condition, i) => (
                    <li key={i}>{condition}</li>
                  ))}
                </ul>
              </div>
            )}
            {detailAction && (
              <section className="trophy-next-action">
                <p className="eyebrow">次は、現地で。</p>
                <h3>{detailAction.label}</h3>
                <p>{actionTime(detailAction)}</p>
                {detailSpot && (
                  <button
                    className="button"
                    onClick={() => {
                      close();
                      onAction(detailAction);
                    }}
                  >
                    {detailSpot.name}の案内をひらく <Icon name="arrow" />
                  </button>
                )}
                {saveExperience && (
                  <SaveButton
                    experience={saveExperience}
                    plans={plans}
                    onSaved={onSaved}
                    reason={`${detail.title}の続きを集めるため`}
                  />
                )}
              </section>
            )}
            <div className="target-choice">
              <button
                className="button secondary full-width"
                disabled={busy}
                onClick={() => void choose(data.target_id === detail.id ? null : detail.id)}
              >
                <Icon name={data.target_id === detail.id ? 'check' : 'bookmark'} />
                {busy
                  ? '手帳に記しています…'
                  : data.target_id === detail.id
                    ? '選んだ一品から外す'
                    : detail.completed
                      ? 'この記念品を棚に飾る'
                      : '次に狙う一品にする'}
              </button>
              {targetError && (
                <ErrorNotice
                  message={targetError}
                  retry={() => void choose(pendingTarget.current)}
                />
              )}
              {message && (
                <p className="success-message" role="status">
                  {message}
                </p>
              )}
            </div>
          </>
        )}
      </dialog>
    </section>
  );
}
