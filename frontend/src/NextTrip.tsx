import { useEffect, useRef, useState } from 'react';
import { api, errorMessage } from './api';
import type { Catalog, Plan, Recommendations, Season, Spot } from './types';
import { seasonName, seasons } from './types';
import { Empty, ErrorNotice, Icon, Scene, SeasonSeal } from './ui';
import { SaveButton } from './SaveButton';

export function NextTrip({
  catalog,
  plans,
  onSaved,
  onRemoved,
  onSpot,
}: {
  catalog: Catalog;
  plans: Plan[];
  onSaved: (plan: Plan) => void;
  onRemoved: (id: string) => void;
  onSpot: (spot: Spot) => void;
}) {
  const [minutes, setMinutes] = useState(90);
  const [season, setSeason] = useState<Season>(catalog.season);
  const [interest, setInterest] = useState('all');
  const [results, setResults] = useState<Recommendations | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const [confirm, setConfirm] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState('');
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setResults(null);
    api
      .recommendations(minutes, season, interest)
      .then((data) => {
        if (active) setResults(data);
      })
      .catch((e) => {
        if (active) setError(errorMessage(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [minutes, season, interest, revision]);
  const remove = async (id: string) => {
    if (lock.current) return;
    lock.current = true;
    setRemoving(true);
    setRemoveError('');
    try {
      await api.remove(id);
      onRemoved(id);
      setConfirm(null);
    } catch (e) {
      setRemoveError(errorMessage(e));
    } finally {
      lock.current = false;
      setRemoving(false);
    }
  };
  const resourceSpots = catalog.spots.filter((s) => s.kind === 'shrine' || s.kind === 'coast');
  return (
    <div className="next-page page-padding">
      <div className="page-title">
        <p className="eyebrow">続きは、次の季節に。</p>
        <h1>次の旅</h1>
        <p>
          もう一度、会いたい景色へ。
          <br />
          時間と関心から、寄り道を見つける。
        </p>
      </div>
      <section className="trip-finder">
        <div className="finder-heading">
          <Icon name="compass" />
          <h2>旅の余白を見つける</h2>
        </div>
        <p>国際会議場を出発して、戻るまでの時間で探せます。</p>
        <div className="finder-selects">
          <label>
            使える時間
            <span className="select-wrap">
              <select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
                {[30, 60, 90, 120, 180, 240].map((n) => (
                  <option key={n} value={n}>
                    {n}分
                  </option>
                ))}
              </select>
              <Icon name="arrow" />
            </span>
          </label>
          <label>
            気になること
            <span className="select-wrap">
              <select value={interest} onChange={(e) => setInterest(e.target.value)}>
                <option value="all">すべて</option>
                <option value="shrine">神社と節目</option>
                <option value="coast">海辺の体験</option>
              </select>
              <Icon name="arrow" />
            </span>
          </label>
        </div>
        <fieldset>
          <legend>訪れたい季節</legend>
          <div className="segmented four-seasons">
            {seasons.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={season === s}
                onClick={() => setSeason(s)}
              >
                {seasonName[s]}
              </button>
            ))}
          </div>
        </fieldset>
      </section>
      <section
        className="recommendations"
        aria-labelledby="recommendation-heading"
        aria-busy={loading}
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              {seasonName[season]} ／ {minutes}分の旅
            </p>
            <h2 id="recommendation-heading">時間におさまる寄り道</h2>
          </div>
        </div>
        {loading ? (
          <p className="inline-loading" role="status">
            時間と季節に合う体験を探しています…
          </p>
        ) : error ? (
          <ErrorNotice message={error} retry={() => setRevision((v) => v + 1)} />
        ) : (
          results && (
            <>
              <p className="recommendation-reason">{results.reason}</p>
              {results.items.length ? (
                <div className="recommendation-list">
                  {results.items.map((item, i) => (
                    <article
                      className={`recommendation-card ${i === 0 ? 'featured' : ''}`}
                      key={item.experience.id}
                    >
                      <div className="recommendation-art">
                        <Scene
                          kind={item.spot.kind}
                          season={
                            item.experience.season === 'all' ? season : item.experience.season
                          }
                        />
                        <span className="duration-badge">
                          <strong>{item.total_minutes}</strong>分
                        </span>
                      </div>
                      <div className="recommendation-copy">
                        <p className="eyebrow">
                          {item.spot.name} ／ {item.experience.month_label}
                        </p>
                        <h3>{item.experience.title}</h3>
                        <p>{item.experience.description}</p>
                        <div className="time-breakdown" aria-label="所要時間の内訳">
                          <span>
                            往復<strong>{item.travel_minutes}分</strong>
                          </span>
                          <span>
                            体験<strong>{item.experience.duration_minutes}分</strong>
                          </span>
                          <span>
                            余裕<strong>{item.buffer_minutes}分</strong>
                          </span>
                        </div>
                        <p className="why-recommended">
                          <Icon name="hint" />
                          {item.reason}
                        </p>
                        <SaveButton
                          experience={item.experience}
                          plans={plans}
                          onSaved={onSaved}
                          reason={item.reason}
                        />
                        <button className="text-button" onClick={() => onSpot(item.spot)}>
                          場所の案内を読む <Icon name="arrow" />
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <Empty title="この条件では見つかりませんでした">
                  使える時間を増やすか、別の季節・関心を選んでみてください。
                </Empty>
              )}
            </>
          )
        )}
      </section>
      <section className="saved-trips" aria-labelledby="saved-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">しおりを挟んだ体験</p>
            <h2 id="saved-heading">
              行きたい旅 <span className="heading-count">{plans.length}</span>
            </h2>
          </div>
          <Icon name="bookmark" />
        </div>
        {plans.length ? (
          <div className="plan-list">
            {plans.map((plan) => (
              <article className="plan-card" key={plan.id}>
                <SeasonSeal season={plan.season} />
                <div className="plan-copy">
                  <p className="eyebrow">
                    {plan.month_label} ／ {plan.spot_name}
                  </p>
                  <h3>{plan.title}</h3>
                  <p>{plan.reason}</p>
                  <span className="planned-label">これから訪れたい場所</span>
                  {confirm === plan.id ? (
                    <div className="remove-confirm">
                      <p>この体験を次の旅から外しますか？</p>
                      <div>
                        <button
                          className="text-button"
                          disabled={removing}
                          onClick={() => {
                            setConfirm(null);
                            setRemoveError('');
                          }}
                        >
                          残す
                        </button>
                        <button
                          className="text-button danger"
                          disabled={removing}
                          onClick={() => void remove(plan.id)}
                        >
                          {removing ? '外しています…' : '次の旅から外す'}
                        </button>
                      </div>
                      {removeError && <ErrorNotice message={removeError} />}
                    </div>
                  ) : (
                    <button
                      className="remove-button"
                      onClick={() => {
                        setConfirm(plan.id);
                        setRemoveError('');
                      }}
                      aria-label={`${plan.title}を次の旅から外す`}
                    >
                      <Icon name="trash" />
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty title="次の旅に、しおりを挟もう">
            気になる体験の「次の旅に保存」を押すと、ここに残せます。
          </Empty>
        )}
      </section>
      <section className="season-stories">
        <div className="section-heading">
          <div>
            <p className="eyebrow">同じ場所、違う楽しみ。</p>
            <h2>季節と節目をたどる</h2>
          </div>
        </div>
        {resourceSpots.map((spot) => (
          <article key={spot.id} className="resource-story">
            <div className="resource-title">
              <Icon name={spot.kind} />
              <h3>{spot.name}</h3>
            </div>
            <ol>
              {catalog.experiences
                .filter((e) => e.spot_id === spot.id)
                .map((exp) => (
                  <li key={exp.id}>
                    <div className={`story-dot season-${exp.season}`} />
                    <div>
                      <span className="eyebrow">{exp.month_label}</span>
                      <h4>{exp.title}</h4>
                      <p>{exp.description}</p>
                      <SaveButton
                        experience={exp}
                        plans={plans}
                        onSaved={onSaved}
                        reason={`${spot.name}の${exp.title}を体験するため`}
                        compact
                      />
                    </div>
                  </li>
                ))}
            </ol>
          </article>
        ))}
      </section>
    </div>
  );
}
