# EV02 静的検査の独立読取レビュー

確認日：2026-11-10。対象は `ev02-after`（測定時刻 `2026-11-10T04:58:24.079924+00:00`）の保存済み結果と対応する現在コード。検査の再実行、ソース、検査設定、基準、raw JSON、`scripts/quality_check.py` の変更は行っていない。この文書は検出内容の解釈を補足するもので、公式ゲートの `regression` を成功に書き換えない。

最新値は末尾「ev02-final追補」を参照。after時点の33件の分析を履歴として保持する。

## 結果

rawの**新規33件**は、CSSメッセージ内行番号の移動29件、既存関数の複雑度上昇2件、レート制限値をPWと解釈したB105 1件、新規Omikuji UIのHTML要素選択1件に分類できた。CSS29件は新しいselectorの問題が増えたものではない。ただし複雑度2件は実際に数値が上がっており、単なる行移動として消せない。

| ツール | 固定基準 | EV02直前 | ev02-after | EV02直前から |
| --- | ---: | ---: | ---: | --- |
| Oxlint | 124 | 115 | 82 | -33 |
| Stylelint | 126 | 126 | 115 | -11 |
| Bandit | 19 | 19 | 20 | +1 |
| C901複雑度超過 | 14 | 14 | 14 | 件数は同じ、2関数の値が悪化 |
| Ruff通常規則 | 0 | 0 | 0 | 0 |

固定基準は `daytrip-wa-verified` / `daytrip-final`。`summary.json` のbeforeはこの固定版で、EV02作業開始直前の115件とは違う。124→82と115→82を混同しない。残件は合計231件、raw `new_count=33`、`status=regression`、`tests=not-run`、検査実行errorsは空。`tests=not-run` はこの静的集計処理の区分であり、別のpytest結果を否定/肯定するものではない。

Oxlint/Stylelint/TypeScriptの設定hashとbackend `quality/ruff.toml` のhashはEV02前後で一致した。測定後manifestに載るfrontend/backendの全ファイルは今回の読取時点の現物SHAと一致した。以後の修正、並行チャットの変更、最終コンテナまで同一とする証拠ではない。

## raw新規33件の扱い

| 分類 | 件数 | 根拠 | 処置 |
| --- | ---: | --- | --- |
| CSSの行番号移動 | 29 | specificity 18件、重複selector 11件。file・rule・selector・多重度が従前と一致し、text内の参照行番号だけが変化 | rawは保持。既存CSS負債として追跡し、新規selector問題と区別 |
| 既存関数の複雑度上昇 | 2 | `create_app` 51→52、`SecurityMiddleware.__call__` 19→20、基準はともに10 | 実質的な保守性の悪化として残す。新たな2関数が基準を越えたわけではない |
| B105 | 1 | `RATE_LIMITS={...,"password":5,...}` の整数5は操作回数の上限 | この箇所はhardcoded credentialの誤検出。抑制せず限定理由を記録 |
| ProviderOmikujiの要素選択 | 1 | `role="status"` よりHTML `output`を使う規則 | 実際の新規静的指摘。別機能担当所有のため報告、ここで編集しない |

### 複雑度と修正提案

`backend/app/main.py` の `create_app` はルーター・例外ハンドラー・内部endpointをまとめる既存の大きいfactory。今回Stage再認証のCSRF検証分岐が追加された。`backend/app/security.py` のmiddlewareにはPW変更専用のrate分類が追加された。数値がメッセージの識別子に含まれるため、rawでは旧値を「解消」、新値を「新規」と数える。**関数の同一性を認めても+1の複雑度増加は実在する**。

対応候補は、次の変更単位で認証routerや安全なbody受信/rate分類を独立した小さい関数へ分け、入力・Origin・CSRF・失効・期限の既存試験を維持すること。数値を下げるために保護分岐を削除したり、C901閾値を上げたりしない。現在の限定読取から即時の機能破壊を示す経路は見つからないが、保守性負債は残る。

ProviderOmikujiの1件はHTML意味づけの改善候補であって、これだけで読み上げが不能と実証したわけではない。新Omikujiの権限・抽選・予算・一回性・現地確認の安全性は今回の静的警告の読取範囲外。

