import { useId, useState } from "react";
import type { DisplayMetric, TrendDay } from "./provider-analytics-types";
const number = new Intl.NumberFormat("ja-JP");
export default function ProviderTrend({
  items,
  metrics,
  status,
  reason,
  intervalDays,
}: {
  items: TrendDay[];
  metrics: DisplayMetric[];
  status: "available" | "insufficient_sample" | "no_data";
  reason: string | null;
  intervalDays: number;
}) {
  const [metricIndex, setMetricIndex] = useState(0);
  const [tableOpen, setTableOpen] = useState(false);
  const titleId = useId();
  const metric = metrics[metricIndex];
  const maximum = items.reduce(
    (value, item) =>
      item.values[metricIndex] === null
        ? value
        : Math.max(value, item.values[metricIndex]),
    1,
  );
  const top = maximum > 4 ? Math.ceil(maximum / 4) * 4 : maximum;
  const ticks = [...new Set([0, Math.ceil(top / 2), top])];
  const positionX = (index: number) =>
    items.length === 1 ? 252 : (index / Math.max(1, items.length - 1)) * 504;
  const positionY = (value: number) => 132 - (value / top) * 132;
  const unavailable =
    status === "insufficient_sample" ||
    items.some((item) => item.values[metricIndex] === null);
  const points = unavailable
    ? ""
    : items
        .flatMap((item, index) => {
          const value = item.values[metricIndex];
          return value === null
            ? []
            : [`${positionX(index)},${positionY(value)}`];
        })
        .join(" ");
  const dates = [
    ...new Set([0, Math.floor((items.length - 1) / 2), items.length - 1]),
  ].filter((index) => index >= 0);
  return (
    <section
      className="dashboard-panel dashboard-trend"
      aria-labelledby={titleId}
    >
      <header className="dashboard-panel-heading">
        <h2 id={titleId}>
          {intervalDays === 1 ? "日別推移" : "期間ごとの推移"}
        </h2>
        <span className="dashboard-unit">
          {metric.value.unit} /{" "}
          {intervalDays === 1 ? "日" : `${intervalDays}日間`}
        </span>
      </header>
      <div className="dashboard-chart-switch" aria-label="推移の指標">
        {metrics.map((item, index) => (
          <button
            key={item.key}
            aria-pressed={index === metricIndex}
            onClick={() => setMetricIndex(index)}
          >
            {item.short}
          </button>
        ))}
      </div>
      {unavailable ? (
        <div className="dashboard-chart-unavailable">
          <span>{intervalDays === 1 ? "日別" : "期間別"}内訳は非表示</span>
          <p>{reason || "少人数の内訳を含むため表示していません。"}</p>
        </div>
      ) : status === "no_data" ? (
        <div className="dashboard-chart-unavailable">
          <p>この期間の確認済み利用はありません。</p>
        </div>
      ) : items.length ? (
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
            aria-label={`${metric.label}の推移。数値表で詳細を確認できます。`}
          >
            <title>{metric.label}の推移</title>
            {ticks.map((tick) => (
              <line
                className="dashboard-chart-grid"
                key={tick}
                x1="0"
                x2="504"
                y1={positionY(tick)}
                y2={positionY(tick)}
              />
            ))}
            <polyline className="dashboard-chart-line" points={points} />
            {items.length === 1 && items[0].values[metricIndex] !== null && (
              <circle
                className="dashboard-chart-dot"
                cx={positionX(0)}
                cy={positionY(items[0].values[metricIndex])}
                r="5"
              />
            )}
          </svg>
          <div className="dashboard-x-axis" aria-hidden="true">
            {dates.map((index) => (
              <span key={items[index].date}>
                {items[index].date.slice(5).replace("-", "/")}
              </span>
            ))}
          </div>
          {items.length === 1 && items[0].values[metricIndex] !== null && (
            <p className="dashboard-single-value">
              {items[0].date}
              {items[0].endDate && items[0].endDate !== items[0].date
                ? `〜${items[0].endDate}`
                : ""}
              ：{number.format(items[0].values[metricIndex])}
              {metric.value.unit}
            </p>
          )}
        </div>
      ) : (
        <div className="dashboard-chart-unavailable">
          <p>この期間の記録はありません。</p>
        </div>
      )}
      <details
        className="dashboard-data-table"
        onToggle={(event) => setTableOpen(event.currentTarget.open)}
      >
        <summary>{intervalDays === 1 ? "日別" : "期間別"}の数値と定義</summary>
        <p className="dashboard-muted">{metric.value.definition}</p>
        <p className="dashboard-muted">
          区間は同じ日数で集計し、最後の区間は短くなる場合があります。区間別の人数の合計と期間全体の人数は一致しない場合があります。
        </p>
        {tableOpen && (
          <table>
            <caption>
              {metric.label}（{metric.value.unit}）
            </caption>
            <thead>
              <tr>
                <th scope="col">日付</th>
                <th scope="col">記録</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.date}>
                  <th scope="row">
                    {item.date}
                    {item.endDate && item.endDate !== item.date
                      ? `〜${item.endDate}`
                      : ""}
                  </th>
                  <td>
                    {unavailable || item.values[metricIndex] === null
                      ? "非表示"
                      : number.format(item.values[metricIndex])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
    </section>
  );
}
