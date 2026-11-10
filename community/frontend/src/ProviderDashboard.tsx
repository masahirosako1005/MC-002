import { lazy, Suspense, useEffect, useState } from "react";
import { api } from "./api";
import Choice from "./Choice";
import type { Provider } from "./marketplace-types";
import type {
  Analytics,
  CityAnalytics,
  CityMetricKey,
  DisplayMetric,
  Scope,
  SelfMetricKey,
  WorkspaceTab,
} from "./provider-analytics-types";
import { Empty, ErrorBox, Icon } from "./ui";
import { errorMessage } from "./validation";
import ProviderTrend from "./ProviderTrend";
import Breakdown from "./ProviderBreakdown";
const ProviderOriginMap = lazy(() => import("./ProviderOriginMap"));
const number = new Intl.NumberFormat("ja-JP");
const selfMetrics: { key: SelfMetricKey; label: string; short: string }[] = [
  { key: "consultations", label: "相談件数", short: "相談" },
  { key: "confirmed_users", label: "利用者数", short: "利用者" },
  { key: "confirmed_visits", label: "延べ参加回数", short: "参加" },
  { key: "completed_outings", label: "実施開催数", short: "開催" },
];
const cityMetrics: { key: CityMetricKey; label: string; short: string }[] = [
  { key: "visitors", label: "来訪者数", short: "来訪" },
  { key: "returning_visitors", label: "再訪者数", short: "再訪" },
  { key: "visit_days", label: "延べ来訪日数", short: "来訪日" },
  { key: "participations", label: "延べ参加回数", short: "参加" },
];
function count(value: number | null, unit = "") {
  return value === null ? "非表示" : `${number.format(value)}${unit}`;
}

function MetricRibbon({ metrics }: { metrics: DisplayMetric[] }) {
  return (
    <div className="dashboard-metrics">
      {metrics.map(({ key, label, value }) => (
        <article
          className="dashboard-metric"
          key={key}
          title={value.definition}
        >
          <h2>{label}</h2>
          <p>
            {value.count === null ? (
              <strong className="dashboard-metric-hidden">非表示</strong>
            ) : (
              <>
                <strong>{number.format(value.count)}</strong>
                <span>{value.unit}</span>
              </>
            )}
          </p>
          <small>
            {value.count === null ? (
              "少人数のため非表示"
            ) : (
              <>
                前期 {count(value.previous_count, value.unit)}
                {value.change_count !== null && (
                  <span className="dashboard-difference">
                    {value.change_count === 0
                      ? "増減なし"
                      : `${value.change_count > 0 ? "+" : ""}${number.format(value.change_count)}${value.unit}`}
                  </span>
                )}
              </>
            )}
          </small>
        </article>
      ))}
    </div>
  );
}

