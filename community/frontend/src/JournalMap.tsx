import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { Prefecture, Visit } from "./journal-types";
import japan from "./map-data/japan.json";
import { Icon } from "./ui";
import "./journal-map.css";

type Bounds = [number, number, number, number];
type Scope = "nearby" | "national";
type RecordPoint = {
  visit: Visit;
  latitude: number;
  longitude: number;
  representative: boolean;
};
type Positioned = RecordPoint & { x: number; y: number };
type Cluster = { records: Positioned[]; x: number; y: number };
const NATIONAL: Bounds = [122, 24, 146, 46];
const WIDTH = 420;
const HEIGHT = 300;
const EMPTY_PREFECTURES: Prefecture[] = [];

function recordPoints(
  visits: Visit[],
  prefectures: Prefecture[],
  ownerView: boolean,
): RecordPoint[] {
  const byId = new Map(
    prefectures.map((prefecture) => [prefecture.id, prefecture]),
  );
  return visits.flatMap<RecordPoint>((visit) => {
    // Shared profiles use only the prefecture point, even if an unexpected
    // payload contains coordinates. This does not replace server authorization.
    if (
      ownerView &&
      visit.latitude !== null &&
      visit.longitude !== null &&
      Number.isFinite(visit.latitude) &&
      Number.isFinite(visit.longitude) &&
      Math.abs(visit.latitude) <= 90 &&
      Math.abs(visit.longitude) <= 180
    ) {
      return [
        {
          visit,
          latitude: visit.latitude,
          longitude: visit.longitude,
          representative: false,
        },
      ];
    }
    const prefecture = byId.get(visit.prefecture_id);
    return prefecture
      ? [
          {
            visit,
            latitude: prefecture.latitude,
            longitude: prefecture.longitude,
            representative: true,
          },
        ]
      : [];
  });
}

function nearbyBounds(points: RecordPoint[]): Bounds {
  if (!points.length) return NATIONAL;
  const latitudes = points.map((point) => point.latitude);
  const longitudes = points.map((point) => point.longitude);
  const south = Math.min(...latitudes),
    north = Math.max(...latitudes);
  const west = Math.min(...longitudes),
    east = Math.max(...longitudes);
  const minimum = points.every((point) => point.representative) ? 0.35 : 0.025;
  const latitudeSpan = Math.max(north - south, minimum);
  const longitudeSpan = Math.max(east - west, minimum);
  return [
    Math.max(-180, (west + east) / 2 - longitudeSpan * 0.7),
    Math.max(-90, (south + north) / 2 - latitudeSpan * 0.7),
    Math.min(180, (west + east) / 2 + longitudeSpan * 0.7),
    Math.min(90, (south + north) / 2 + latitudeSpan * 0.7),
  ];
}

function projection(bounds: Bounds) {
  const [west, south, east, north] = bounds;
  const ratio = Math.max(
    0.2,
    Math.cos((((north + south) / 2) * Math.PI) / 180),
  );
  const scale = Math.min(
    (WIDTH - 64) / ((east - west) * ratio),
    (HEIGHT - 64) / (north - south),
  );
  return (latitude: number, longitude: number) => ({
    x: WIDTH / 2 + (longitude - (east + west) / 2) * ratio * scale,
    y: HEIGHT / 2 - (latitude - (north + south) / 2) * scale,
  });
}

function inside(
  point: { latitude: number; longitude: number },
  bounds: Bounds,
) {
  return (
    point.longitude >= bounds[0] &&
    point.longitude <= bounds[2] &&
    point.latitude >= bounds[1] &&
    point.latitude <= bounds[3]
  );
}

function coastPath(project: ReturnType<typeof projection>) {
  return japan.coordinates
    .map((polygon) =>
      polygon
        .map(
          (ring) =>
            ring
              .map(([longitude, latitude], index) => {
                const point = project(latitude, longitude);
                return `${index ? "L" : "M"}${point.x.toFixed(2)},${point.y.toFixed(2)}`;
              })
              .join(" ") + "Z",
        )
        .join(" "),
    )
    .join(" ");
}

