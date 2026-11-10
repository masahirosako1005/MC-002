# 講 — 最新の発表資料と原稿

PR03：入口は「旅行の準備に使うサービスがバラバラ」に絞る。Instagramで探す、LINEで相談、楽天トラベルで宿を予約する、の3つだけを示す。「再訪を気軽にするには準備の流れを途切れさせない」→「講で仲間探しから事業者への相談までをつなぐ」という順で提案理由を説明する。これは設計上の狙いであり、再訪効果の実測結果ではない。

今回の簡素化と接続の確認：[PR03検証記録](../artifacts/presentation-html/v3/verification.json)。入口を2つのPC幅で確認し、原稿と260秒の配分を照合済み。以下のPR02記録は前構成の検証として保持する。

2026-11-10、PR03改訂。**最新の発表入口は9枚のHTML資料と日本語原稿**です。実装・検証の最終章40秒を外し、その時間を導入へ移し、問題提起25秒→本質課題15秒→講の提案20秒の3枚へ分離しました。本文はメイリオ、和の見出し、実際の画面と第13版動画を組み合わせています。資料の作成と、登壇者による通し練習・時間内の発表成功は別です。実際の通し練習は未確認です。

- [発表用HTML](kou-presentation.html)
- [登壇者の原稿](speaker-script.txt)
- [スライド本文・時間配分](presentation-content.js)
- [紹介動画・第13版](../outputs/kou-revisit-intro-v13.mp4)／[字幕](../outputs/kou-revisit-intro-v13-ja.vtt)

## 開き方と操作

プロジェクトのルート `C:/AI-Sprint/workspace/MC-002` で起動します。

```powershell
python scripts/serve_presentation.py
```

