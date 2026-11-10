# 現在の品質測定 — root-layout-final

2026-11-10。ルート配置への移動後に保存された測定結果を、実装担当とは別に読み取って整理した。本書作成ではアプリ・DB・既存レポートを変更せず、試験を再実行していない。

**363試験＋32サブテストが成功し、失敗・エラー・スキップは0。静的解析は固定基準に対する新規指摘0だが、既存274件が残り、総合ゲートは `review-required`。** 全面合格、安全性保証、スキルの満点、大会の点数を意味しない。[集約結果](../artifacts/quality/root-layout-final/summary.json)

## 測定した範囲と時点

| 項目 | 確認した事実 |
|---|---|
| 集約日時 | 2026-11-10 13:44:00 JST（04:44:00 UTC） |
| productionの静的解析 | `frontend/src` の67ファイル、`backend/app` の84 Pythonモジュール |
| 動作試験 | `test/backend` と `test/tooling`。API・保存・境界・ツール等の試験であり、ブラウザー操作の一括実行ではない |
| ソース識別 | バックエンド記録のGit HEADは `b55bfb0686b3ede1df697ee1d804f9d62be789a9`、`dirty: true`。対象ファイルのSHA-256を各manifestに保存 |
| 比較元 | フロント `daytrip-wa-verified`、バックエンド `daytrip-final`。比較元の対象は45ファイル・55モジュール |
| 規則 | フロント設定3種のハッシュとバックエンド規則設定のハッシュは比較元と一致 |

根拠：[フロントmanifest](../artifacts/community/frontend-quality/root-layout-final-manifest.json)、[バックエンド測定](../artifacts/community/quality/root-layout-final/summary.json)。測定時の作業ツリーには別チャットの未コミット変更が含まれるため、配置移動コミット単独の検証結果とは扱わない。以後の編集や現在編集中のコードへ、保存時の結果を自動的に引き継がない。

## 試験数・時間・失敗

| 指標 | 結果 |
|---|---:|
| pytestの試験 | 363 passed |
| pytestのサブテスト | 32 subtests passed |
| JUnitの集計 `tests` | 395（上記の合計） |
| JUnitの独立した `testcase` 要素 | 363 |
| 失敗 / エラー / skipped | 0 / 0 / 0 |
| JUnitの経過時間 | 342.657秒（5分42.657秒） |
| pytestログの丸め表示 | 342.66秒 |

[試験ログ](../artifacts/quality/root-layout-final/tests.log)と[JUnit XML](../artifacts/quality/root-layout-final/tests.xml)を照合した。「独立した395試験」とは表現しない。時間はpytest実行の経過時間で、静的解析やDockerビルドを含む作業全体の時間ではない。この実行にスキップはなく、旧版の実モデル試験のスキップ記録とは別の測定である。

実行中に、別チャットとのpytest一時領域の共有問題が見つかった。後続修正では `test/fixtures/runtime/quality-<phase>-<uuid>/` の下で一時領域とキャッシュを分けた。この変更は別の[対象13試験](../artifacts/quality-test-isolation-final-tests.xml)が0.24秒で成功している。上記363試験へ遡及して含めず、件数も合算しない。

## 静的解析の比較

| ツール・指標 | 固定比較元 | 今回 | 差分 |
|---|---:|---:|---:|
| TypeScript型エラー | 0 | 0 | 0 |
| Ruff | 0 | 0 | 0 |
| Oxlint | 124 | 115 | −9 |
| Stylelint | 126 | 126 | 0 |
| 複雑度 C901 | 14 | 14 | 0 |
| Bandit | 19 | 19 | 0 |
| 上記lint・複雑度・Banditの残件合計 | 283 | 274 | −9 |

BanditはMedium 19 / High 0、走査エラー0。19件という検出数を、確定した脆弱性19件や安全性の得点へ読み替えない。Ruff・型検査の0も、他の解析や実操作を代替しない。[生結果の概要](../artifacts/community/quality/root-layout-final/summary.json)