## Stylelint29件の同一性確認

`quality_check.findings()` はfileとruleに加えてmessage全体を識別子にする。Stylelintのmessageには `at line N` / `first used at line N` が含まれるため、コード行移動により同じselectorが別の指摘となる。原本を保持したまま、読取計算だけでこの参照行番号を除き、file/rule/messageのCounterを比較した。複雑度の数値はこの計算では除去していない。

この照合をEV02直前および固定基準の双方で行い、CSSの実質新規は0件、raw29件すべてに同じ多重度の従前指摘が対応した。実際のStylelint残件は115件で、`no-descending-specificity` が105→102、`no-duplicate-selectors` が21→13。行番号移動の分類は115件の削除/免除ではない。実ブラウザの見た目・CSS cascadeが全面的に正しいことも証明しない。

## Bandit全20件の限定データフロー確認

既存19件はすべてB608（SQL文字列構築）。それぞれの補間値/連結値の定義と呼出し元を読み、ユーザー入力がSQL構文に直接入る経路をこの19箇所では確認しなかった。値を単に「内部用」と見なして免除したわけではない。固定候補からの識別子選択と、値の `?` バインドを具体的に確認した。

| 指摘箇所（ev02-after時点） | 件数 | SQL構文の由来と利用者入力の扱い |
| --- | ---: | --- |
| `backend/app/main.py:176` | 1 | logoutのtableは `stage_sessions` / `sessions` の2固定値。ヘッダ内容自体をtableへ入れずtoken hashを `?` に束縛 |
| `backend/app/security.py:38` | 1 | 同じ2固定tableを認証方式で選択。Bearer/Cookie tokenはdigest後に `?`、期限も `?` |
| `backend/app/marketplace/service.py:164,169,173,175` | 4 | table/columnは `party_messages,party_id` または `consultation_messages,consultation_id` の2組。router呼出しはscope文字列を固定指定。scope_id、既存result_id、本文、actor、時刻は `?`。先にparty/consultation権限判定 |
| `backend/app/personalization/schema.py:30,34,38,40,44,47,49,53,55,58,61,64` | 12 | `_reset_all` / `_reset_circle` / `_provider_guard` はコード定数。DEFAULT_FILTERSも空値等の固定dictのjsonで、利用者の保存filterではない。migrationが固定DDLを実行。NEW/OLDのDB列をPythonでSQL文字列へ補間しない |
| `backend/app/service.py:33` | 1 | `cid` の有無で固定 `AND community_id=?` を足すだけ。uid/cidの実値はタプルで束縛 |
| `backend/app/security.py:16` B105 | 1 | `password` は操作種別キー、5は60秒window内の最大回数。`rate_allowed` は回数比較に使う。PW保存/照合やtoken生成に渡さない |

この結果から上記B105は誤検出、B608は固定構文組立による指摘として限定的に説明できる。すべてのSQLを動的攻撃で検査した、認可やデータ整合性も全面保証した、Banditが見つけない脆弱性もない、という結論ではない。`# nosec`、ツール無効化、基準更新でraw件数を隠す変更はしていない。

この読取では修正が必要な注入経路・hardcoded credentialの実害を新たに確認していない。継続課題は新規UI要素選択1件、複雑度の実増分2件、既存CSS/React警告の残件、実ブラウザ・統合検証の証拠結合。人の理解・満足・再訪効果はこれらの静的件数から評価しない。

## 行番号対応と原本識別

以下はEV02直前の解消扱い行と今回の新規扱い行を、file/rule/selectorの同一性と多重度で対応させた記録。行番号は警告文中の比較相手selectorまたは最初の出現の参照行であり、警告の発生箇所そのものとは限らない。

