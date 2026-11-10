# 最新の成果物

更新：2026-11-10。対象は、ルート `backend/`・`frontend/` にある現行の講アプリです。最新動画は **第12版（現地QRの写真読取→お地蔵さん→当選結果を追加）**。第10版・第11版は比較用として保持しています。旧スタンプラリー版の資料や過去の検査結果を、現在の完成度として扱いません。

第13版は制作中です。完成ファイルと検証が揃うまでは第12版を配布し、[制作記録](../docs/REVISIT-VIDEO.md)で状態を分けます。ソースZIPも固定コミットの配布物であり、その後の文書変更を含む最新HEADの複製ではありません。

## 閲覧するもの

| 内容 | 現在の入口 | 状態 |
|---|---|---|
| 現行ソース | [ソースZIP](kou-current-source.zip) / [配布manifest](kou-current-source-manifest.json) | カメラAR修正を含むcommit `b05211c`、446ファイル。稼働DB・バックアップ・導入済み依存は含めない |
| 現行の機能・設計 | [DESIGN](../DESIGN.md) / [起動手順](../README.md) | 仕様・実装範囲・制約の正本 |
| 紹介動画 | [MP4・第12版](kou-revisit-intro-v12.mp4) / [日本語字幕](kou-revisit-intro-v12-ja.vtt) / [再生ページ](video-preview/index.html) | 女性の案内役と音声、70秒。講・事業者・通う旅・月1回のおみくじの実操作を含む |
| 発表資料・2026-11-10版 | [PowerPoint](kou-current-20261110.pptx) / [PDF](kou-current-20261110.pdf) / [制作手順](../presentation/README.md) | 全10枚。月次くじ追加時点の保存資料。後続のカメラAR画面とEV02評価は未反映 |
| 作業と未完了項目 | [TASKS](../TASKS.md) / [チケットボード](project-board.html) | 未確認・未解決事項を含む現在の状態 |
| 最新の全体評価 | [EV02・21eb465](../docs/evaluation-frameworks/EV02-REPORT.md) / [試験XML](../artifacts/quality/ev02-full/tests.xml) / [評価入口](../docs/QUALITY-CURRENT.md) | 433試験＋32細分成功。静的ゲートregressionと残課題を保持。後続AR/QRへ転用しない |

発表資料は [構造・文字領域の検査](../artifacts/presentation-current/validation.json) と [全10枚の描画・目視確認記録](../artifacts/presentation-current/VISUAL-QA.json) に対応する完成ファイルです。実ファイルのハッシュも両記録と照合しました。旧名に `final` とある資料は代用しません。機械向けの入口は [latest.json](latest.json) です。

## 動画の確認範囲

[制作・検証記録](../docs/REVISIT-VIDEO.md) / [第10版までのレビュー履歴](../docs/REVISIT-VIDEO-WA-REVIEW.md) / [最終ファイル検査](../artifacts/video-revisit/v12/final/verification.json) / [出力の検査](../artifacts/video-revisit/v12/final/delivery-checks.json)。完成MP4のSHA-256は検査記録と一致。70秒・2,100フレームの全デコードが記録されています。第12版は[ブラウザーで33.7秒までの部分再生](../artifacts/video-revisit/v12/browser-playback-partial.json)を確認しましたが、章移動が先頭へ戻り、変更場面への移動と全編再生は未確認です。第11版の全編再生記録を第12版の結果として流用しません。

**人による声の自然さ・聞き取りやすさ・面白さの評価、利用者の最終承認は未確認です。** 実操作映像は機能の紹介であり、実際の来訪や再訪効果の実証ではありません。再生ページのMP4と字幕は、両方とも正本とバイト単位のハッシュが一致しています。収録したのはQR写真の読み取り→お地蔵さん表示→実際の100円当選結果です。ライブカメラ映像ではありません。動作センサーやVRヘッドセットの検証は未実施です。現地コード方式をGPSによる現地証明とは扱いません。

## 品質と残る課題

最新の全体評価はEV02・21eb465版。以後のAR/QRは限定検証に分離し、現配信camera=()と物理カメラ未確認を[仕様](../docs/OMIKUJI.md)へ記録しています。