表示先：[http://127.0.0.1:8093/presentation/kou-presentation.html](http://127.0.0.1:8093/presentation/kou-presentation.html)。公開用の資料・動画・画像だけを、同じPCから参照するサーバーです。

| 操作 | キー・ボタン |
|---|---|
| 前／次のスライド | ←／→ |
| 発表原稿の表示／非表示 | N |
| 全画面の切替 | F |
| 最初／最後のスライド | Home／End |
| 経過時間 | 「計時開始」、停止、リセット |

動画は**5枚目**で手動再生し、再生後に次へ進みます。ページを離れると動画を一時停止します。PR02の表示・操作結果は [第2構成の検証記録](../artifacts/presentation-html/v2/verification.json) に保存しました。[前構成の検証記録](../artifacts/presentation-html/verification.json)は保持し、新構成の成功へ流用しません。通常の発表用ブラウザーでの全画面操作、印刷出力、人による通し練習は別途確認してください。

## 時間配分と説明の範囲

全体は**4分20秒（260秒）を目標、4分30秒（270秒）を上限**とし、10秒の余裕を設けています。登壇者の原稿175秒＋動画枠85秒。動画本体77.9秒以外の約7秒は、再生開始とスライド切替に使います。話す速さ・操作・待ち時間を含む実際の所要時間は、通し練習で確認してください。

| 枚 | 時間 | 内容 |
|---|---|---|
| 1 | 0:00–0:25（25秒） | 問題提起：旅行の準備、使うサービスがバラバラ。 |
| 2 | 0:25–0:40（15秒） | 本質課題：再訪を気軽にするには、準備をひと続きに |
| 3 | 0:40–1:00（20秒） | 講の提案 — 「仲間探しから事業者への相談まで、一つの「講」で。」 |
| 4 | 1:00–1:20（20秒） | 良かった点のデータと着目点 |
| 5 | 1:20–2:45（85秒） | 第13版動画77.9秒と再生・切替 |
| 6 | 2:45–3:10（25秒） | 再訪策1：通う旅 |
| 7 | 3:10–3:35（25秒） | 再訪策2：先達への追加ポイント |
| 8 | 3:35–4:00（25秒） | 再訪策3：20〜40kmへの追加割引 |
| 9 | 4:00–4:20（20秒） | 事業者の価値と締め |

導入の「Instagramで行き先探し→LINEで相談→楽天トラベルで宿の予約」は、準備が複数の場所へ分かれる**場面例**です。頻度・負担・因果効果を測った結果ではなく、講にSNSとの実連携や予約代行が実装されているという説明でもありません。事業者の承諾後に共有相談し、予約確定は別である境界を維持します。

提供サンプルの良かった点は同行・交流69人、自然・景観65人、回答者287人で、講の需要や再訪効果の証明ではありません。案内はローカルの規則・定型処理で、汎用AIの写真認識や正当な評価を実証したとは説明しません。実装・検証章は今回の9枚から外しましたが、EV02・`21eb465`対象版の433試験等の既存評価記録は保持します。再訪効果・割引費用対効果・実利用者評価は未測定です。

## 保存版：現地くじ追加時点の10枚PPTX／PDF

2026-11-10。講・架空都市N西市・再訪3施策を10枚に整理した発表資料です。旧版「湯遊地」の13枚資料とは別です。

**保存済みPPTX/PDFは、対面コード方式の現地くじを追加した時点の版です。後続のカメラ・QR・お地蔵さんのAR体験と、EV02の433試験＋32 subtestsの評価結果は未反映です。** 第9枚はroot-layout-final、第10枚は現地コード発行・当選・利用確認を扱います。最新の実装範囲は[DESIGN](../DESIGN.md)、版を固定した評価は[EV02評価記録](../docs/evaluation-frameworks/EV02-REPORT.md)で確認してください。以下の検証記録は保存済み資料そのものに対応し、最新アプリ全体との内容一致を保証するものではありません。

- [PowerPoint](../outputs/kou-current-20261110.pptx)
- [PDF](../outputs/kou-current-20261110.pdf)
- [全10枚の描画](../artifacts/presentation-current/rendered-omikuji/)
- [構造・文字領域・フォント検証](../artifacts/presentation-current/validation.json)
- [全ページ目視確認](../artifacts/presentation-current/VISUAL-QA.json)

講の意味、データの限界、3役、利用者・事業者の実画面、通う旅、先達加点、20〜40km地域への追加割引、検証と未測定事項を説明します。保存済み実操作・実画面を使用し、架空初期データを実再訪の成果として扱いません。本文はメイリオ、表と文字は編集可能。AIはMOCで実推論なしです。

測定基準は root-layout-final。363試験＋32 subtests成功、Ruff0、Oxlint115、Stylelint126、複雑度14、Bandit Medium19／High0。満点や認証に読み替えません。未コミット差分を含む作業ツリーでの測定であり、単独コミットの評価ではありません。

第10枚は現地の月替わりくじを追加済みです。追加対象12試験と、現地コード発行→100円当選の保存→500円購入確認での消込→本人再表示で利用済み、を確認しました。対面配布コードはGPS証明ではありません。方向センサー・ゴーグルの実機、再訪効果は未検証です。統合363試験＋32 subtestsは追加前の測定と分けています。

### 保存版PPTX／PDFの再生成

scripts/build_current_presentation.mjs がCodex同梱Artifact ToolでPPTXを作成し、構造・文字領域・フォント・再読込を検証。scripts/build_current_presentation.ps1 が既設PowerPointで読み取り専用に開き、全10PNGとPDFを出力します。外部へアップロードしません。

```powershell
node scripts/build_current_presentation.mjs
& scripts/build_current_presentation.ps1
```

環境が変わる場合は KOU_BUNDLED_RUNTIME と KOU_PRESENTATIONS_SKILL を設定してください。最終PPTX/PDFを上書きしないため、改訂時は出力名を新しくしてください。素材出典とhashは [provenance.json](assets/current/provenance.json)、文書・証拠hashは [content-manifest.json](../artifacts/presentation-current/content-manifest.json) に保存しています。

### 保存版の履歴

月くじ追加前の10枚版は artifacts/presentation-current/before-omikuji.* に保持。旧版は [outputs/history/presentation](../outputs/history/presentation/) に保持。現行機能や評価として引用しません。最初の画像埋込欠落案は artifacts/presentation-current/rejected-missing-media.* として分離し、採用版は画像バイトの存在とPowerPoint全ページ描画を確認しました。