| file / rule | selector | 従前参照行 | 今回参照行 |
| --- | --- | ---: | ---: |
| `src/marketplace.css` / `no-descending-specificity` | `.choice-trigger > span / .consultation-row > span:nth-child(2)` | 508 | 481 |
| `src/marketplace.css` / `no-descending-specificity` | `.consultation-context > p / .message.mine p` | 379 | 352 |
| `src/marketplace.css` / `no-descending-specificity` | `.market-plan-card > img / .market-plan-card.featured > img` | 757 | 730 |
| `src/marketplace.css` / `no-descending-specificity` | `.market-plan-copy h3 / .market-plan-card.featured h3` | 180 | 737 |
| `src/marketplace.css` / `no-descending-specificity` | `.market-plan-copy / .market-plan-card.featured .market-plan-copy` | 1085 | 1058 |
| `src/marketplace.css` / `no-descending-specificity` | `.market-plan-copy / .market-plan-card.featured .market-plan-copy` | 174 | 156 |
| `src/marketplace.css` / `no-descending-specificity` | `.market-plan-copy / .market-plan-card.featured .market-plan-copy` | 761 | 734 |
| `src/marketplace.css` / `no-descending-specificity` | `.message-author / .message.mine .message-author` | 354 | 327 |
| `src/marketplace.css` / `no-descending-specificity` | `.mismatch-details > div / .message.mine > div` | 351 | 324 |
| `src/marketplace.css` / `no-descending-specificity` | `.mismatch-details p / .message.mine p` | 379 | 352 |
| `src/marketplace.css` / `no-descending-specificity` | `.plan-detail-action > .button / .provider-workspace .section-title .button` | 1021 | 994 |
| `src/marketplace.css` / `no-descending-specificity` | `.plan-detail-cover img / .market-plan-card.featured > img` | 168 | 150 |
| `src/marketplace.css` / `no-descending-specificity` | `.plan-price > span / .consultation-row > span:nth-child(2)` | 508 | 481 |
| `src/marketplace.css` / `no-descending-specificity` | `.plan-price / .market-plan-card.featured .plan-price` | 183 | 162 |
| `src/marketplace.css` / `no-descending-specificity` | `.plan-schedule > .icon / .travel-search-pill > .icon:first-child` | 911 | 884 |
| `src/marketplace.css` / `no-descending-specificity` | `.privacy-summary p / .message.mine p` | 379 | 352 |
| `src/marketplace.css` / `no-descending-specificity` | `.stop-editor-head > div / .message.mine > div` | 351 | 324 |
| `src/marketplace.css` / `no-descending-specificity` | `.travel-search-pill > span / .consultation-row > span:nth-child(2)` | 508 | 481 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.catalog-switch button` | 114 | 99 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.catalog-switch button.selected` | 123 | 108 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.catalog-switch` | 108 | 93 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.market-discovery-heading` | 93 | 82 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.market-plan-card` | 133 | 118 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.market-plan-card.featured .market-plan-copy` | 174 | 156 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.market-plan-copy h3` | 149 | 131 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.market-tabs` | 68 | 61 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.party-toolbar > .button` | 31 | 27 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.plan-price > span` | 194 | 173 |
| `src/marketplace.css` / `no-duplicate-selectors` | `.plan-price strong` | 190 | 169 |

参照JSONは変更せず、記録作成の前後に同じSHAであることを確認した。

| 原本 | SHA-256 |
| --- | --- |
| `artifacts/quality/ev02-after/summary.json` | `79b21e1acdf228e2e19ac19ba34d05997305b5022c02d7b5c0af12b96352e5d9` |
| `C:/AI-Sprint/workspace/MC-002/artifacts/community/frontend-quality/ev02-before-oxlint.json` | `1a27b56fe60a07cdc37526990ecba69fabd4f0298c20ac3cb37cebfede5bba90` |
| `C:/AI-Sprint/workspace/MC-002/artifacts/community/frontend-quality/ev02-after-oxlint.json` | `23871cad5a7c57634b594a5a5b2efffecf344b01aaae8d30082877ffdd38203d` |
| `C:/AI-Sprint/workspace/MC-002/artifacts/community/frontend-quality/ev02-before-stylelint.json` | `fde781d5ab7208f661eecc58fcc5b78d89ce498d21d351f0b97e877bd180f71b` |
| `C:/AI-Sprint/workspace/MC-002/artifacts/community/frontend-quality/ev02-after-stylelint.json` | `09c78ec84a2543dacdcee9f63745fb8d283ca7f92ea271512b2f31e98ac58c74` |
| `C:/AI-Sprint/workspace/MC-002/artifacts/community/quality/ev02-before/bandit.json` | `198f17935b701d969074c73f889eb34c58b7ca4fa89bbfe8abbe9f171b991774` |
| `C:/AI-Sprint/workspace/MC-002/artifacts/community/quality/ev02-after/bandit.json` | `7a83134169c35685a0968c924343079f5efbfdc6c1a23a18f7df408c5814b0d1` |
| `C:/AI-Sprint/workspace/MC-002/artifacts/community/quality/ev02-before/complexity.json` | `516e0290332476a4d6ec2dcc4c6d4abffcd0fbd29a46107e38daf8ce9236613b` |
| `C:/AI-Sprint/workspace/MC-002/artifacts/community/quality/ev02-after/complexity.json` | `2537237ee2dc9308c1c834d25d78af1b6a69747c911848f5889d3cc073b70ae3` |

