# 講 — 日帰りの旅と仲間

React・Python・Dockerで動く、ローカルの旅行コミュニティです。写真と本人が許可した関心から仲間を探し、講で行き先を決め、事業者と相談します。

日帰りのターゲティングゾーンは片道の経路距離20〜40km。開催・本人の参加承諾・実施確認・先達の役割を分けて保存し、確認済みの実績からポイントとランクを計算します。割引は事業者が公開した条件に従います。

## 起動

プロジェクトのフォルダで次を実行します。

```powershell
.\scripts\start.ps1 -Build
```

- [旅行者スマホ・事業者PCの画面](http://127.0.0.1:8081/stage)：左が旅行者のスマホ、右が事業者のPCダッシュボード。
- [アプリ](http://127.0.0.1:8081/) / [操作手順](docs/COMMUNITY-TRY.md)
- [現行の構成・保存・検証](docs/OPERATIONS.md)

初回の依存取得とイメージ構築にはネットワークを使います。通常利用は外部API・外部DB・外部素材配信に依存しません。AI風の案内はローカルの規則と定型応答で、モデル推論やChatGPT APIは使いません。

## 最初に見る資料

- [現在の設計仕様](DESIGN.md) / [作業と未解決事項](TASKS.md)
- [文書一覧](docs/README.md) / [フォルダの用途と整理結果](docs/FOLDER-STRUCTURE.md)
- [成果物の最新版一覧](outputs/README.md) / [直近の品質評価](docs/QUALITY-CURRENT.md)
- [最新紹介動画・女性音声と実操作](outputs/kou-revisit-intro-v10.mp4)（46.5秒）

## プロジェクトの配置

| 場所 | 用途 |
|---|---|
| `backend` | 現行Python API・保存処理 |
| `frontend` | 現行React画面と同梱素材 |
| `test` | API・画面・保全・開発ツールの試験、合成素材 |
| `scripts` | 起動、保全、品質測定、動画、台帳、CSV分析、環境準備 |
| `outputs` | 最新の動画・発表資料・配布物。旧版はhistoryへ分離 |
| `presentation` | 現行発表資料の素材と再生成手順 |
| `project` | チケット台帳と履歴 |
| `docs` | 設計の根拠、調査、評価、変更記録 |
| `.agents/skills` | 固定した公式React・FastAPIの開発指針 |
| `artifacts` | 新しい試験・品質評価の結果（既存証拠は元の場所を保持） |

**現行コードはルート直下の `frontend/` と `backend/` です。旧残骸は `artifacts/retired/legacy-frontend` と `test/fixtures/runtime/legacy-root` へ分離済み。現在の `frontend`・`backend` は削除しないでください。**

ソースと成果物はこのプロジェクト内に置きます。`C:/AI-Sprint/sample-data`は参照専用です。DB・写真・秘密情報はGitに含めません。旧版ソースの整理方針と結果は[撤去監査](docs/CLEANUP-AUDIT.md)へ記録し、過去の変更はGit履歴から追跡します。

## 設計・評価

[設計書](DESIGN.md) / [タスク](TASKS.md) / [チケットボード](outputs/project-board.html) / [日帰りとランクの計画](docs/DAYTRIP-RANK-REDESIGN-PLAN.md) / [和の画面設計](docs/WA-ART-DIRECTION.md) / [直近の品質評価](docs/QUALITY-CURRENT.md)

過去の試験件数や点数を、新しい変更の成功証拠として流用しません。通常のEdgeプロファイルでの応答停止は、アプリの分離した検証環境での成功とは別の未解決事項です。

試験の入口は[test/README.md](test/README.md)。継続評価は `./.venv/Scripts/python.exe scripts/quality_check.py <新しい測定名>` で静的検査とAPI・開発ツール試験を順次実行します。利用する指針と測定の限界は[スキル・品質方針](docs/SKILL-QUALITY-POLICY.md)を参照してください。


## N西市と来訪元

目的地は大阪府内の架空都市N西市。登録画面からアカウントと居住市区町村を登録できます。番地は集めません。一覧外の地域では住所を登録せずに続けられます。地域集計への協力は任意で、プロフィールから取り消せます。

事業者の「実績の概要」で30/90/365日の来訪元・再訪を全国/関西の地図と表で確認できます。現在の居住地域であり、実際の出発地ではありません。5人未満の地域等は省略します。

現在の保存内容にN西市の設定と追加資料を入れる操作は、先にバックアップ後、`python -m app.city_setup --apply`、`python -m app.enrichment --apply` の順に明示的に実行します（コンテナ内）。通常起動時には既存データを書き換えません。来歴は[追加資料](docs/CONTENT-PACK.md)、確認結果は[今回の検証](docs/NISHI-ACCEPTANCE.md)。
