> 履歴資料：本文の制作状況・手順は当時のものです。現行仕様は [設計書](../DESIGN.md)、最新動画は [第10版の記録](../docs/REVISIT-VIDEO.md) を参照してください。旧生成器は撤去済みのため、存在しない再生成手順を実行しないでください。

# プレゼン資料の生成と確認

完成版は `outputs/` のPowerPointファイル。本文・見出し・構成図は編集可能な図形と文字で作成し、アプリの実画面3点は画像として挿入する。収集棚と収集体験の調査を加えた全13枚。外部サービスへのアップロードは行わない。

## 再生成

`build.mjs` はローカルの `@oai/artifact-tool` で作成し、`artifacts/release-metrics.json` から試験数・独自評価・状態を読み込む。`presentation/node_modules` はCodex付属ランタイムへのリンク。再生成にはこのランタイムが必要だが、生成済みPPTXの閲覧・編集には不要。

```powershell
& 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1104-2876-0_26.1104.2876.0_x64__3k8sg7r9htsxt/dependencies/node/bin/node.exe' presentation/build.mjs tang-you-chi-presentation-v2.pptx
powershell -NoProfile -ExecutionPolicy Bypass -File presentation/render.ps1 -Deck outputs/tang-you-chi-presentation-v2.pptx
```

ファイナライザーは既存ファイルを上書きしないため、再生成時は新しい出力名を指定する。

今回の更新では新規名で作成・検証後、水門の操作画面を改善した `tang-you-chi-presentation-refresh-reviewed.pptx` を採用し、`artifacts/presentation/refresh/` へ全13枚を描画した。同じ内容を正本 `outputs/tang-you-chi-presentation-final.pptx` と同名PDFへ反映している。中間PPTXは `artifacts/presentation/candidates-13/`、初期11枚版のファイル・検証記録は `artifacts/presentation/version-11-verified/` に保持する。現在版の照合値と検証範囲は `artifacts/presentation/VISUAL-QA.md` を参照する。

## 描画と検証

- Artifact ToolでPPTXを出力し、付属ファイナライザーでパッケージ、寸法、文字領域、フォント指定、同ツールでの再読込を確認する。
- このWindows環境ではArtifact ToolのPNG出力が最初のスライドで終了コード1となり、診断文を返さなかった。PPTX出力と検証は成功するため、PNG描画は既設のMicrosoft PowerPoint 16.0で行う。
- `render.ps1` はPPTXを読み取り専用・ウィンドウ非表示で開き、各スライドを1280×720のPNGとPDFへ出力する。PPTXそのものを書き換えない。
- `powerpoint-text-layout.json` に各文字領域とPowerPoint実描画の境界を記録する。PNG全枚の視覚確認と併用し、自動検査だけを見た目の保証としない。
- 原稿や評価数値を変えたら、新規出力に対して構造検証と全枚描画をやり直す。

公式API根拠：[PowerPoint Slide.Export](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.slide.export)、[Presentations.Open](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.presentations.open)。

評価の点数はプロジェクト独自の進捗評価。大会公式点・認証・実際の再訪効果とは区別する。基準の版、採用項目と未検証範囲は `docs/BENCHMARKS.md`、試験結果は `docs/EVALUATION.md` を正本とする。
