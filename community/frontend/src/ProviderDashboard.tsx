import { lazy, Suspense, useEffect, useId, useState } from "react";
import type { ProviderOrigins } from "./ProviderOriginMap";
import { api } from "./api";
import Choice from "./Choice";
import type { Provider } from "./marketplace-types";
import { Empty, ErrorBox, Icon } from "./ui";
import { errorMessage } from "./validation";
const ProviderOriginMap = lazy(() => import("./ProviderOriginMap"));

type MetricKey =
  | "consultations"
  | "confirmed_users"
  | "confirmed_visits"
  | "completed_outings";
type WorkspaceTab = "plans" | "consultations" | "circles" | "daytrip";
type Metric = {
  count: number;
  previous_count: number;
  change_count: number;
  change_percent: number | null;
  unit: string;
  definition: string;
};
type Daily = { date: string } & Record<MetricKey, number>;
type Distribution = {
  label: string;
  status: "available" | "insufficient_sample" | "no_data";
  known_count: number;
  missing_count: number;
  bins: { key: string; label: string; count: number | null }[];
  reason: string | null;
};
type Analytics = {
  provider_id: string;
  generated_at: string;
  period: {
    days: number;
    timezone: string;
    start_date: string;
    end_date: string;
    previous_start_date: string;
    previous_end_date: string;
    today_partial: boolean;
  };
  summary: Record<MetricKey, Metric>;
  daily: Daily[];
  plans: ({ id: string; title: string; status: "published" } & Record<
    MetricKey,
    number
  >)[];
  conditions: {
    population_unit: string;
    sample_count: number;
    unique_sharers: number;
    consultation_count: number;
    people: Distribution;
    nights: Distribution;
    budget_per_person: Distribution;
  };
  demographics: Record<
    "age" | "gender" | "interests",
    {
      status: "not_collected";
      reason: string;
      known_count: number;
      missing_count: number;
    }
  >;
  notes: string[];
  origins: ProviderOrigins;
};
const metrics: { key: MetricKey; label: string; short: string }[] = [
  { key: "consultations", label: "届いた相談", short: "相談" },
  { key: "confirmed_users", label: "実参加を確認した人", short: "実参加者" },
  { key: "confirmed_visits", label: "確認済みの延べ参加", short: "延べ参加" },
  { key: "completed_outings", label: "実施確認のある開催", short: "開催" },
];
const number = new Intl.NumberFormat("ja-JP");
function shortDate(value: string) {
  return value.slice(5).replace("-", "/");
}

