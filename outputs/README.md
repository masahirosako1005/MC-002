# 最新の成果物

更新：2026-11-10。対象は、ルート `backend/`・`frontend/` にある現行の講アプリです。最新動画は **第11版（おみくじの実操作を追加）**。第10版は追加前の比較用として保持しています。旧スタンプラリー版の資料や過去の検査結果を、現在の完成度として扱いません。

## 閲覧するもの

| 内容 | 現在の入口 | 状態 |
|---|---|---|
| 現行の機能・設計 | [DESIGN](../DESIGN.md) / [起動手順](../README.md) | 仕様・実装範囲・制約の正本 |
| 紹介動画 | [MP4・第11版](kou-revisit-intro-v11.mp4) / [日本語字幕](kou-revisit-intro-v11-ja.vtt) / [再生ページ](video-preview/index.html) | 女性の案内役と音声、70秒。講・事業者・通う旅・月1回のおみくじの実操作を含む |
| 発表資料・2026-11-10版 | [PowerPoint](kou-current-20261110.pptx) / [PDF](kou-current-20261110.pdf) / [制作手順](../presentation/README.md) | 全10枚。現地くじの当選・事業者利用確認まで反映 |
| 作業と未完了項目 | [TASKS](../TASKS.md) / [チケットボード](project-board.html) | 未確認・未解決事項を含む現在の状態 |
| 最新の品質測定 | [root-layout-final](../artifacts/quality/root-layout-final/REPORT.md) / [機械可読結果](../artifacts/quality/root-layout-final/summary.json) / [試験XML](../artifacts/quality/root-layout-final/tests.xml) | おみくじ追加前の363試験＋32 subtests成功。静的指摘が残り `review-required` |

発表資料は [構造・文字領域の検査](../artifacts/presentation-current/validation.json) と [全10枚の描画・目視確認記録](../artifacts/presentation-current/VISUAL-QA.json) に対応する完成ファイルです。実ファイルのハッシュも両記録と照合しました。旧名に `final` とある資料は代用しません。機械向けの入口は [latest.json](latest.json) です。

## 動画の確認範囲

[制作・検証記録](../docs/REVISIT-VIDEO.md) / [独立レビュー](../docs/REVISIT-VIDEO-WA-REVIEW.md) / [最終ファイル検査](../artifacts/video-revisit/v11/final/verification.json) / [出力の検査](../artifacts/video-revisit/v11/final/delivery-checks.json)。完成MP4のSHA-256は検査記録と一致。70秒・2,100フレームの全デコードが記録されています。[ブラウザー全編再生](../artifacts/video-revisit/v11/browser-playback.json)も主担当が確認し、70秒の終端までエラーなしで完了した記録を照合しました。

**人による声の自然さ・聞き取りやすさ・面白さの評価、利用者の最終承認は未確認です。** 実操作映像は機能の紹介であり、実際の来訪や再訪効果の実証ではありません。再生ページのMP4と字幕は、両方とも正本とバイト単位のハッシュが一致しています。動作センサーやVRヘッドセットの検証は未実施で、収録したのはポインター操作です。現地コード方式をGPSによる現地証明とは扱いません。

## 品質と残る課題

2026-11-10の `root-layout-final` 測定は、おみくじ追加前の363試験＋32 subtests・失敗0・エラー0・スキップ0。静的指摘はBandit中19／高0、Ruff 0、C901複雑度14、oxlint 115、stylelint 126。固定基準からの新規指摘0ですが、既存指摘や変更箇所のレビューは残り、結果は `review-required` です。これらは認証・安全性保証・使いやすさの点数ではありません。

動画の最終評価、既存静的指摘、通常Edgeの応答停止、未確認画面の文字拡大、実利用者・再訪効果の評価などは [TASKS](../TASKS.md) と [現行評価](../docs/EVALUATION-COMMUNITY.md) で区別します。発表資料は既存の363試験＋32 subtestsと、追加のおみくじ12ケースを別の範囲として示しています。

おみくじの追加検証は別枠で12ケース成功（初回10件＋追加3件のうち1件重複）。[対象検証](../artifacts/omikuji/verification.json) / [APIと条件](../docs/OMIKUJI-CONTRACT.md)。新モジュール限定Ruff・C901・Banditは0件。既存363試験へ足して「全体375件通過」とは扱いません。

現行ソース配布ZIPとmanifestは準備中です。完成と検証を確認してから入口へ追加します。旧配布ZIPは代用しません。

## 補足の分析資料

[旅行データの相関図](community-data-correlations.png) / [属性・活動の集計図](sample-data-trends.png) / [アンケートの集計図](survey-content-trends.png)。[分析条件](../docs/COMMUNITY-SAMPLE-ANALYSIS.md) と [集計の制限](../docs/SAMPLE-DATA-TRENDS.md) を併読してください。開発用の分析であり、現行アプリで発生した事業者実績や再訪効果ではありません。

前の完成版：[第10版MP4](kou-revisit-intro-v10.mp4) / [第10版字幕](kou-revisit-intro-v10-ja.vtt)。おみくじ追加前の比較・検証用で、今回移動していません。

## 履歴の保管

| 保管場所 | 内容 |
|---|---|
| [history/videos](history/videos/) | 再訪動画v1〜v7・v9、旧字幕、旧20秒動画とポスター。v8は音声比較用で独立MP4はない |
| [history/presentation](history/presentation/) | 旧スタンプラリー版13枚の [PPTX](history/presentation/tang-you-chi-presentation-final.pptx) / [PDF](history/presentation/tang-you-chi-presentation-final.pdf)。現行の講・N西市・通う旅を説明する資料ではない |
| [history/legacy-release](history/legacy-release/) | 旧ソースZIP、Git bundle、当時のrelease manifest。現行ソースの配布物として使わない |
| [history/preview](history/preview/) | 過去版のローカル再生用コピー。現在の再生ページには使わない |

23ファイルを上書き・削除せず移動し、全件のSHA-256が移動前後で一致しています。[移動表](../artifacts/output-history-move-map.json) / [鮮度・参照監査](../artifacts/output-freshness-audit.json)。過去の署名・manifest・検証本文は、その時点の記録として変更していません。そこに残る旧パスは移動表で現在位置を確認します。

既存のXML/JSON 23本は過去の検証証拠として元の場所に保持しています。新たな試験結果は `artifacts/`、試験ソースは `test/`。`cleanup-verified-paths.json` は過去の記録であり、削除を再実行するための一覧ではありません。現在のルートbackend/frontendは現行ソースです。