新規0・解消9はファイル・規則・メッセージの比較結果。解消9件はApp 3、Composer 1、Journal 1、ProviderWorkspace 4。以前の直前比較 `119→115` は別の基準であり、今回の固定比較 `124→115` と混ぜない。対象ファイル数が増えているので、同一母集団の品質改善率としても扱わない。

13ファイルではソースハッシュが変わり、既存指摘が残っている。件数だけでは同種の問題の置換を判別できないため `review-required` のままにしている。フロントのOxlint exit 1 / Stylelint exit 2、バックエンドの複雑度・Bandit exit 1は指摘を含む完了結果で、集約の実行エラー配列は空。未実行の検査を0件とした結果ではない。

配置変更では、保存済みの `community/backend/app/` と現在の `backend/app/` を、指摘とソースハッシュの比較時だけ同一のファイル識別子へ正規化した。過去のJSONやbaselineを書き換えていない。[参照更新・比較の確認](../artifacts/root-layout-reference-validation.json)

## レビューとの関係

| 範囲 | 根拠と意味 | 今回の数値だけでは確認できないこと |
|---|---|---|
| React / Vite | Vercel React指針を選別適用。型・Oxlintは67ファイルを測定。市集計の範囲切替、取得中断、古い結果の破棄等は[個別レビュー](CITY-ANALYTICS-REVIEW.md)にも記録 | React指針の全項目適合、全導線の速度・使いやすさ、最新編集へのレビュー継承 |
| FastAPI / Python | 入出力検証、認証依存、公開レスポンス、同期DB処理等を指針と契約に沿ってレビュー。今回のAPI試験と84モジュールの静的解析を別の証拠として扱う | 全入力・全競合・全障害の網羅、稼働環境の完全な保証、公開サービス運用の適合 |
| セキュリティ | Banditの生結果を保持し、SQL構築等は[個別トリアージ](DAYTRIP-SECURITY-TRIAGE.md)と[通常実行レビュー](COMMUNITY-RUNTIME-SECURITY-REVIEW.md)で入力経路を確認。認可や地域公開は別の限定レビューを参照 | 未知の攻撃、全依存・全構成の安全性、少人数集計の数学的匿名性 |
| 新しい評価基準 | [EV02独立評価](evaluation-frameworks/EV02-INDEPENDENT-REVIEW.md)と[ASVS台帳](evaluation-frameworks/ASVS-assessment.csv)は、適用・未達・未検証を別管理している | lint新規0をASVS要求の合格に換算すること。EV02の修正候補をこの測定だけで解消済みとすること |

採用元・適用範囲は [SKILL-QUALITY-POLICY.md](SKILL-QUALITY-POLICY.md)、大会8項目への対応は [EVALUATION-TOOLS.md](EVALUATION-TOOLS.md)に従う。スキルは判断の指針であり、自動測定や認証そのものではない。これらの個別レビューは対象版と範囲が限定され、root-layout-finalによる全指針の再レビューを行ったという意味ではない。

## 未検証・別評価

今回の一括実行には、本番ビルド、ブラウザーの全操作、axe、最新主要導線の文字200%、実機・支援技術、負荷測定、coverage、pip-audit/npm auditを含まない。過去の実行結果がある項目でも、今回の結果へ転記しない。ブラウザーの観測・DB/画像の保全・隔離復元・動画の確認は、それぞれの証拠と対象版で評価する。

実利用者の満足度、多様な利用者の完遂率、実際の別日再訪・観光効果、第三者による再現は、この数値からは判断できない。固定評価C1は既存の **40/100を据え置き**、今回の計測による加点は行わない。[評価正本](EVALUATION-COMMUNITY.md)

設計書や紹介資料では、次の要点を使える。「ルート配置移動後の作業ツリーで363試験と32サブテストが成功。型とRuffは0件、固定基準に対する新規の静的指摘は0件。既存274件と未検証の範囲を残し、総合判定は要レビュー。」
