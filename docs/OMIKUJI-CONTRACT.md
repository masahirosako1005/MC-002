# 月1回の現地配布コード式おみくじ

2026-11-10実装。無料・ローカル完結。3箱や視点移動は画面上の演出であり、抽選値はサーバーの `secrets.randbelow(100)` だけが決める。GPS・位置センサーによる現地証明ではない。

## 参加と確率

- 本人は日本時間の暦月ごとに1回、全事業者共通。0円（特典なし）も実施済みに数える。
- 事業者の有効な担当者が店頭等で渡す6桁コードを使う。コードは10分有効で、成功した抽選1回だけに使用できる。
- 階級は日帰りの既存 `Daytrip.rank_states` の **eligible側** を使う。自己申告や相互確認だけの個人ポイントでは、金銭特典の抽選確率を上げない。本人の表示階級 `personal_rank` と特典資格階級 `rank` は別々に返す。

| 特典資格階級 | 特典なし | 100円引き | 200円引き | 300円引き |
|---|---:|---:|---:|---:|
| 1〜3 | 50% | 40% | 10% | 0% |
| 4〜6 | 30% | 40% | 25% | 5% |
| 7〜10 | 10% | 30% | 40% | 20% |

## 事業者の同意・予算・利用

初期設定は無効・予算0円。種データや起動で自動有効化しない。担当者は明示的に有効化し、月予算を300〜10,000円に設定する。予算は当月の発行額を確保し、既発行額未満には下げられない。最大当選額300円に満たない残予算ではコード発行と抽選を開始しない。抽選結果を出してから金額を減らしたり、予算に合わせて再抽選したりしない。

当選券は発行から30日、その事業者でのみ使用できる。換金・譲渡・他割引併用なし。事業者担当者が実利用額と他割引を併用しないことを確認し、券額面以上の利用額を入力して利用済みにする。外部決済・購入履歴の自動照合は行わない。使用済み・期限切れの利用は409。他社担当者・本人による利用確定は404。受付停止後も既発行券の条件は維持する。

月予算は発行月で計上し、期限切れや利用済みへの変化で当月発行額を減らさない。前月発行券が翌月に使える場合がある。階級・当選額は抽選時の保存結果であり、後日の階級変動で再抽選しない。

## API

すべて `/api` 配下、既存認証・Origin・CSRF・書込レート制限を適用。入力の追加項目を拒否し、予算・利用額は整数、同意はJSON booleanを要求する。

| 操作 | 入力・返却 |
|---|---|
| `GET /omikuji` | `month,can_draw,rank:{level,name},personal_rank:{level,name},odds:[{amount_yen,probability_percent}],draws:[Draw],terms`。`can_draw`は月未実施の意味であり、事業者の受付・予算はコード検証時に別途判定 |
| `POST /omikuji/draw` | `{code,client_request_id}` → `Draw`。codeは6桁、request_idは8〜100文字の英数字・`_`・`-` |
| `GET /omikuji/provider` | `{month,providers:[Policy],rewards:[Reward]}`。現在有効な自社担当者の範囲のみ |
| `PUT /omikuji/provider/policy` | `{provider_id,enabled,monthly_budget_yen,version}` → `Policy`。初回version=0、その後は応答versionを使用。競合409 |
| `POST /omikuji/provider/codes` | `{provider_id}` → `{code,expires_at,provider_id,provider_name}`。コードを表示するのは作成時のみ。GETで再取得しない |
| `POST /omikuji/rewards/{id}/redeem` | `{purchase_yen,no_other_discount:true}` → `Reward` |

`Policy` = `id,name,enabled,monthly_budget_yen,issued_yen,remaining_yen,version`。

`Draw` = `id,provider_id,provider_name,month,amount_yen,rank_level,created_at,reward`。0円のrewardはnull。

`Reward` = `id,provider_id,provider_name,title,amount_yen,status,expires_at,redeemed_at,created_at`。statusは`available / redeemed / expired`。利用者ID・名前・コード・コードhashは公開しない。本人は自分の最大36件、事業者は自社の最大100件の当選券を閲覧する。

同じ本人・client_request_id・codeの再送は同じ保存結果を返す。別codeを同じrequest_idで送ると400。別request_idで当月2回目は409。通信失敗後はGETで実施結果を再取得できる。無効・消費済み・期限切れコードは同じ404メッセージにする。

## 保存と安全策

- `omikuji-schema=1` という独立settings markerで新テーブルを追加する。アプリのPRAGMA user_versionは12のまま。追加DDLとmarkerは同一transaction、未知markerは起動拒否。
- `UNIQUE(user_id,month)`・`UNIQUE(user_id,client_request_id)`・`UNIQUE(code_id)`。`BEGIN IMMEDIATE` 内で資格・予算を確認し、コード消費・抽選・券発行を一括保存する。
- 6桁コードは乱数生成し、protected DB内のランダム鍵を用いたHMAC-SHA256のみ保存する。平文コードは応答1回のみ。コード・鍵をログや分析へ出さない。
- 本人ごとの試行はDBに保存し、同じ1分枠では5回まで。失敗した試行もcommitする。サービス再生成・セッション切替でリセットしない。既存のIP単位書込上限120回/分も維持。専用IP制限は追加していないため、複数アカウント間の試行はこの既存全体上限に依存する。
- 資格実績の取消後に既発行くじを再抽選する仕組みはない。抽選時の資格・当選結果を保存する。実際の現地滞在や決済の証明、再訪効果の実証ではない。

## 検証

対象は `test/backend/test_omikuji.py`。初回10件成功（19.08秒）、strict booleanと追加境界の3件成功（7.99秒、うち1件重複）。計12の独立した試験ケース。月のJST境界・全事業者共通の月制限・同時抽選・同時予算・同時利用、本人/他社/失効担当者、期限、失敗試行の永続化、同key別コード拒否、eligible階級、確率の100個の境界値、移行rollback/再実行と外部キーを確認した。

証拠：`artifacts/omikuji/pytest.xml`、`final-tests.xml`、`verification.json`。新omikujiモジュール限定のRuff/C901/Banditは各0。既存アプリ全体の指摘0や全回帰成功を意味しない。実画面の操作・DBバックアップ・コンテナ検証は主担当が別途担当する。