function SelfDetails({
  data,
  onNavigate,
}: {
  data: Analytics;
  onNavigate: (tab: WorkspaceTab) => void;
}) {
  const [tab, setTab] = useState<"plans" | "conditions" | "demographics">(
    "plans",
  );
  return (
    <section className="dashboard-detail-section">
      <div className="dashboard-detail-tabs" aria-label="自社集計の詳細">
        {(
          [
            ["plans", "プラン別実績"],
            ["conditions", "共有された条件"],
            ["demographics", "属性の収集状況"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            aria-pressed={tab === key}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "plans" ? (
        <div className="dashboard-panel">
          <header className="dashboard-panel-heading">
            <div>
              <h2>公開中のプラン別実績</h2>
              <p>非公開の相談件数は自社だけに表示</p>
            </div>
            <button className="text-button" onClick={() => onNavigate("plans")}>
              管理へ
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
                    <th scope="col">利用者</th>
                    <th scope="col">参加</th>
                    <th scope="col">開催</th>
                  </tr>
                </thead>
                <tbody>
                  {data.plans.map((plan) => (
                    <tr key={plan.id}>
                      <th scope="row">{plan.title}</th>
                      <td>{count(plan.consultations, "件")}</td>
                      <td>{count(plan.confirmed_users, "人")}</td>
                      <td>{count(plan.confirmed_visits, "人回")}</td>
                      <td>{count(plan.completed_outings, "回")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="dashboard-unavailable">
              公開中のプランはありません。
            </p>
          )}
        </div>
      ) : tab === "conditions" ? (
        <div className="dashboard-panel">
          <header className="dashboard-panel-heading">
            <div>
              <h2>相談者が共有した条件</h2>
              <p>
                相談{count(data.conditions.consultation_count, "件")}・
                {count(data.conditions.sample_count, "人")}の最新の相談
              </p>
            </div>
          </header>
          <p className="dashboard-method-note">
            希望人数や予算です。参加者本人の年齢・性別とは異なります。
          </p>
          <div className="dashboard-breakdowns">
            <Breakdown value={data.conditions.people} />
            <Breakdown value={data.conditions.nights} />
            <Breakdown value={data.conditions.budget_per_person} />
          </div>
        </div>
      ) : (
        <div className="dashboard-panel dashboard-demographics">
          <header className="dashboard-panel-heading">
            <div>
              <h2>属性の収集状況</h2>
              <p>
                対象：共有した相談者 {count(data.conditions.sample_count, "人")}
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
                    回答あり{count(data.demographics[key].known_count, "人")}
                    ・未回答{count(data.demographics[key].missing_count, "人")}
                  </span>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </section>
  );
}

function CityComparison({
  data,
  providerId,
}: {
  data: CityAnalytics;
  providerId: string;
}) {
  return (
    <section className="dashboard-panel dashboard-city-comparison">
      <header className="dashboard-panel-heading">
        <div>
          <h2>公開事業者の比較</h2>
          <p>
            {count(data.provider_count, "事業者")}・
            {count(data.published_plan_count, "公開プラン")}が対象
          </p>
        </div>
        <span className="dashboard-public-badge">市内の集計</span>
      </header>
      <p className="dashboard-method-note">
        市全体の人数は事業者をまたいで重複を除きます。各社の人数は合算できません。
      </p>
      {data.providers.status === "insufficient_sample" && (
        <p className="dashboard-unavailable">
          {data.providers.reason ||
            "少人数の内訳を含むため、事業者別の利用実績は非表示です。"}
        </p>
      )}
      {data.providers.items.length ? (
        <div className="dashboard-table-wrap">
          <table className="dashboard-comparison-table">
            <thead>
              <tr>
                <th scope="col">事業者</th>
                <th scope="col">公開プラン</th>
                <th scope="col">利用者</th>
                <th scope="col">参加</th>
                <th scope="col">開催</th>
              </tr>
            </thead>
            <tbody>
              {data.providers.items.map((provider) => (
                <tr
                  key={provider.id}
                  className={provider.id === providerId ? "is-own" : ""}
                >
                  <th scope="row">
                    <span>
                      {provider.name}
                      {provider.id === providerId && (
                        <small className="dashboard-own-label">自社</small>
                      )}
                    </span>
                    <small className="dashboard-provider-area">
                      {provider.area}
                    </small>
                  </th>
                  <td>{count(provider.published_plan_count, "件")}</td>
                  <td>
                    {data.providers.status !== "insufficient_sample"
                      ? count(provider.visitors, "人")
                      : "非表示"}
                  </td>
                  <td>
                    {data.providers.status !== "insufficient_sample"
                      ? count(provider.participations, "人回")
                      : "非表示"}
                  </td>
                  <td>
                    {data.providers.status !== "insufficient_sample"
                      ? count(provider.completed_outings, "回")
                      : "非表示"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="dashboard-unavailable">公開対象の事業者はありません。</p>
      )}
      {data.plan_categories.length > 0 && (
        <details className="dashboard-definitions">
          <summary>公開プランの分野を見る</summary>
          <p className="dashboard-muted">
            公開プランについたタグの本数です。複数タグは重複し、利用者の属性は表しません。
          </p>
          <ul className="dashboard-category-list">
            {data.plan_categories.map((category) => (
              <li key={category.id}>
                <span>{category.label}</span>
                <strong>{count(category.plan_count, "件")}</strong>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

type Result =
  { scope: "self"; data: Analytics } | { scope: "city"; data: CityAnalytics };
function AnalyticsContent({
  providerId,
  days,
  scope,
  onNavigate,
}: {
  providerId: string;
  days: number;
  scope: Scope;
  onNavigate: (tab: WorkspaceTab) => void;
}) {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        if (scope === "city") {
          const data = await api<CityAnalytics>(
            `/providers/${encodeURIComponent(providerId)}/city-analytics?days=${days}`,
            "GET",
            undefined,
            { signal: controller.signal },
          );
          if (!controller.signal.aborted) setResult({ scope: "city", data });
        } else {
          const data = await api<Analytics>(
            `/providers/${encodeURIComponent(providerId)}/analytics?days=${days}`,
            "GET",
            undefined,
            { signal: controller.signal },
          );
          if (!controller.signal.aborted) setResult({ scope: "self", data });
        }
      } catch (cause) {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      }
    }
    void load();
    return () => controller.abort();
  }, [providerId, days, scope]);
  if (error) return <ErrorBox message={error} />;
  if (!result)
    return (
      <output className="dashboard-loading" aria-live="polite">
        {scope === "city" ? "N西市全体の集計" : "自社の実績"}を読み込んでいます…
      </output>
    );
  const data = result.data;
  const metrics: DisplayMetric[] =
    result.scope === "city"
      ? cityMetrics.map((item) => ({
          ...item,
          value: result.data.summary[item.key],
        }))
      : selfMetrics.map((item) => ({
          ...item,
          value: result.data.summary[item.key],
        }));
  const daily =
    result.scope === "city"
      ? result.data.trend.items.map((item) => ({
          date: item.date,
          endDate: item.end_date,
          values: cityMetrics.map((metric) => item[metric.key]),
        }))
      : result.data.daily.map((item) => ({
          date: item.date,
          values: selfMetrics.map((metric) => item[metric.key]),
        }));
  const updated = new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tokyo",
  }).format(new Date(data.generated_at));
  return (
    <div className="dashboard-results">
      <div className="dashboard-period">
        <span className={`dashboard-scope-label ${scope}`}>
          {scope === "city" ? "市全体の集計" : "自社専用"}
        </span>
        <p>
          {data.period.start_date} — {data.period.end_date}
        </p>
        <small>
          {updated}更新{data.period.today_partial ? " · 本日は途中集計" : ""}
        </small>
      </div>
      <MetricRibbon metrics={metrics} />
      <div className="dashboard-analysis-grid">
        <ProviderTrend
          intervalDays={
            result.scope === "city" ? result.data.trend.interval_days : 1
          }
          metrics={metrics}
          items={daily}
          status={
            result.scope === "city" ? result.data.trend.status : "available"
          }
          reason={result.scope === "city" ? result.data.trend.reason : null}
        />
        <Suspense
          fallback={
            <output className="dashboard-loading">
              居住地域を読み込んでいます…
            </output>
          }
        >
          <ProviderOriginMap value={data.origins} compact />
        </Suspense>
      </div>
      {result.scope === "city" ? (
        <CityComparison data={result.data} providerId={providerId} />
      ) : (
        <SelfDetails data={result.data} onNavigate={onNavigate} />
      )}
      <details className="dashboard-definitions">
        <summary>集計の対象・定義・非表示の条件</summary>
        <p>
          比較期間：{data.period.previous_start_date} —{" "}
          {data.period.previous_end_date}（日本時間）
        </p>
        <dl>
          {metrics.map(({ key, label, value }) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd>
                {value.definition}
                {"reason" in value && value.reason && <p>{value.reason}</p>}
              </dd>
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
  const [scope, setScope] = useState<Scope>("self");
  const [days, setDays] = useState(90);
  const [revision, setRevision] = useState(0);
  const provider =
    providers.find((item) => item.id === selectedId) || providers[0];
  if (!provider) return <Empty title="管理できる事業者がありません" />;
  return (
    <div className="provider-dashboard">
      <h1 className="sr-only">自社とN西市全体の実績</h1>
      <div className="dashboard-toolbar">
        <div className="dashboard-scope-switch" aria-label="集計の範囲">
          <button
            aria-pressed={scope === "self"}
            onClick={() => setScope("self")}
          >
            自社
          </button>
          <button
            aria-pressed={scope === "city"}
            onClick={() => setScope("city")}
          >
            N西市全体
          </button>
        </div>
        <div className="dashboard-range" aria-label="集計期間">
          {[30, 90, 365].map((value) => (
            <button
              key={value}
              aria-label={`過去${value}日`}
              aria-pressed={days === value}
              onClick={() => setDays(value)}
            >
              {value}日
            </button>
          ))}
        </div>
        <button
          className="dashboard-refresh"
          aria-label="集計を更新する"
          title="集計を更新する"
          onClick={() => setRevision((value) => value + 1)}
        >
          <Icon name="refresh" />
        </button>
        {providers.length > 1 && (
          <Choice
            ariaLabel="管理する事業者"
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
      </div>
      <AnalyticsContent
        key={`${provider.id}-${scope}-${days}-${revision}`}
        providerId={provider.id}
        days={days}
        scope={scope}
        onNavigate={onNavigate}
      />
    </div>
  );
}
