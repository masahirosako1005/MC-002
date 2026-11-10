# 講 — 現行発表資料

2026-11-10。講・架空都市N西市・再訪3施策を10枚に整理した発表資料です。旧版「湯遊地」の13枚資料とは別です。

- [PowerPoint](../outputs/kou-current-20261110.pptx)
- [PDF](../outputs/kou-current-20261110.pdf)
- [全10枚の描画](../artifacts/presentation-current/rendered-omikuji/)
- [構造・文字領域・フォント検証](../artifacts/presentation-current/validation.json)
- [全ページ目視確認](../artifacts/presentation-current/VISUAL-QA.json)

講の意味、データの限界、3役、利用者・事業者の実画面、通う旅、先達加点、20〜40km地域への追加割引、検証と未測定事項を説明します。保存済み実操作・実画面を使用し、架空初期データを実再訪の成果として扱いません。本文はメイリオ、表と文字は編集可能。AIはMOCで実推論なしです。

測定基準は root-layout-final。363試験＋32 subtests成功、Ruff0、Oxlint115、Stylelint126、複雑度14、Bandit Medium19／High0。満点や認証に読み替えません。未コミット差分を含む作業ツリーでの測定であり、単独コミットの評価ではありません。

第10枚は現地の月替わりくじを追加済みです。追加対象12試験と、現地コード発行→100円当選の保存→500円購入確認での消込→本人再表示で利用済み、を確認しました。対面配布コードはGPS証明ではありません。方向センサー・ゴーグルの実機、再訪効果は未検証です。統合363試験＋32 subtestsは追加前の測定と分けています。

## 再生成

scripts/build_current_presentation.mjs がCodex同梱Artifact ToolでPPTXを作成し、構造・文字領域・フォント・再読込を検証。scripts/build_current_presentation.ps1 が既設PowerPointで読み取り専用に開き、全10PNGとPDFを出力します。外部へアップロードしません。

```powershell
node scripts/build_current_presentation.mjs
& scripts/build_current_presentation.ps1
```

環境が変わる場合は KOU_BUNDLED_RUNTIME と KOU_PRESENTATIONS_SKILL を設定してください。最終PPTX/PDFを上書きしないため、改訂時は出力名を新しくしてください。素材出典とhashは [provenance.json](assets/current/provenance.json)、文書・証拠hashは [content-manifest.json](../artifacts/presentation-current/content-manifest.json) に保存しています。

## 履歴

月くじ追加前の10枚版は artifacts/presentation-current/before-omikuji.* に保持。旧版は [outputs/history/presentation](../outputs/history/presentation/) に保持。現行機能や評価として引用しません。最初の画像埋込欠落案は artifacts/presentation-current/rejected-missing-media.* として分離し、採用版は画像バイトの存在とPowerPoint全ページ描画を確認しました。
