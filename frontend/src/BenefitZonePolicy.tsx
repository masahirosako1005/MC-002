import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import type { Benefit, ZonePolicy } from "./daytrip-types";
import { ErrorBox, Icon, Modal } from "./ui";
import { errorMessage } from "./validation";
import "./benefit-zone.css";

const yen = (value: number) => `${value.toLocaleString("ja-JP")}円`;
function PolicyForm({
  benefit,
  onClose,
  onSaved,
  onRefresh,
}: {
  benefit: Benefit;
  onClose: () => void;
  onSaved: () => void;
  onRefresh: () => void;
}) {
  const [additional, setAdditional] = useState(
    String(benefit.zone_policy?.additional_percent ?? 0),
  );
  const [budget, setBudget] = useState(
    benefit.zone_policy ? String(benefit.zone_policy.budget_yen) : "",
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const lock = useRef(false);
  useEffect(() => {
    const request = new AbortController();
    controller.current = request;
    return () => request.abort();
  }, []);
  const usedYen = benefit.zone_policy?.used_yen ?? benefit.zone_used_yen ?? 0;
  const minimum = Math.max(1, usedYen);
  const extra = Number(additional),
    total = Number(budget);
  const valid =
    additional.trim() !== "" &&
    budget.trim() !== "" &&
    Number.isInteger(extra) &&
    extra >= 0 &&
    extra <= 100 &&
    Number.isInteger(total) &&
    total >= minimum &&
    total <= 100000000;
  async function save() {
    if (
      !valid ||
      lock.current ||
      !controller.current ||
      controller.current.signal.aborted
    )
      return;
    const request = controller.current;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      await api<ZonePolicy & { version: number }>(
        `/daytrip/benefits/${encodeURIComponent(benefit.id)}/zone-policy`,
        "PUT",
        {
          version: benefit.version,
          additional_percent: extra,
          budget_yen: total,
        },
        { signal: request.signal },
      );
      if (!request.signal.aborted) onSaved();
    } catch (cause) {
      if (!request.signal.aborted) {
        setError(errorMessage(cause));
        setConflict(cause instanceof ApiError && cause.status === 409);
      }
    } finally {
      lock.current = false;
      if (!request.signal.aborted) setBusy(false);
    }
  }
  return (
    <Modal title="対象地域の追加率と割引予算" busy={busy} onClose={onClose}>
      <form
        className="zone-policy-form"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <p>{benefit.title}</p>
        <p className="quiet-note">
          登録地域からN西市への参考距離が片道20〜40kmの人に適用します。本人の市区町村は事業者に表示しません。
        </p>
        <ErrorBox message={error} />
        <fieldset disabled={busy || conflict}>
          <label className="field" htmlFor="zone-extra">
            追加する割引率（%）
            <input
              id="zone-extra"
              type="number"
              inputMode="numeric"
              min={0}
              max={100}
              step={1}
              value={additional}
              onChange={(event) => setAdditional(event.target.value)}
              required
            />
          </label>
          <p className="zone-rate-preview">
            基本 {benefit.discount_value}% → 対象地域{" "}
            {Number.isFinite(extra)
              ? Math.min(100, benefit.discount_value + Math.max(0, extra))
              : benefit.discount_value}
            %<span>割引上限 {yen(benefit.max_discount_yen)} / 一人</span>
          </p>
          <label className="field" htmlFor="zone-budget">
            割引予算の総額（円）
            <input
              id="zone-budget"
              type="number"
              inputMode="numeric"
              min={minimum}
              max={100000000}
              step={1}
              value={budget}
              onChange={(event) => setBudget(event.target.value)}
              required
            />
          </label>
          <p className="quiet-note">
            確保・利用済み {yen(usedYen)}
            以上を設定します。基本分を含む割引総額を計上し、予算を超える新しい確保を止めます。
          </p>
          <button className="button primary full" disabled={!valid}>
            {busy ? "保存しています…" : "事業者負担の条件を保存"}
          </button>
        </fieldset>
        {conflict && (
          <button
            type="button"
            className="button secondary full"
            onClick={onRefresh}
          >
            最新の予算を読み直す
          </button>
        )}
        <p className="quiet-note">
          確保の取消分は残額に戻ります。追加率を0にしても予算上限は有効です。交通の実測値や自宅からの距離を保証する設定ではありません。
        </p>
      </form>
    </Modal>
  );
}

export default function BenefitZonePolicy({
  benefit,
  disabled,
  onSaved,
  onRefresh,
}: {
  benefit: Benefit;
  disabled: boolean;
  onSaved: () => void;
  onRefresh: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const policy = benefit.zone_policy;
  if (!policy && !benefit.zone_policy_configurable) return null;
  return (
    <section className="zone-budget-panel">
      <header>
        <h4>対象地域の追加割引</h4>
        {policy && <span>基本に +{policy.additional_percent}%</span>}
      </header>
      {policy ? (
        <dl className="zone-budget-totals">
          <div>
            <dt>予算総額</dt>
            <dd>{yen(policy.budget_yen)}</dd>
          </div>
          <div>
            <dt>確保・利用分</dt>
            <dd>{yen(policy.used_yen)}</dd>
          </div>
          <div>
            <dt>残額</dt>
            <dd>{yen(policy.remaining_yen)}</dd>
          </div>
        </dl>
      ) : (
        <p>20〜40kmの対象地域への追加率と、割引予算を設定できます。</p>
      )}
      {benefit.zone_policy_configurable && (
        <button
          className="text-button"
          disabled={disabled}
          onClick={() => setEditing(true)}
        >
          <Icon name="filter" />
          {policy ? "追加率・予算を変更" : "追加率・予算を設定"}
        </button>
      )}
      {editing && (
        <PolicyForm
          benefit={benefit}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onSaved();
          }}
          onRefresh={() => {
            setEditing(false);
            onRefresh();
          }}
        />
      )}
    </section>
  );
}