過去の構成移動時の `root-layout-final` 測定は、おみくじ追加前の363試験＋32 subtests・失敗0・エラー0・スキップ0。静的指摘はBandit中19／高0、Ruff 0、C901複雑度14、oxlint 115、stylelint 126。固定基準からの新規指摘0ですが、既存指摘や変更箇所のレビューは残り、結果は `review-required` です。これらは認証・安全性保証・使いやすさの点数ではありません。

動画の最終評価、既存静的指摘、通常Edgeの応答停止、未確認画面の文字拡大、実利用者・再訪効果の評価などは [TASKS](../TASKS.md) と [現行評価](../docs/EVALUATION-COMMUNITY.md) で区別します。発表資料は作成当時の363試験＋32細分と追加おみくじ12ケースを示し、EV02の433件＋32細分やカメラARは未反映です。最新の全体評価と同一の資料ではありません。

おみくじの追加検証は別枠で12ケース成功。最初の分割実行に続き、[最終12ケース通し実行](../artifacts/omikuji/release-tests.xml)も30.647秒・失敗0で成功しました。[対象検証](../artifacts/omikuji/verification.json) / [APIと条件](../docs/OMIKUJI-CONTRACT.md)。新モジュール限定Ruff・C901・Banditは0件。既存363試験へ足して「全体375件通過」とは扱いません。

現行ソースZIPは50,523,357 bytes、SHA-256 `f8b0ee6712ab2007f00fd0899fb4c8e240cf41250dc252059f27a59c2e01cb40`。manifestと実ファイルのハッシュ、446ファイルの名前・サイズ、必須の起動・実装入口を照合しました。DB・バックアップ・秘密名・旧配布物・依存キャッシュに該当する配置名は0件でした。名前と配置による検査はコード全体の秘密情報監査ではありません。

ZIPはコミット `b05211ccfd688886c0ae1e6d0528347a84d779a1` の保存済みソースです。コミットに保存された変更だけを含み、未コミットの作業は混ぜていません。依存は起動手順に従って導入し、稼働データは別途保全します。旧配布ZIPは現行版の代用にしません。

## 補足の分析資料

[旅行データの相関図](community-data-correlations.png) / [属性・活動の集計図](sample-data-trends.png) / [アンケートの集計図](survey-content-trends.png)。[分析条件](../docs/COMMUNITY-SAMPLE-ANALYSIS.md) と [集計の制限](../docs/SAMPLE-DATA-TRENDS.md) を併読してください。開発用の分析であり、現行アプリで発生した事業者実績や再訪効果ではありません。

前の完成版：[第11版MP4（AR修正前）](kou-revisit-intro-v11.mp4) / [第11版字幕](kou-revisit-intro-v11-ja.vtt)。[第10版MP4](kou-revisit-intro-v10.mp4) / [第10版字幕](kou-revisit-intro-v10-ja.vtt)。第11版はAR修正前、第10版はおみくじ追加前の比較・検証用で、今回移動していません。

## 履歴の保管

| 保管場所 | 内容 |
|---|---|
| [history/videos](history/videos/) | 再訪動画v1〜v7・v9、旧字幕、旧20秒動画とポスター。v8は音声比較用で独立MP4はない |
| [history/presentation](history/presentation/) | 旧スタンプラリー版13枚の [PPTX](history/presentation/tang-you-chi-presentation-final.pptx) / [PDF](history/presentation/tang-you-chi-presentation-final.pdf)。現行の講・N西市・通う旅を説明する資料ではない |
| [history/legacy-release](history/legacy-release/) | 旧ソースZIP、Git bundle、当時のrelease manifest。現行ソースの配布物として使わない |
| [history/preview](history/preview/) | 過去版のローカル再生用コピー。現在の再生ページには使わない |

23ファイルを上書き・削除せず移動し、全件のSHA-256が移動前後で一致しています。[移動表](../artifacts/output-history-move-map.json) / [鮮度・参照監査](../artifacts/output-freshness-audit.json)。過去の署名・manifest・検証本文は、その時点の記録として変更していません。そこに残る旧パスは移動表で現在位置を確認します。

既存のXML/JSON 23本は過去の検証証拠として元の場所に保持しています。新たな試験結果は `artifacts/`、試験ソースは `test/`。`cleanup-verified-paths.json` は過去の記録であり、削除を再実行するための一覧ではありません。現在のルートbackend/frontendは現行ソースです。