## ev02-final追補

最終静的測定：`2026-11-10T05:03:35.038349+00:00`。保存済み `ev02-final` と `ev02-after` のraw findingsを同じ比較関数で読み取り比較した。再測定・抑制・設定変更・原本変更はしていない。

| ツール | ev02-after | ev02-final | afterからの差分 |
| --- | ---: | ---: | ---: |
| Oxlint | 82 | 81 | -1 |
| Stylelint | 115 | 115 | 0 |
| Bandit | 20 | 20 | 0 |
| C901超過関数 | 14 | 14 | 0 |
| Ruff通常規則 | 0 | 0 | 0 |

TypeScriptは終了コード0。after→finalのraw新規指摘は0、解消は `ProviderOmikuji.tsx` の `jsx-a11y(prefer-tag-over-role)` 1件。現在コードで `<output>` への修正を確認した。この新機能の警告修正を本担当のコード変更として計上しない。残件は231→230。

**固定基準からの最終ゲートは引き続き `regression`**。raw新規は33→32で、CSS行番号移動29、既存関数の複雑度実増分2、B105のrate値誤検出1が残る。afterからの新規0を、既存負債の解消や公式ゲート合格に読み替えない。複雑度51→52・19→20は前節の評価を維持する。

final frontend/backend manifestに載る全ファイルのSHAを読取時点の現物と照合し、一致した。after→finalで変わったfrontendソースは `ProviderOmikuji.tsx`、`provider-dashboard.css`、`provider-omikuji.css`。設定hashはafterと同一で、変更による警告除外はない。CSSの変更を静的件数115だけで無影響と断定せず、コントラストの実画面証拠は別のUI記録で確認する。

最終ゲート内の `tests=not-run` は静的測定として保持する。親担当の全体試験は進行中で、この追補から合格とは報告しない。独立したUI after-004は9シナリオ成功、axe5状態で違反0、監視したブラウザ実行エラー/外部リクエスト0。対象と限界はEV02-INDEPENDENT-REVIEW末尾の別追補に記録した。

| 最終原本 | SHA-256 |
| --- | --- |
| `artifacts/quality/ev02-final/summary.json` | `784107a8b55e773788ed9db34d29c51d8706f253c2e80af253527bfdc11cb7e6` |
| `artifacts/community/frontend-quality/ev02-final-manifest.json` | `8ee2f3a4794b20782b02a3ff072db590bc54ccbbbff6fded4543218ca8bd6b04` |
| `artifacts/community/frontend-quality/ev02-final-oxlint.json` | `4cb1965a81108da6dd6f559529e8a3056494f7edf1bb07a9f2afb014b4957124` |
| `artifacts/community/frontend-quality/ev02-final-stylelint.json` | `09c78ec84a2543dacdcee9f63745fb8d283ca7f92ea271512b2f31e98ac58c74` |
| `artifacts/community/quality/ev02-final/bandit.json` | `693c8fe3ebbe08658abf7752f0e5424d6846d92989d7e209cc6164a1e0e05723` |
| `artifacts/community/quality/ev02-final/complexity.json` | `2537237ee2dc9308c1c834d25d78af1b6a69747c911848f5889d3cc073b70ae3` |
| `artifacts/community/quality/ev02-final/summary.json` | `67edb088134303169d94928732440699861146bdf197560531dd5287e95b5459` |
