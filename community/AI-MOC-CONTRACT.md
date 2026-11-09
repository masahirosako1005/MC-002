# 現在のMOCと本番AIの境界

利用者の2026-11-09最新指示: 現在はAI風のMOC、本番は外部APIによるAIを予定する。現在の返答を実AIの推論と扱わない。既存モデル資産は保管し、通常起動からの読込/推論だけを停止した。外部API実装自体はまだ存在せず、削除した実装があるとは説明しない。

## ソース上の出力箇所

- `backend/app/circles/assistant.py` の `turns` 内: **MOC** コメントの直後で、入力条件を既存ルールで整理し、公開カタログと定型文から返答を構成する。
- `backend/app/image_guidance.py` の `photo_guidance`: **MOC** コメントの直後で、4種類の公開素材の正確なSHA256だけ事前タグ候補を返し、その他は手動選択を返す。ファイル名/投稿文から認識済み扱いにしない。
- `main.py` は `ImageGuidance` を作り、bootstrapで `inference_enabled=false` / `external_ai_enabled=false` を返す。実モデルのclass/ファイルは保持するが呼び出さない。

## 本番で差し替えるときの契約（未実装）

外部APIはサーバー側adapterで返答候補だけを生成する。利用者の同意と送信最小化、秘密管理、期限/取消、構造化出力検証、失敗時の定型案内への復帰、コスト制限は本番導入時の必須設計事項。現時点ではネットワーク開放・SDK・鍵は追加しない。

本人認証、コミュニティ/講の所属、共有同意、料金/日付/事業者の公開状態、候補ID/版の照合、冪等性とDB transactionは現サーバー側で必ず判定する。AI返答だけで招待・相談送信・予約・保存を完了しない。候補の理由生成と、本人が選んで保存する動作を分離する。

## 現在の検証

`artifacts/guided-runtime/api-tests.json`: CP45+基盤API 22成功、旧実モデル試験1skip。推論constructor/import/networkを禁止して起動、事前候補/任意写真manual、旧job保持、相談/双方確認の実保存、削除ファイルの再試行を含む。

`artifacts/guidance/browser.json`: 実配信画面の写真アップロード→事前タグ候補→本人が選択→下書き実保存を確認。axe違反0/外部要求0/pageerror0、試験投稿は削除。最初の2回は試験側の旧初期画面想定と存在しない単体GET参照で失敗し、正しい導線とfeed取得へ修正して通過。製品エラーを成功へ偽装しない。

Docker最初の切替時はcleanup methodがCOPYされる前の状態を組み込み起動失敗。編集を凍結して再buildしapp/gateway Healthyへ回復。記録は `artifacts/quality/deployment-loop.json`。schema8移行で追加された保守cursorを全行一致は検出したが、46旧表の旧行保全と8既存media一致を別途確認した。
