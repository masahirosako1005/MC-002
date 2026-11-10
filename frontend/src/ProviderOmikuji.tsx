import { useEffect, useId, useState } from "react";
import { api } from "./api";
import { ErrorBox } from "./ui";
import { errorMessage } from "./validation";
import "./provider-omikuji.css";

type Shop = { id: string; name: string; enabled: boolean; monthly_budget_yen: number; issued_yen: number; remaining_yen: number; version: number };
type Reward = { id: string; provider_id: string; provider_name: string; amount_yen: number; status: "available" | "redeemed" | "expired"; expires_at: string; created_at: string };
type Overview = { month: string; providers: Shop[]; rewards: Reward[] };
type Code = { code: string; expires_at: string; provider_name: string };
const yen = (n: number) => `${n.toLocaleString("ja-JP")}円`;
const date = (s: string) => new Date(s).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });

function ShopPanel({ shop, refresh }: { shop: Shop; refresh: () => Promise<void> }) {
  const [enabled, setEnabled] = useState(shop.enabled);
  const [budget, setBudget] = useState(String(shop.monthly_budget_yen || 3000));
  const [code, setCode] = useState<Code | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const id = useId();
  async function run(action: "policy" | "code") {
    if (busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      if (action === "policy") {
        await api("/omikuji/provider/policy", "PUT", { provider_id: shop.id, enabled, monthly_budget_yen: Number(budget), version: shop.version });
        setNotice("予算と受付状態を保存しました。");
        setCode(null);
      } else {
        setCode(await api<Code>("/omikuji/provider/codes", "POST", { provider_id: shop.id }));
      }
      await refresh();
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <article className="omikuji-shop">
    <div className="omikuji-shop-heading"><h2>{shop.name}</h2><span>{shop.enabled ? "受付中" : "停止中"}</span></div>
    <dl className="omikuji-budget"><div><dt>月の予算</dt><dd>{yen(shop.monthly_budget_yen)}</dd></div><div><dt>発行した特典</dt><dd>{yen(shop.issued_yen)}</dd></div><div><dt>残り</dt><dd>{yen(shop.remaining_yen)}</dd></div></dl>
    <form onSubmit={(e) => { e.preventDefault(); void run("policy"); }}>
      <label className="omikuji-toggle"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} disabled={busy} />現地おみくじを受け付ける</label>
      <label htmlFor={`${id}-budget`}>今月の割引予算（円）</label>
      <div className="omikuji-budget-input"><input id={`${id}-budget`} type="number" min={enabled ? 300 : 0} max={10000} step={1} value={budget} onChange={(e) => setBudget(e.target.value)} required disabled={busy} /><button className="button primary" disabled={busy}>設定を保存</button></div>
    </form>
    <p>上限10,000円。券面額を発行時に確保します。残り300円未満では受付を止めます。</p>
    <button className="button" type="button" disabled={busy || !shop.enabled || shop.remaining_yen < 300} onClick={() => void run("code")}>来訪者に渡すコードを発行</button>
    {code && <output className="omikuji-code"><span>{code.provider_name} · 現地確認コード</span><strong>{code.code}</strong><span>{date(code.expires_at)}まで・一人一回</span><span>来訪した本人にだけお渡しください。画面を離れると再表示できません。</span></output>}
    <output>{notice}</output><ErrorBox message={error} />
  </article>;
}

function RedeemPanel({ reward, refresh }: { reward: Reward; refresh: () => Promise<void> }) {
  const [purchase, setPurchase] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const id = useId();
  async function redeem() {
    if (busy || !confirmed) return;
    setBusy(true); setError("");
    try { await api(`/omikuji/rewards/${reward.id}/redeem`, "POST", { purchase_yen: Number(purchase), no_other_discount: confirmed }); await refresh(); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <article className="omikuji-reward-row"><div><strong>{yen(reward.amount_yen)}割引</strong><p>{reward.provider_name} · {date(reward.expires_at)}まで</p><small>券番号 {reward.id.slice(-8)}</small></div>
    {reward.status === "available" ? <form onSubmit={(e) => { e.preventDefault(); void redeem(); }}><label htmlFor={id}>割引前の購入金額（円）</label><input id={id} type="number" min={reward.amount_yen} step={1} required value={purchase} onChange={(e) => setPurchase(e.target.value)} disabled={busy} /><label className="omikuji-toggle"><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} disabled={busy} />本人の券番号・他の割引との併用なしを確認</label><button className="button" disabled={busy || !confirmed || !purchase}>利用済みにする</button><ErrorBox message={error} /></form> : <span>{reward.status === "redeemed" ? "利用済み" : "期限切れ"}</span>}
  </article>;
}

export default function ProviderOmikuji() {
  const [value, setValue] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  async function refresh() { setValue(await api<Overview>("/omikuji/provider")); }
  useEffect(() => {
    const controller = new AbortController();
    void api<Overview>("/omikuji/provider", "GET", undefined, { signal: controller.signal }).then(setValue).catch((e: unknown) => { if (!controller.signal.aborted) setError(errorMessage(e)); });
    return () => controller.abort();
  }, []);
  return <section className="provider-omikuji"><p className="omikuji-provider-intro">現地で月に一度、階級に応じたくじを引けます。割引は下記の予算内で発行します。</p><ErrorBox message={error} />
    {!value ? error ? <button className="button" onClick={() => { setError(""); void refresh().catch((e: unknown) => setError(errorMessage(e))); }}>もう一度読み込む</button> : <output>受付情報を読み込んでいます…</output> : <><p>{value.month.replace("-", "年")}月の受付</p><div className="omikuji-shops">{value.providers.map((shop) => <ShopPanel key={shop.id} shop={shop} refresh={refresh} />)}</div><h2>発行済みの割引券</h2>{!value.rewards.length ? <p>まだ割引券の発行はありません。</p> : value.rewards.map((reward) => <RedeemPanel key={`${reward.id}-${reward.status}`} reward={reward} refresh={refresh} />)}</>}
  </section>;
}