function clusters(
  points: Positioned[],
  width: number,
  height: number,
): Cluster[] {
  const groups: Positioned[][] = [];
  for (const point of points) {
    const touching = groups.flatMap((group, index) =>
      group.some(
        (other) =>
          Math.hypot(
            ((point.x - other.x) * width) / WIDTH,
            ((point.y - other.y) * height) / HEIGHT,
          ) < 48,
      )
        ? [index]
        : [],
    );
    if (!touching.length) {
      groups.push([point]);
      continue;
    }
    const joined = [point, ...touching.flatMap((index) => groups[index])];
    for (let index = touching.length - 1; index >= 0; index--)
      groups.splice(touching[index], 1);
    groups.push(joined);
  }
  return groups.map((records) => ({
    records,
    x: records.reduce((sum, record) => sum + record.x, 0) / records.length,
    y: records.reduce((sum, record) => sum + record.y, 0) / records.length,
  }));
}

function useMapSize() {
  const element = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: WIDTH, height: HEIGHT });
  useEffect(() => {
    if (!element.current) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0 && entry.contentRect.height > 0)
        setSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
    });
    observer.observe(element.current);
    return () => observer.disconnect();
  }, []);
  return { element, size };
}

export default function JournalMap({
  prefectures,
  visits,
  selected,
  onSelect,
  visited = EMPTY_PREFECTURES,
  ownerView = false,
}: {
  prefectures: Prefecture[];
  visits: Visit[];
  selected: string;
  onSelect: (id: string) => void;
  visited?: Prefecture[];
  ownerView?: boolean;
}) {
  const [scope, setScope] = useState<Scope>(
    visits.length ? "nearby" : "national",
  );
  const titleId = useId();
  const { element, size } = useMapSize();
  const points = useMemo(
    () => recordPoints(visits, prefectures, ownerView),
    [visits, prefectures, ownerView],
  );
  const bounds = useMemo(
    () => (scope === "nearby" ? nearbyBounds(points) : NATIONAL),
    [scope, points],
  );
  const project = useMemo(() => projection(bounds), [bounds]);
  const land = useMemo(() => coastPath(project), [project]);
  const shown = points
    .filter((point) => inside(point, bounds))
    .map((point) =>
      Object.assign({}, point, project(point.latitude, point.longitude)),
    );
  const groups = clusters(shown, size.width, size.height);
  const selectedPoint = points.find((point) => point.visit.id === selected);
  const selectedGroup = groups.find((group) =>
    group.records.some((point) => point.visit.id === selected),
  );
  const visitedIds = new Set([
    ...visited.map((prefecture) => prefecture.id),
    ...visits.map((visit) => visit.prefecture_id),
  ]);
  const representativeCount = points.filter(
    (point) => point.representative,
  ).length;
  function select(id: string) {
    const point = points.find((item) => item.visit.id === id);
    if (point && !inside(point, bounds)) setScope("nearby");
    onSelect(id);
  }
  return (
    <figure className="journal-map-view" aria-labelledby={titleId}>
      <header className="journal-map-heading">
        <div>
          <h2 id={titleId}>記録した場所</h2>
          <p>
            {visits.length}件の訪問記録 · {visitedIds.size}都道府県
          </p>
        </div>
        <div className="journal-map-scopes" aria-label="地図の表示範囲">
          <button
            type="button"
            aria-pressed={scope === "nearby"}
            disabled={!points.length}
            onClick={() => setScope("nearby")}
          >
            記録周辺
          </button>
          <button
            type="button"
            aria-pressed={scope === "national"}
            onClick={() => setScope("national")}
          >
            全国
          </button>
        </div>
      </header>
      <div className="journal-map-canvas" ref={element}>
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path d={land} className="journal-map-coast" fillRule="evenodd" />
          {prefectures
            .filter((prefecture) => inside(prefecture, bounds))
            .map((prefecture) => {
              const point = project(prefecture.latitude, prefecture.longitude);
              return (
                <g key={prefecture.id}>
                  <circle
                    cx={point.x}
                    cy={point.y}
                    r={visitedIds.has(prefecture.id) ? 4 : 2}
                    className={
                      visitedIds.has(prefecture.id)
                        ? "journal-map-prefecture visited"
                        : "journal-map-prefecture"
                    }
                  />
                  {scope === "nearby" && (
                    <text
                      x={point.x + 7}
                      y={point.y - 7}
                      className="journal-map-area-label"
                    >
                      {prefecture.name}
                    </text>
                  )}
                </g>
              );
            })}
        </svg>
        <span className="journal-map-north" aria-hidden="true">
          ↑ 北
        </span>
        <span className="journal-map-scale-note">
          {scope === "nearby" ? "記録周辺の概略図" : "日本の概略図"}
        </span>
        {groups.map((group) => {
          const first = group.records.reduce((left, right) =>
            left.visit.id.localeCompare(right.visit.id) <= 0 ? left : right,
          );
          const active = group.records.some(
            (point) => point.visit.id === selected,
          );
          const multiple = group.records.length > 1;
          return (
            <button
              type="button"
              key={first.visit.id}
              className={`journal-map-marker ${active ? "selected" : ""} ${multiple ? "cluster" : ""}`}
              style={{
                left: `${(group.x / WIDTH) * 100}%`,
                top: `${(group.y / HEIGHT) * 100}%`,
              }}
              aria-pressed={active}
              aria-label={
                multiple
                  ? `近接する${group.records.length}件の記録。${first.visit.place_label}を選ぶ`
                  : `${first.visit.place_label}、${first.visit.visited_on}、${first.representative ? "県の代表点" : "本人確認した位置"}を選ぶ`
              }
              onClick={() => select(active ? selected : first.visit.id)}
            >
              {multiple ? (
                <span>
                  {group.records.length}
                  <small>件</small>
                </span>
              ) : (
                <Icon name="pin" />
              )}
            </button>
          );
        })}
      </div>
      <figcaption>
        数字は近接する記録の件数です。下の一覧から場所と日付で選べます。県の代表点{" "}
        {representativeCount}件。道路や境界を示す地図ではありません。
        {points.length < visits.length && (
          <span>
            位置を表示できない記録が{visits.length - points.length}件あります。
          </span>
        )}
        {scope === "national" && shown.length < points.length && (
          <span>
            全国図の範囲外に{points.length - shown.length}
            件あります。「記録周辺」か一覧で確認できます。
          </span>
        )}
      </figcaption>
      <div className="journal-map-selection" aria-live="polite">
        {selectedPoint ? (
          <>
            <strong>{selectedPoint.visit.place_label}</strong>
            <span>
              {selectedPoint.visit.visited_on} ·{" "}
              {selectedPoint.visit.prefecture_name} ·{" "}
              {selectedPoint.representative
                ? "県の代表点"
                : "本人が確認した位置"}
            </span>
            {selectedGroup && selectedGroup.records.length > 1 && (
              <small>
                このまとまりに{selectedGroup.records.length}
                件。場所名と日付を一覧で選べます。
              </small>
            )}
          </>
        ) : (
          <span>地図の点や一覧から、振り返る記録を選んでください。</span>
        )}
      </div>
      {visits.length > 0 && (
        <details className="journal-map-records" open>
          <summary>地図と連動する記録一覧（{visits.length}件）</summary>
          <ul>
            {visits.map((visit) => (
              <li key={visit.id}>
                <button
                  type="button"
                  aria-pressed={selected === visit.id}
                  onClick={() => select(visit.id)}
                >
                  <span>
                    <strong>{visit.place_label}</strong>
                    <small>
                      {visit.visited_on} · {visit.prefecture_name}
                    </small>
                  </span>
                  <span className="journal-map-record-position">
                    {ownerView &&
                    visit.latitude !== null &&
                    visit.longitude !== null
                      ? "確認した位置"
                      : "県の代表点"}
                    {selected === visit.id && <Icon name="check" />}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </figure>
  );
}
