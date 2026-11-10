# Python API

現行バックエンドはこの `backend/app/` です。FastAPI・SQLiteを用い、Dockerのappサービス内で動作します。DBの現在版はschema 12。実AIモデルや外部AI APIは通常起動で使いません。

- [全体設計](../DESIGN.md)
- [起動・停止・保存・復元](../docs/OPERATIONS.md)
- [API契約一覧](../docs/README.md)
- [テスト](../test/README.md)：実装は `test/backend/`。このフォルダに旧テストや一時DBを戻さない。
- [最新評価](../docs/EVALUATION-COMMUNITY.md)：旧版の試験数・skip・点数を現在の状態として使わない。

通常はルートで `./scripts/start.ps1 -Build` を実行します。`requirements.txt` は実行依存、`requirements-dev.txt` は試験用依存です。秘密情報、実DB、写真、バックアップをGitに含めません。
