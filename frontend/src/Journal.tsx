import type { Catalog, Collection, CollectionAction, Journal, Plan, Spot } from './types';
import { dateLabel, seasonName, seasons } from './types';
import { Empty, Icon, SeasonSeal } from './ui';
import { CollectionShelf } from './CollectionShelf';

export function JournalPage({
  catalog,
  journal,
  onSpot,
  onNext,
  collection,
  collectionError,
  collectionLoading,
  onCollectionRetry,
  onTargetChanged,
  onAction,
  onSaved,
}: {
  catalog: Catalog;
  journal: Journal;
  onSpot: (spot: Spot) => void;
  onNext: () => void;
  collection: Collection | null;
  collectionError: string;
  collectionLoading: boolean;
  onCollectionRetry: () => void;
  onTargetChanged: (id: string | null) => void;
  onAction: (action: CollectionAction) => void;
  onSaved: (plan: Plan) => void;
}) {
  const timeline = [
    ...journal.visits.map((v) => ({
      id: `visit-${v.id}`,
      type: '訪問',
      title: v.spot_name,
      time: v.visited_at,
      description: '現地の訪問を記しました。',
      icon: 'compass' as const,
    })),
    ...journal.achievements.map((a) => ({
      id: `achievement-${a.id}`,
      type: '実績',
      title: a.title,
      time: a.earned_at,
      description: a.description,
      icon: 'trophy' as const,
    })),
  ].sort((a, b) => b.time.localeCompare(a.time));
  const unfinished = journal.attempts.filter((a) => !a.completed_at);
  // A recorded season belongs to the attempt, even after its game leaves the current catalog.
  const puzzleSeasons = new Set(
    journal.attempts.filter((a) => a.completed_at).map((a) => a.season),
  );
  return (
    <div className="journal-page page-padding">
      <div className="page-title">
        <p className="eyebrow">歩いた日々を、ひとつずつ。</p>
        <h1>旅の手帳</h1>
        <p>
          訪れた場所と、解いた謎。
          <br />
          この街で集めた記録を振り返る。
        </p>
      </div>
      <CollectionShelf
        data={collection}
        error={collectionError}
        loading={collectionLoading}
        catalog={catalog}
        plans={journal.plans}
        onRetry={onCollectionRetry}
        onTargetChanged={onTargetChanged}
        onAction={onAction}
        onSaved={onSaved}
      />
      <section className="journal-cover journal-record-summary">
        <span className="cover-corner">四季の記録</span>
        <Icon name="book" />
        <h2>
          {catalog.city}
          <br />
          わたしの旅
        </h2>
        <div className="journal-totals">
          <div>
            <strong>{journal.visits.length}</strong>
            <span>訪問</span>
          </div>
          <div>
            <strong>{journal.achievements.length}</strong>
            <span>実績</span>
          </div>
          <div>
            <strong>{journal.plans.length}</strong>
            <span>次の旅</span>
          </div>
        </div>
      </section>
      <section className="collection">
        <div className="section-heading">
          <div>
            <p className="eyebrow">四季の謎</p>
            <h2>集めた季節</h2>
          </div>
          <span className="section-number">{puzzleSeasons.size} / 4</span>
        </div>
        <div className="collection-seasons">
          {seasons.map((s) => {
            const earned = puzzleSeasons.has(s);
            return (
              <div key={s} className={earned ? 'collected' : ''}>
                <SeasonSeal season={s} earned={earned} />
                <strong>{seasonName[s]}</strong>
                <span>{earned ? '謎を達成' : 'これから'}</span>
              </div>
            );
          })}
        </div>
      </section>
      {unfinished.length > 0 && (
        <section className="unfinished">
          <h2>開きかけの謎</h2>
          {unfinished.map((attempt) => {
            const game = catalog.games.find((g) => g.id === attempt.game_id);
            const spot = catalog.spots.find((s) => s.id === game?.spot_id);
            return (
              spot && (
                <button className="unfinished-row" key={attempt.id} onClick={() => onSpot(spot)}>
                  <Icon name="gate" />
                  <span>
                    {attempt.title}
                    <small>{spot.name}</small>
                  </span>
                  <Icon name="arrow" />
                </button>
              )
            );
          })}
        </section>
      )}
      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">日付をたどる</p>
            <h2>旅のあしあと</h2>
          </div>
        </div>
        {timeline.length ? (
          <ol className="timeline">
            {timeline.map((item) => (
              <li key={item.id}>
                <div className={`timeline-dot ${item.type === '実績' ? 'is-achievement' : ''}`}>
                  <Icon name={item.icon} />
                </div>
                <div>
                  <time dateTime={item.time}>{dateLabel(item.time)}</time>
                  <span className="record-type">{item.type}</span>
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <Empty
            title="まだ、白紙の手帳です"
            action={
              <button
                className="text-button"
                onClick={() => {
                  const first = catalog.spots[0];
                  if (first) onSpot(first);
                }}
              >
                最初の場所をひらく <Icon name="arrow" />
              </button>
            }
          >
            現地で訪問コードを入力すると、最初のあしあとが残ります。
          </Empty>
        )}
      </section>
      <div className="journal-next">
        <Icon name="bookmark" />
        <div>
          <h2>次のページを、用意しよう。</h2>
          <p>気になる季節や場所を「次の旅」に残せます。</p>
        </div>
        <button className="button secondary" onClick={onNext}>
          次の旅をひらく <Icon name="arrow" />
        </button>
      </div>
    </div>
  );
}
