import { useEffect, useState } from "react";
import { api } from "./api";
import type { PublicExperienceSummary } from "./reflection-types";
import "./reflections.css";

export function ExperienceReference({
  summary,
}: {
  summary: PublicExperienceSummary;
}) {
  return (
    <section
      className="experience-reference"
      aria-label="利用した旅からの参考情報"
    >
      <p className="small-label">利用した旅からの参考情報</p>
      {summary.status === "available" ? (
        <>
          <p>{summary.trip_count}件の旅からまとめた参考集計</p>
          <ul>
            {summary.facets.map((facet) => (
              <li key={facet.aspect_id}>
                <strong>{facet.label}</strong>
                <span>{facet.summary}</span>
                {facet.trip_count !== null && (
                  <small>{facet.trip_count}件の旅</small>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p>
          公開できる参考情報はまだありません。未評価や少数の感想を、低い評価として扱うことはありません。
        </p>
      )}
      <details>
        <summary>まとめ方とおすすめへの使い方</summary>
        <p>{summary.note}</p>
        <p>
          同意した旅行後の振り返りを、限られた言葉の規則で整理しています。原文や個人名は公開しません。希望との関連度が同じ候補では、この参考情報を順番の補助に使います。
        </p>
      </details>
    </section>
  );
}

export default function ProviderExperience({
  providerId,
}: {
  providerId: string;
}) {
  const [data, setData] = useState<PublicExperienceSummary | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    setData(null);
    setFailed(false);
    api<PublicExperienceSummary>(`/providers/${providerId}/experience-summary`)
      .then((result) => {
        if (active) setData(result);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [providerId]);
  return data ? (
    <ExperienceReference summary={data} />
  ) : (
    <p className="reflection-note" role="status">
      {failed
        ? "参考情報を読み込めませんでした。詳細をひらき直すと再確認できます。"
        : "利用した旅からの参考情報を確認しています…"}
    </p>
  );
}