function Trend({
  daily,
  summary,
}: {
  daily: Daily[];
  summary: Analytics["summary"];
}) {
  const [metric, setMetric] = useState<MetricKey>("consultations");
  const [tableOpen, setTableOpen] = useState(false);
  const titleId = useId();
  const title =
    metrics.find((item) => item.key === metric)?.label || "日別推移";
  const maximum = Math.max(1, ...daily.map((item) => item[metric]));
  const top = maximum > 4 ? Math.ceil(maximum / 4) * 4 : maximum;
  const ticks = [...new Set([0, Math.ceil(top / 2), top])];
  const positionX = (index: number) =>
    (index / Math.max(1, daily.length - 1)) * 504;
  const positionY = (value: number) => 132 - (value / top) * 132;
  const points = daily
    .map((item, index) => `${positionX(index)},${positionY(item[metric])}`)
    .join(" ");
  const dates = [
    ...new Set([0, Math.floor((daily.length - 1) / 2), daily.length - 1]),
  ].filter((index) => index >= 0);
  return (
    <section
      className="dashboard-panel dashboard-trend"
      aria-labelledby={titleId}
    >
      <header className="dashboard-panel-heading">
        <div>
          <h2 id={titleId}>日別の推移</h2>
          <p>1日ごとの記録 · {summary[metric].unit}</p>
        </div>
      </header>
      <div className="dashboard-chart-switch" aria-label="推移の指標">
        {metrics.map((item) => (
          <button
            key={item.key}
            aria-pressed={metric === item.key}
            onClick={() => setMetric(item.key)}
          >
            {item.short}
          </button>
        ))}
      </div>
      {daily.length > 0 ? (
        <div className="dashboard-chart-area">
          <div className="dashboard-y-axis" aria-hidden="true">
            {ticks.map((tick) => (
              <span key={tick} style={{ bottom: `${(tick / top) * 100}%` }}>
                {tick}
              </span>
            ))}
          </div>
          <svg
            className="dashboard-chart"
            viewBox="0 0 504 132"
            preserveAspectRatio="none"
            aria-label={`${title}の日別推移。詳しい値は日別の数値表で確認できます。`}
          >
            <title>{title}の日別推移</title>
            {ticks.map((tick) => (
              <line
                key={tick}
                className="dashboard-chart-grid"
                x1="0"
                x2="504"
                y1={positionY(tick)}
                y2={positionY(tick)}
              />
            ))}
            <polyline className="dashboard-chart-line" points={points} />
            {daily.length === 1 && (
              <circle
                className="dashboard-chart-dot"
                cx={0}
                cy={positionY(daily[0][metric])}
                r="3"
              />
            )}
          </svg>
          <div className="dashboard-x-axis" aria-hidden="true">
            {dates.map((index) => (
              <span key={daily[index].date}>
                {shortDate(daily[index].date)}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p className="dashboard-muted">この期間の日別記録はありません。</p>
      )}
      {metric === "confirmed_users" && (
        <p className="dashboard-muted">
          同じ人の別の日の参加は日ごとに計上します。期間全体の人数は重複を除きます。
        </p>
      )}
      <details
        className="dashboard-data-table"
        onToggle={(event) => setTableOpen(event.currentTarget.open)}
      >
        <summary>日別の数値を見る</summary>
        {tableOpen && (
          <table>
            <caption>{title}の日別記録</caption>
            <thead>
              <tr>
                <th scope="col">日付</th>
                <th scope="col">
                  {title}（{summary[metric].unit}）
                </th>
              </tr>
            </thead>
            <tbody>
              {daily.map((item) => (
                <tr key={item.date}>
                  <th scope="row">{item.date}</th>
                  <td>{number.format(item[metric])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
    </section>
  );
}

function Breakdown({ value }: { value: Distribution }) {
  const maximum = Math.max(1, ...value.bins.map((bin) => bin.count || 0));
  return (
    <section className="dashboard-breakdown">
      <h3>{value.label}</h3>
      <p className="dashboard-muted">
        回答あり {number.format(value.known_count)}人 · 対象外・未回答{" "}
        {number.format(value.missing_count)}人
      </p>
      {value.status === "available" ? (
        <ul className="dashboard-bars">
          {value.bins.map((bin) => (
            <li key={bin.key}>
              <span>{bin.label}</span>
              <div className="dashboard-bar-track">
                <span
                  className="dashboard-bar-fill"
                  style={{ width: `${((bin.count || 0) / maximum) * 100}%` }}
                />
              </div>
              <strong>
                {bin.count === null
                  ? "非表示"
                  : `${number.format(bin.count)}人`}
              </strong>
            </li>
          ))}
        </ul>
      ) : (
        <p className="dashboard-unavailable">
          {value.reason || "集計できる回答がまだありません。"}
        </p>
      )}
      {value.status === "available" && value.reason && (
        <p className="dashboard-muted">{value.reason}</p>
      )}
    </section>
  );
}

function AnalyticsContent({
  providerId,
  days,
  onNavigate,
}: {
  providerId: string;
  days: number;
  onNavigate: (tab: WorkspaceTab) => void;
}) {
  const [result, setResult] = useState<{
    data: Analytics | null;
    error: string;
  }>({ data: null, error: "" });
  useEffect(() => {
    const controller = new AbortController();
    api<Analytics>(
      `/providers/${encodeURIComponent(providerId)}/analytics?days=${days}`,
      "GET",
      undefined,
      { signal: controller.signal },
    )
      .then((data) => {
        if (!controller.signal.aborted) setResult({ data, error: "" });
        return undefined;
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted)
          setResult({ data: null, error: errorMessage(cause) });
      });
    return () => controller.abort();
  }, [providerId, days]);
  if (result.error) return <ErrorBox message={result.error} />;
  if (!result.data)
    return (
      <output className="dashboard-loading" aria-live="polite">
        実績を読み込んでいます…
      </output>
    );
  const data = result.data;
  const updated = new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tokyo",
  }).format(new Date(data.generated_at));
  return (
    <div className="dashboard-results">
      <div className="dashboard-period">
        <p>
          {data.period.start_date} — {data.period.end_date}
          <span>
            日本時間{data.period.today_partial ? " · 本日分は途中集計" : ""}
          </span>
        </p>
        <small>{updated} 更新</small>
      </div>
      <div className="dashboard-metrics">
        {metrics.map(({ key, label }) => {
          const item = data.summary[key];
          return (
            <article className="dashboard-metric" key={key}>
              <h2>{label}</h2>
              <p>
                <strong>{number.format(item.count)}</strong>
                <span>{item.unit}</span>
              </p>
              <small>
                前期間 {number.format(item.previous_count)}
                {item.unit}
                <span className="dashboard-difference">
                  {item.change_count === 0
                    ? "増減なし"
                    : `（${item.change_count > 0 ? "+" : ""}${number.format(item.change_count)}${item.unit}）`}
                </span>
              </small>
            </article>
          );
        })}
      </div>
      <div className="dashboard-work-links">
        <button onClick={() => onNavigate("consultations")}>
          <Icon name="people" />
          相談を確認
          <Icon name="arrow" />
        </button>
        <button onClick={() => onNavigate("daytrip")}>
          <Icon name="calendar" />
          実施確認・特典
          <Icon name="arrow" />
        </button>
        <button onClick={() => onNavigate("plans")}>
          <Icon name="compass" />
          プランを管理
          <Icon name="arrow" />
        </button>
      </div>
      <Suspense
        fallback={
          <output className="dashboard-loading">
            居住地域の集計をひらいています…
          </output>
        }
      >
        <ProviderOriginMap value={data.origins} />
      </Suspense>
      <Trend daily={data.daily} summary={data.summary} />
      <section className="dashboard-panel">
        <header className="dashboard-panel-heading">
          <div>
            <h2>相談者が共有した条件</h2>
            <p>
              相談 {number.format(data.conditions.consultation_count)}件 ·
              相談者 {number.format(data.conditions.sample_count)}人の最新の相談
            </p>
          </div>
        </header>
        <p className="dashboard-method-note">
          希望人数や予算の内訳です。参加者本人の年齢・性別とは異なります。
        </p>
        <div className="dashboard-breakdowns">
          <Breakdown value={data.conditions.people} />
          <Breakdown value={data.conditions.nights} />
          <Breakdown value={data.conditions.budget_per_person} />
        </div>
      </section>
      <section className="dashboard-panel">
        <header className="dashboard-panel-heading">
          <div>
            <h2>公開中のプラン別実績</h2>
            <p>選択した期間内の記録</p>
          </div>
          <button className="text-button" onClick={() => onNavigate("plans")}>
            プラン管理
            <Icon name="arrow" />
          </button>
        </header>
        {data.plans.length ? (
          <div className="dashboard-table-wrap">
            <table className="dashboard-plan-table">
              <thead>
                <tr>
                  <th scope="col">プラン</th>
                  <th scope="col">相談</th>
                  <th scope="col">実参加者</th>
                  <th scope="col">延べ参加</th>
                  <th scope="col">開催</th>
                </tr>
              </thead>
              <tbody>
                {data.plans.map((plan) => (
                  <tr key={plan.id}>
                    <th scope="row">{plan.title}</th>
                    <td>{number.format(plan.consultations)}件</td>
                    <td>{number.format(plan.confirmed_users)}人</td>
                    <td>{number.format(plan.confirmed_visits)}人回</td>
                    <td>{number.format(plan.completed_outings)}回</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="dashboard-unavailable">公開中のプランはありません。</p>
        )}
      </section>
      <section className="dashboard-panel dashboard-demographics">
        <header className="dashboard-panel-heading">
          <div>
            <h2>利用者の属性</h2>
            <p>
              対象：共有した相談者 {number.format(data.conditions.sample_count)}
              人。未収集の値は推定しません。
            </p>
          </div>
        </header>
        <dl>
          {(
            [
              ["age", "年齢"],
              ["gender", "性別"],
              ["interests", "関心"],
            ] as const
          ).map(([key, label]) => (
            <div key={key}>
              <dt>
                {label}
                <span>未収集</span>
              </dt>
              <dd>
                {data.demographics[key].reason}
                <span className="dashboard-demographic-count">
                  回答あり {number.format(data.demographics[key].known_count)}人
                  · 未回答 {number.format(data.demographics[key].missing_count)}
                  人
                </span>
              </dd>
            </div>
          ))}
        </dl>
      </section>
      <details className="dashboard-definitions">
        <summary>集計の範囲と数え方</summary>
        <p>
          比較期間：{data.period.previous_start_date} —{" "}
          {data.period.previous_end_date}
        </p>
        <dl>
          {metrics.map(({ key, label }) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd>{data.summary[key].definition}</dd>
            </div>
          ))}
        </dl>
        <ul>
          {data.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}

export default function ProviderDashboard({
  providers,
  onNavigate,
}: {
  providers: Provider[];
  onNavigate: (tab: WorkspaceTab) => void;
}) {
  const [selectedId, setSelectedId] = useState(providers[0]?.id || "");
  const [days, setDays] = useState(90);
  const [revision, setRevision] = useState(0);
  const provider =
    providers.find((item) => item.id === selectedId) || providers[0];
  if (!provider) return <Empty title="管理できる事業者がありません" />;
  return (
    <div className="provider-dashboard">
      <div className="dashboard-toolbar">
        {providers.length > 1 && (
          <Choice
            ariaLabel="集計する事業者"
            value={provider.id}
            onChange={(event) => setSelectedId(event.target.value)}
          >
            {providers.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </Choice>
        )}
        <div className="dashboard-range" aria-label="集計期間">
          {[30, 90, 365].map((value) => (
            <button
              key={value}
              aria-pressed={days === value}
              onClick={() => setDays(value)}
            >
              過去{value}日
            </button>
          ))}
        </div>
        <button
          className="text-button"
          onClick={() => setRevision((value) => value + 1)}
        >
          <Icon name="refresh" />
          再集計
        </button>
      </div>
      <AnalyticsContent
        key={`${provider.id}-${days}-${revision}`}
        providerId={provider.id}
        days={days}
        onNavigate={onNavigate}
      />
    </div>
  );
}
