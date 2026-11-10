# 20〜40km地域の追加割引と有限予算

2026-11-10。本人が登録した市区町村に対する追加率を、事業者が明示設定した割合クーポンにだけ適用する。設定のない既存クーポンは計算式・金額とも変更しない。金額型クーポンにはこの追加率を設定しない。

## 距離と本人の情報

距離版は `n-nishi-reference-2026-11-10-v1`。大阪市32km・吹田市24km・京都市38km・神戸市40km・堺市39kmを固定する。既存カタログの各市代表駅から架空のN西市への計画用参考値であり、住所からの実測、直線距離、確定した交通経路ではない。20km以上40km以下が対象。未登録・未設定地域では基本率を適用する。今後距離値を変える場合は版を更新する必要がある。

住所の市区町村と集計共有同意を分離する。`share_analytics` はこの評価では読まず変更しない。本人の `/daytrip/me` にだけ適用可否・理由・参考距離を返す。事業者のAPIへ本人の市区町村、距離、適用理由を追加しない。事業者には既存の確保金額と、クーポン全体の使用予算を返す。

## 計算と予算

- 適用率 = min(100, 基本率 + 対象本人への追加率)。追加率は percentage points。
- 割引額 = min(一人の対象料金, floor(対象料金×適用率/100), 既存 `max_discount_yen`)。
- `settings` の `daytrip-zone-policy:<benefit_id>` に追加率・予算・距離版を保存。スキーマ追加はない。
- 予算使用額は同クーポンの `reserved` / `redeemed` の `discount_yen` 総計。追加分だけでなく基本分も含み、設定前の確保も含む。
- `BEGIN IMMEDIATE` の確保トランザクション内で再評価・予算確認・保存する。残予算不足は409。基本率への自動切替や部分割引はしない。
- 未利用取消は予算を返す。利用済みは使用額に残す。使用額未満への予算減額は409。既存の回数上限と本人一開催一度の制限も継続する。
- 確保時の適用結果・距離版を `conditions_json.zone_offer` へ保存。住所・共有同意・率・予算の変更で保存済み金額を再計算しない。既存の開催取消・資格根拠取消・プラン変更の保護は維持する。

## API

`PUT /api/daytrip/benefits/{id}/zone-policy` は認証済みの当該事業者スタッフのみ。入力は `{version, additional_percent, budget_yen}`。`version` はクーポン版。追加率0〜100整数、予算1〜100,000,000円整数。公開中の割合クーポン・公開プラン・正規N西経路が必要。成功時クーポン版を加算し `{version,additional_percent,budget_yen,used_yen,remaining_yen,distance_version}` を返す。競合版は409。

`GET /api/daytrip/provider` の各クーポンへ `zone_policy`（未設定null）、`zone_policy_configurable`、`zone_used_yen` を追加。最後の値は未設定の時点でも既存の確保・利用済み総額を示し、初回予算設定の下限に使う。本人の各クーポンへ `zone_offer`（未設定null）を追加する。本人の項目は `eligible,reason,base_percent,effective_percent,target_percent,additional_percent,one_way_km,distance_version,distance_basis,distance_note,discount_yen,can_reserve`。`can_reserve` は予算条件だけを表し、階級・対象開催・期間等は既存条件を別に満たす必要がある。`target_percent` は対象地域に適用される率、`effective_percent` は本人の率。

## 追加データ

`python -m app.zone_benefit_seed --apply` は `app.operational_seed` 適用後、明示実行のみ。`zone26-nnishi-reference` を1件追加し、基本5%＋対象地域5ポイント、上限1,000円、割引総予算12,000円を設定する。既存12件のクーポン・本人住所・同意は変更しない。初期利用者の市区町村が未登録なら基本率のまま。繰り返し適用はmanifestを返すだけで、二重追加しない。実DBへの投入は主担当が行う。

## 検証範囲

専用試験 `test/backend/test_zone_benefits.py` は本人評価・同意独立・設定認可・入力検証・既存金額・上限・確保/取消・住所/政策変更後の保存額・同時申込を扱い、9件成功（15.13秒）。証拠は `artifacts/zone-benefits/pytest.xml`。その後、新API登録を小関数へ移したため認可・入力・既存予算のAPI試験1件を再確認し成功（1.71秒、`artifacts/zone-benefits/router-check.xml`）。

画面との最終照合で、policy初設定時も既存使用額を表示する `zone_used_yen` を補い、同API試験に「未設定でも300円使用済み」を追加して1件成功（1.86秒、`artifacts/zone-benefits/initial-budget-display.xml`）。これ以外の条件や金額計算は変更していない。

今回変更したPython 6ファイルのRuffは0。新規module/seedのBanditは0（`artifacts/zone-benefits/bandit.json`）。同一条件のC901には既存 `daytrip/router.py:create_router` 20、`daytrip/service.py:create` 13が残るが、今回増加はない。新規module/seedにC901はない。独立担当が本人情報の非共有、予算の原子処理、保存金額不変を読取確認し、追加P1/P2指摘なし。全体回帰・実DB投入・実画面検証は主担当の統合結果と区別する。
