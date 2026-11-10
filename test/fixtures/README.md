# テスト用データ

- `journal-gps.jpg`：位置情報の確認に使う既存の合成画像。実利用者の写真ではない。
- `coffee.png`：同梱の合成素材 `assets/coffee.png` とSHA-256が同じ試験用コピー。アップロード入力として使う。元のアプリ素材は保持する。
- `runtime/`：試験ごとに生成する合成DB・画像・一時台帳。Git対象外。実データや復元用バックアップを入れない。

実行結果・ログ・画面証拠はプロジェクト直下の `artifacts/` に保存する。旧 `community/artifacts/` の内容は `artifacts/community/` に移動して保持する。

`runtime/legacy-root/` には現行ソースから分離した旧試験一時領域がある。過去のルート `.backend-test-tmp` / `.test-work`、旧backendの残骸、旧community内の試験キャッシュ等で、現在のアプリから読み込まない。移動の事実は [root配置移動記録](../../artifacts/root-layout-move-result.json) と [最初の2フォルダー移動記録](../../artifacts/test-relocation-result.json) に残す。移動を削除済みとは扱わない。
