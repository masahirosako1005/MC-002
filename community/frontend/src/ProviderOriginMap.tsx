import { useState } from "react";
import japan from "./map-data/japan.json";
import type { ResidenceArea, ResidenceDestination } from "./ResidenceFields";
import "./provider-origin.css";

type OriginArea = ResidenceArea & {
  visitors: number;
  returning_visitors: number | null;
  visits: number | null;
  returning_status: "available" | "insufficient_sample";
};
export type ProviderOrigins = {
  status: "available" | "insufficient_sample" | "no_data";
  destination: ResidenceDestination;
  total_visitors: number;
  consented_visitors: number;
  missing_visitors: number;
  withheld_visitors: number;
  suppressed_visitors: number;
  areas: OriginArea[];
  privacy_threshold: number;
  definitions: string[];
};
export type CityOrigins = Omit<
  ProviderOrigins,
  | "total_visitors"
  | "consented_visitors"
  | "missing_visitors"
  | "withheld_visitors"
  | "suppressed_visitors"
> & {
  total_visitors: number | null;
  consented_visitors: number | null;
  missing_visitors: number | null;
  withheld_visitors: number | null;
  suppressed_visitors: number | null;
  reason: string | null;
};
type Focus = "national" | "kansai" | "nearby";
type Mode = "visitors" | "returning_visitors";
const bounds: Record<Focus, [number, number, number, number]> = {
  national: [122, 24, 146, 46],
  kansai: [134, 33.4, 137, 36.1],
  nearby: [134.85, 34.35, 136.05, 35.2],
};
const focusLabels: Record<Focus, string> = {
  national: "全国",
  kansai: "関西",
  nearby: "N西市周辺",
};
const width = 640;
const height = 380;
const latitudeRatio = Math.cos((35 * Math.PI) / 180);
function project(longitude: number, latitude: number, focus: Focus) {
  const [west, south, east, north] = bounds[focus];
  const scale = Math.min(
    (width - 36) / ((east - west) * latitudeRatio),
    (height - 36) / (north - south),
  );
  return {
    x: width / 2 + (longitude - (east + west) / 2) * latitudeRatio * scale,
    y: height / 2 - (latitude - (north + south) / 2) * scale,
  };
}
function within(area: { latitude: number; longitude: number }, focus: Focus) {
  const [west, south, east, north] = bounds[focus];
  return (
    area.longitude >= west &&
    area.longitude <= east &&
    area.latitude >= south &&
    area.latitude <= north
  );
}
function coastline(focus: Focus) {
  return japan.coordinates
    .map((polygon) =>
      polygon
        .map(
          (ring) =>
            ring
              .map(([longitude, latitude], index) => {
                const point = project(longitude, latitude, focus);
                return `${index === 0 ? "M" : "L"}${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
              })
              .join(" ") + "Z",
        )
        .join(" "),
    )
    .join(" ");
}
const coastlines: Record<Focus, string> = {
  national: coastline("national"),
  kansai: coastline("kansai"),
  nearby: coastline("nearby"),
};
const number = new Intl.NumberFormat("ja-JP");

export default function ProviderOriginMap({
  value,
  compact = false,
}: {
  value: ProviderOrigins | CityOrigins;
  compact?: boolean;
}) {
  const [focus, setFocus] = useState<Focus>("nearby");
  const [mode, setMode] = useState<Mode>("visitors");
  const [selectedId, setSelectedId] = useState("");
  const selected = value.areas.find((area) => area.id === selectedId);
  const visible = value.areas.filter((area) => within(area, focus));
  const maximum = value.areas.reduce(
    (maximumCount, area) =>
      area[mode] === null ? maximumCount : Math.max(maximumCount, area[mode]),
    5,
  );
  const destination = project(
    value.destination.longitude,
    value.destination.latitude,
    focus,
  );
  const selectedPoint =
    selected && within(selected, focus)
      ? project(selected.longitude, selected.latitude, focus)
      : null;
  const plotted = visible.flatMap((area) => {
    const count = area[mode];
    if (count === null || count <= 0) return [];
    const point = project(area.longitude, area.latitude, focus);
    const radius = 5 + Math.sqrt(count / maximum) * 12;
    // The nearby Osaka/Suita labels sit on opposite sides of their close markers.
    const left =
      point.x > width - (compact ? 190 : 140) ||
      (point.x > (compact ? 210 : 130) &&
        (point.x < destination.x - 40 || area.city === "大阪市"));
    return [
      {
        area,
        count,
        point,
        radius,
        left,
        labelX: point.x + (left ? -26 : 26),
        labelY: Math.max(
          20,
          Math.min(height - 12, point.y + (area.city === "大阪市" ? 34 : -10)),
        ),
      },
    ];
  });
  const unitLabel = mode === "visitors" ? "来訪者" : "再訪者";
  function select(area: OriginArea) {
    setSelectedId(area.id);
    if (!within(area, focus)) setFocus("national");
  }
  return (
    <section
      className={`dashboard-panel origin-panel ${compact ? "origin-compact" : ""}`}
    >
      <header className="dashboard-panel-heading">
        <div>
          <h2>{compact ? "居住地域" : "来訪・再訪者の居住地域"}</h2>
          {!compact && (
            <p>
              目的地：{value.destination.prefecture} {value.destination.name}
            </p>
          )}
        </div>
        {compact && <span className="dashboard-unit">市区町村の代表点</span>}
      </header>
      {!compact && (
        <p className="dashboard-method-note">
          事業者確認まで完了した参加者を集計しています。市区町村の代表地点で、自宅や実際の出発地ではありません。
        </p>
      )}
      <div className="origin-controls">
        <div className="dashboard-chart-switch" aria-label="地域図の指標">
          <button
            aria-pressed={mode === "visitors"}
            aria-label="来訪者"
            onClick={() => setMode("visitors")}
          >
            {compact ? "来訪" : "来訪者"}
          </button>
          <button
            aria-pressed={mode === "returning_visitors"}
            aria-label="再訪者"
            onClick={() => setMode("returning_visitors")}
          >
            {compact ? "再訪" : "再訪者"}
          </button>
        </div>
        <div className="dashboard-chart-switch" aria-label="地域図の範囲">
          <button
            aria-pressed={focus === "nearby"}
            aria-label="N西市周辺"
            onClick={() => setFocus("nearby")}
          >
            {compact ? "周辺" : "N西市周辺"}
          </button>
          <button
            aria-pressed={focus === "kansai"}
            onClick={() => setFocus("kansai")}
          >
            関西
          </button>
          <button
            aria-pressed={focus === "national"}
            onClick={() => setFocus("national")}
          >
            全国
          </button>
        </div>
      </div>
      <figure className="origin-figure">
        <div className="origin-map">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            aria-label={`${focusLabels[focus]}の${unitLabel}の居住地域図。地域別人数は下の表で確認できます。`}
          >
            <title>
              {focusLabels[focus]}の{unitLabel}の居住地域
            </title>
            <path
              className="origin-land"
              d={coastlines[focus]}
              fillRule="evenodd"
            />
            {plotted.map(({ area, count, point, radius }) => (
              <circle
                key={area.id}
                className={`origin-circle ${area.id === selectedId ? "selected" : ""}`}
                cx={point.x}
                cy={point.y}
                r={radius}
              >
                <title>
                  {area.label}：{unitLabel} {count}人
                </title>
              </circle>
            ))}
            {focus === "nearby" &&
              plotted.map(({ area, count, point, left, labelX, labelY }) => (
                <g key={`label-${area.id}`}>
                  <line
                    className="origin-label-leader"
                    x1={point.x + (left ? -9 : 9)}
                    y1={point.y}
                    x2={labelX + (left ? 5 : -5)}
                    y2={labelY - 5}
                  />
                  <text
                    className="origin-city-label"
                    x={labelX}
                    y={labelY}
                    textAnchor={left ? "end" : "start"}
                  >
                    {area.city} {number.format(count)}人
                  </text>
                </g>
              ))}
            {selectedPoint && (
              <circle
                className="origin-selection"
                cx={selectedPoint.x}
                cy={selectedPoint.y}
                r="29"
              />
            )}
            <path
              className="origin-destination"
              d={`M${destination.x} ${destination.y - 7}l7 7-7 7-7-7Z`}
            />
          </svg>
          <span
            className="origin-place-label"
            style={{
              left: `${(destination.x / width) * 100}%`,
              top: `${(destination.y / height) * 100}%`,
            }}
          >
            {value.destination.name}
          </span>
          {selectedPoint &&
            selected &&
            (focus !== "nearby" ||
              selected[mode] === null ||
              selected[mode] === 0) && (
              <span
                className="origin-selection-label"
                style={{
                  left: `${(selectedPoint.x / width) * 100}%`,
                  top: `${(selectedPoint.y / height) * 100}%`,
                }}
              >
                {selected.city} ·{" "}
                {selected[mode] === null
                  ? "再訪の内訳は非表示"
                  : `${number.format(selected[mode])}人`}
              </span>
            )}
        </div>
        <figcaption>
          <span className="origin-map-legend">
            <i />
            円の大きさ：{unitLabel}数
          </span>
          <span>
            <b />
            目的地
          </span>
          {!compact && <span>人数0人の地域は円を表示しません。</span>}
        </figcaption>
      </figure>
      {value.status !== "available" && (
        <p className="origin-status">
          {compact
            ? value.status === "no_data"
              ? "表示できる居住地域の記録はありません。"
              : "少人数の内訳を含むため地域図は非表示です。"
            : ("reason" in value && value.reason) ||
              (value.status === "no_data"
                ? "この期間に地図へ表示できる居住地域の記録はありません。"
                : "共有が許可された地域の人数が少ないため、地図に表示していません。")}
        </p>
      )}
      {focus !== "national" &&
        value.areas.some((area) => !within(area, focus)) && (
          <p className="dashboard-muted">
            表示範囲外の地域があります。全国に切り替えると確認できます。
          </p>
        )}
      <p className="origin-brief">
        未登録{" "}
        {value.missing_visitors === null
          ? "非表示"
          : `${number.format(value.missing_visitors)}人`}{" "}
        · 未共有{" "}
        {value.withheld_visitors === null
          ? "非表示"
          : `${number.format(value.withheld_visitors)}人`}{" "}
        · 少人数の地域は非表示
      </p>
      <details className="origin-details" open={!compact}>
        <summary>地域別の数値と集計条件</summary>
        <dl className="origin-coverage">
          {(
            [
              ["確認済み来訪者", value.total_visitors],
              ["地域共有あり", value.consented_visitors],
              ["地域未登録", value.missing_visitors],
              ["地域共有なし", value.withheld_visitors],
              ["少人数で非表示", value.suppressed_visitors],
            ] as const
          ).map(([label, count]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>
                {count === null ? "非表示" : number.format(count)}
                {count !== null && <small>人</small>}
              </dd>
            </div>
          ))}
        </dl>
        <p className="dashboard-muted">
          {"reason" in value
            ? `市全体では、${value.privacy_threshold}人未満の内訳がある場合は地域図全体を非表示にします。`
            : `地域ごとに${value.privacy_threshold}人未満の場合や、再訪の内訳に少人数が含まれる場合は、その地域の名前・位置・人数を表示しません。`}
        </p>
        {"reason" in value && value.reason && (
          <p className="dashboard-muted">{value.reason}</p>
        )}
        {value.areas.length > 0 && (
          <div className="dashboard-table-wrap">
            <table className="origin-table">
              <caption>地域名を選ぶと、地図上の位置を強調します。</caption>
              <thead>
                <tr>
                  <th scope="col">居住地域</th>
                  <th scope="col">来訪者</th>
                  <th scope="col">再訪者</th>
                </tr>
              </thead>
              <tbody>
                {value.areas.map((area) => (
                  <tr
                    key={area.id}
                    className={area.id === selectedId ? "selected" : ""}
                  >
                    <th scope="row">
                      <button
                        className="text-button"
                        aria-pressed={area.id === selectedId}
                        onClick={() => select(area)}
                      >
                        {area.label}
                      </button>
                    </th>
                    <td>{number.format(area.visitors)}人</td>
                    <td>
                      {area.returning_visitors === null
                        ? "少数のため非表示"
                        : `${number.format(area.returning_visitors)}人`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="dashboard-definitions">
          <p>市区町村の代表地点です。自宅や実際の出発地ではありません。</p>
          <ul>
            {value.definitions.map((definition) => (
              <li key={definition}>{definition}</li>
            ))}
          </ul>
        </div>
      </details>
    </section>
  );
}
