import type { Distribution } from "./provider-analytics-types";
const number = new Intl.NumberFormat("ja-JP");
export default function Breakdown({ value }: { value: Distribution }) {
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
