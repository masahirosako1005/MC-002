# 最新の成果物

更新：2026-11-10。対象は、ルート `backend/`・`frontend/` にある現行の講アプリです。最新動画は **第13版（ログインから写真・仲間探し・事業者への相談・次回の提案までの操作紹介）**。第12版の現地QR・お地蔵さんを含む構成も比較用に保持しています。旧スタンプラリー版の資料や過去の検査結果を、現在の完成度として扱いません。

最新の発表入口はPR04の [9枚のHTML資料](../presentation/kou-presentation.html) と [登壇者原稿](../presentation/speaker-script.txt)。問題提起→本質課題→講の提案を導入3枚に分け、5枚目に動画を置きます。全体4分20秒を目標、4分30秒を上限とし、登壇者の発話175秒＋動画枠85秒を維持。実際の通し練習は未確認です。旧10枚PPTX/PDFは保存版として維持します。

第13版は77.9秒、8場面。女性の音声をNanamiNeuralへ差し替え、通常速度で会話調の原稿を読みます。実際の操作画面と、その同じ画面の拡大を併用します。[制作記録](../docs/REVISIT-VIDEO.md)に検証範囲を記録しています。ソースZIPは固定コミットの配布物であり、今回の動画制作コードや文書変更を含む最新HEADの複製ではありません。

## 閲覧するもの

| 内容 | 現在の入口 | 状態 |
|---|---|---|
| 現行ソース | [ソースZIP](kou-current-source.zip) / [配布manifest](kou-current-source-manifest.json) | カメラAR修正を含むcommit `b05211c`、446ファイル。稼働DB・バックアップ・導入済み依存は含めない |
| 現行の機能・設計 | [DESIGN](../DESIGN.md) / [起動手順](../README.md) | 仕様・実装範囲・制約の正本 |
| 紹介動画 | [MP4・第13版](kou-revisit-intro-v13.mp4) / [日本語字幕](kou-revisit-intro-v13-ja.vtt) / [再生ページ](video-preview/index.html) | 女性の案内役と新しい声、77.9秒。左右ログイン→写真とタグ→仲間→陶芸のプランと共有相談→振り返り条件→通う旅の誘い |
| 最新の発表資料・原稿 | [HTML・9枚](../presentation/kou-presentation.html) / [登壇原稿](../presentation/speaker-script.txt) / [起動と操作](../presentation/README.md) | 4分20秒目標／4分30秒上限。動画77.9秒を85秒枠に配置、登壇原稿175秒。通し練習未確認 |
| 保存版の発表資料 | [PowerPoint](kou-current-20261110.pptx) / [PDF](kou-current-20261110.pdf) | 月次くじ追加時点の10枚。後続のカメラAR画面とEV02評価は未反映。最新HTMLの代用にはしない |
| 作業と未完了項目 | [TASKS](../TASKS.md) / [チケットボード](project-board.html) | 未確認・未解決事項を含む現在の状態 |
| 最新の全体評価 | [EV02・21eb465](../docs/evaluation-frameworks/EV02-REPORT.md) / [試験XML](../artifacts/quality/ev02-full/tests.xml) / [評価入口](../docs/QUALITY-CURRENT.md) | 433試験＋32細分成功。静的ゲートregressionと残課題を保持。後続AR/QRへ転用しない |

保存版PPTX/PDFは [構造・文字領域の検査](../artifacts/presentation-current/validation.json) と [全10枚の描画・目視確認記録](../artifacts/presentation-current/VISUAL-QA.json) に対応するファイルです。この記録を最新HTMLの検証結果として流用しません。旧名に `final` とある資料も代用しません。機械向けの入口は [latest.json](latest.json) です。

## 発表を開く

