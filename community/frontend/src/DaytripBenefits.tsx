import { useId, useState } from "react";
import Choice from "./Choice";
import type { Benefit, DaytripCatalog, Route } from "./daytrip-types";
import { RANK_NAMES } from "./daytrip-types";
import { Empty, Icon } from "./ui";
import { SealMark } from "./WaArt";

const yen = (value: number) => `${value.toLocaleString("ja-JP")}円`;
const rankLabel = (rank: number) => RANK_NAMES[rank - 1] || RANK_NAMES[0];

export function benefitsForRoute(
  benefits: Benefit[],
  route: Route,
  catalog: DaytripCatalog,
) {
  const plans = new Set(
    catalog.plans
      .filter((plan) => plan.route_id === route.id)
      .map((plan) => plan.plan_id),
  );
  return benefits.filter(
    (item) => item.route_ids?.includes(route.id) || plans.has(item.plan_id),
  );
}

export function BenefitLocation({ benefit }: { benefit: Benefit }) {
  return (
    <div className="benefit-location">
      <p className="benefit-place">
        <Icon name="pin" />
        {benefit.area || "利用場所は対象プランで確認"}
      </p>
      {benefit.provider_name && (
        <p className="benefit-provider">{benefit.provider_name}</p>
      )}
      {benefit.plan_title && (
        <p className="benefit-plan">対象：{benefit.plan_title}</p>
      )}
    </div>
  );
}

export function BenefitTerms({ benefit }: { benefit: Benefit }) {
  const offer = benefit.zone_offer;
  return (
    <>
      {offer && (
        <p className="benefit-zone-rates">
          基本 {offer.base_percent}%{" "}
          <span>対象地域 {offer.target_percent}%</span>
        </p>
      )}
      <p className="benefit-price">
        {benefit.discount_type === "percent"
          ? `${offer?.effective_percent ?? benefit.discount_value}%`
          : yen(benefit.discount_value)}
        <span>{offer ? "あなたの割引率" : "割引"}</span>
        <small>一人あたり・割引上限 {yen(benefit.max_discount_yen)}</small>
      </p>
      {offer && (
        <div className="benefit-zone-summary">
          <p className={offer.eligible ? "benefit-zone-eligible" : ""}>
            {offer.reason}
          </p>
          <p>条件を満たす開催で {yen(offer.discount_yen)}引き</p>
          {!offer.can_reserve && (
            <p className="benefit-budget-unavailable">
              割引予算が不足しているため、現在は確保できません。
            </p>
          )}
          <details>
            <summary>対象地域の判定について</summary>
            {offer.one_way_km !== null && (
              <p>登録地域からの参考距離：片道 {offer.one_way_km}km</p>
            )}
            <p>{offer.distance_note}</p>
            <p>
              地域集計への共有設定とは別に、本人のクーポン条件として判定します。
            </p>
          </details>
        </div>
      )}
      <dl className="benefit-terms">
        <div>
          <dt>対象階級</dt>
          <dd>{rankLabel(benefit.min_rank)}以上</dd>
        </div>
        <div>
          <dt>対象の開催日</dt>
          <dd>
            {benefit.starts_on} 〜 {benefit.ends_on}
          </dd>
        </div>
      </dl>
      <p className="benefit-funding">事業者負担・他の特典との併用不可</p>
      <details className="benefit-conditions">
        <summary>利用条件</summary>
        <p>
          対象プランに参加承諾済みの本人一人分に適用します。事業者負担で、他の特典との併用はできません。
        </p>
        <p>
          利用枠は合計{benefit.max_redemptions}
          件まで。残数と資格は確保時に確認します。クーポンの確保だけでは予約・入金は確定しません。
        </p>
      </details>
    </>
  );
}