プロジェクトルートで `python scripts/serve_presentation.py` を実行し、[発表ページ](http://127.0.0.1:8093/presentation/kou-presentation.html)を開きます。←／→でページ移動、Nで原稿、Fで全画面。「計時開始」で経過時間を確認し、5枚目の動画は梅木が手動再生します。

| 担当 | 枚・時間帯 | 読み上げと操作 |
|---|---|---|
| 野村 | 1–2枚：0:00–0:40／9枚：4:00–4:20 | 導入・本質課題40秒と、事業者の価値・締め20秒。発話計60秒 |
| 梅木 | 3–5枚：0:40–2:45 | 講・データの発話40秒。5枚目は動画枠85秒で読み上げず、再生・切替を操作 |
| 樋口 | 6–8枚：2:45–4:00 | 通う旅・先達・距離割引を各25秒。発話計75秒 |

**交代は2→3枚目（0:40）で野村→梅木、5→6枚目（2:45・動画後）で梅木→樋口、8→9枚目（4:00）で樋口→野村。** 順番は野村→梅木→樋口と進み、締めだけ野村へ戻ります。原稿本文を読み上げ、再生・ページ送り・交代の操作指示は読み上げません。

時間配分は問題提起25秒→本質課題15秒→講の提案20秒→データ20秒→動画85秒→再訪3策各25秒→事業者と締め20秒。[詳細タイムテーブル](../presentation/README.md)を参照してください。4分20秒は計画値で、話す速さ・交代・切替を含む実測ではありません。導入のInstagramで探す→LINEで相談→楽天トラベルで予約する流れは場面例であり、準備負担の因果実証やSNS実連携・予約代行を示しません。

今回の表示・操作検証は [PR04検証記録](../artifacts/presentation-html/v4/verification.json) へ記録しました。[PR03検証記録](../artifacts/presentation-html/v3/verification.json)は前版の保存記録とし、新版の確認済み事項へ流用しません。過去の改訂は [変更履歴](../docs/CHANGELOG.md) を参照してください。

## 動画の確認範囲

[制作・検証記録](../docs/REVISIT-VIDEO.md) / [最終ファイル検査](../artifacts/video-revisit/v13/final/verification.json) / [出力の検査](../artifacts/video-revisit/v13/final/delivery-checks.json)。77.9秒・2,337フレームの全デコードが成功。最終音声は−18.0 LUFS、真のピーク−7.5 dBFS。音量のみ調整し、音声の早回し・切り落とし・BGM追加は行っていません。ブラウザーの確認結果は[第13版の再生記録](../artifacts/video-revisit/v13/browser-playback.json)を参照し、過去版の結果を流用しません。

**人による声の自然さ・暖かさ・聞き取りやすさの評価、利用者の最終承認は未確認です。** 実操作映像は機能の紹介であり、実際の来訪や再訪効果の実証ではありません。写真タグは登録サンプルの候補を本人が確認し、関心の利用も本人が許可します。通常チャットの自動評価ではなく、専用の振り返りの同意条件を紹介しています。集計完了は今回実演していません。陶芸プランにカフェの写真・タグが残る元データの不一致は、動画で実画面を書き換えず残課題として記録しています。

音声生成時は公開用の紹介原稿だけを送信しました。アプリの実行方式はローカルMOCのままで、会話・写真・CSV・コード・秘密情報の外部送信はありません。従来の現地QR写真読取→お地蔵さん→当選結果は[第12版](kou-revisit-intro-v12.mp4)に保持しています。ライブカメラやGPSによる現地証明は検証済みとしません。

## 品質と残る課題

最新の全体評価はEV02・21eb465版。以後のAR/QRは限定検証に分離し、現配信camera=()と物理カメラ未確認を[仕様](../docs/OMIKUJI.md)へ記録しています。

過去の構成移動時の `root-layout-final` 測定は、おみくじ追加前の363試験＋32 subtests・失敗0・エラー0・スキップ0。静的指摘はBandit中19／高0、Ruff 0、C901複雑度14、oxlint 115、stylelint 126。固定基準からの新規指摘0ですが、既存指摘や変更箇所のレビューは残り、結果は `review-required` です。これらは認証・安全性保証・使いやすさの点数ではありません。

動画の最終評価、既存静的指摘、通常Edgeの応答停止、未確認画面の文字拡大、実利用者・再訪効果の評価などは [TASKS](../TASKS.md) と [現行評価](../docs/EVALUATION-COMMUNITY.md) で区別します。PR04の最新HTMLに実装・検証章は含めませんが、EV02対象版の433試験等の評価記録は保持しています。保存版PPTX/PDFは作成当時の363試験＋32細分と追加おみくじ12ケースを示し、EV02やカメラARは未反映です。両資料を同じ評価時点として扱いません。

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