export function DaytripBenefits({
  benefits,
  catalog,
  route,
  eligibleRank,
  eligiblePoints,
  busy,
  onSelect,
  onClearRoute,
  onExplore,
}: {
  benefits: Benefit[];
  catalog: DaytripCatalog;
  route: Route | null;
  eligibleRank: number;
  eligiblePoints: number;
  busy: boolean;
  onSelect: (benefit: Benefit) => void;
  onClearRoute: () => void;
  onExplore: () => void;
}) {
  const [level, setLevel] = useState("all");
  const selectId = useId();
  const forPlace = route
    ? benefitsForRoute(benefits, route, catalog)
    : benefits;
  const groups = RANK_NAMES.map((name, index) => ({
    name,
    level: index + 1,
    items: forPlace.filter((item) => item.min_rank === index + 1),
  }));
  const shown = groups.filter(
    (group) =>
      group.items.length > 0 &&
      (level === "all" || String(group.level) === level),
  );
  return (
    <section className="coupon-directory">
      <div className="coupon-qualification">
        <SealMark className="coupon-rank-seal">
          {rankLabel(eligibleRank)}
        </SealMark>
        <div>
          <p>あなたの特典対象階級</p>
          <strong>{rankLabel(eligibleRank)}</strong>
          <small>
            {eligiblePoints > 0
              ? "事業者の利用確認がある活動で判定"
              : "初回の事業者利用確認後に確保できます"}
          </small>
        </div>
      </div>
      {route && (
        <div className="coupon-place-filter">
          <div>
            <span>この場所のクーポン</span>
            <strong>{route.destination}</strong>
          </div>
          <button
            className="text-button"
            onClick={() => {
              setLevel("all");
              onClearRoute();
            }}
          >
            すべて見る
          </button>
        </div>
      )}
      <label className="field coupon-rank-filter" htmlFor={selectId}>
        対象階級から探す
        <Choice
          id={selectId}
          value={level}
          onChange={(event) => setLevel(event.target.value)}
        >
          <option value="all">すべての階級（{forPlace.length}件）</option>
          {groups
            .filter((group) => group.items.length > 0)
            .map((group) => (
              <option key={group.level} value={group.level}>
                {group.name}から（{group.items.length}件）
              </option>
            ))}
        </Choice>
      </label>
      <p className="coupon-count">
        {shown.reduce((total, group) => total + group.items.length, 0)}件 ·
        事業者と対象プランを確認して選べます
      </p>
      {shown.length ? (
        shown.map((group) => (
          <section key={group.level} className="coupon-rank-group">
            <header>
              <h2>{group.name}から</h2>
              <span>{group.items.length}件</span>
            </header>
            {group.items.map((item) => (
              <article key={item.id} className="daytrip-benefit coupon-ticket">
                <BenefitLocation benefit={item} />
                <h3>{item.title}</h3>
                <BenefitTerms benefit={item} />
                <button
                  className="button secondary full"
                  disabled={
                    busy ||
                    item.zone_offer?.can_reserve === false ||
                    eligiblePoints <= 0 ||
                    eligibleRank < item.min_rank
                  }
                  onClick={() => onSelect(item)}
                >
                  {item.zone_offer?.can_reserve === false
                    ? "割引予算が不足しています"
                    : eligiblePoints <= 0
                      ? "事業者の利用確認後に選べます"
                      : eligibleRank < item.min_rank
                        ? `${rankLabel(item.min_rank)}になると選べます`
                        : "対象の開催を選ぶ"}
                  {eligiblePoints > 0 && eligibleRank >= item.min_rank && (
                    <Icon name="arrow" />
                  )}
                </button>
              </article>
            ))}
          </section>
        ))
      ) : (
        <Empty
          title={
            route
              ? "この場所のクーポンはまだありません"
              : "公開中のクーポンはありません"
          }
        >
          <p>事業者が設定すると、利用場所と条件がここに表示されます。</p>
          <button className="button secondary" onClick={onExplore}>
            日帰りの行き先を見る
          </button>
        </Empty>
      )}
    </section>
  );
}
