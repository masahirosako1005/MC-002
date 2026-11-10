# 講：ローカル運用

更新：2026年11月10日。現行データベースは **schema 10**。実装の正本はプロジェクトの [DESIGN.md](../DESIGN.md)、作業状態は [TASKS.md](../TASKS.md)、変更履歴は [CHANGELOG.md](../docs/CHANGELOG.md)。この文書は現行の起動・保存・検証手順を扱う。

## 現行の構成と動作

- ReactとPythonをDockerで起動し、[ローカル画面](http://127.0.0.1:8081)で使う。Composeプロジェクトは `kou-community`、保存volumeは `kou-community_community-data`。
- 日帰りの主ゾーンは片道20〜40km。初期経路は新宿〜町田、新宿〜新百合ヶ丘の鉄道参考経路。距離・所要時間の出典と限界は [経路調査](../docs/DAYTRIP-ROUTES.md)に記録している。
- 講ごとに開催を保存し、先達の事前承諾、実参加の本人申告、別参加者の確認を分ける。通常ポイントと、事業者の利用確認がある特典資格ポイントも別管理。先達は開催ごとの役割で、利用ランクとは別。
- 割引は事業者が公開した条件だけを使う。参加失効や講・相談の閉鎖で、対象の未利用分だけ取消して利用枠を戻す。利用済み金額と他人の有効な確保は変えない。
- 通常起動ではモデル推論・外部AI API・SDK・キーを使わない。対話は規則と定型文、実カタログによる案内。写真は手動タグ選択を基本とし、既知の同梱素材だけ内容ハッシュ一致による事前候補を表示する。
- 写真、訪問記録、訪問バッジ、関心と許可、記念日、宿泊プラン、従来の会話は保持する。旧写真・見積確認・訪問記録を、新しい開催実績やポイントへ自動換算しない。
- 左右スマホは独立認証。前回画面・コミュニティ・参加済み講・探索条件を本人別に保存し、再開時に現在の権限を確認する。未送信の文章や入力中の見積すべてを自動保存する機能ではない。

予約・入金・現地訪問の外部認証は行わない。見積や割引の記録は予約確定を意味しない。詳しい状態と権限は [日帰りAPI](DAYTRIP-CONTRACT.md)、[既存API](API-CONTRACT.md)、[旅の記録API](JOURNAL-CONTRACT.md)を参照する。

## 起動と停止

Docker/WSL、ビルド依存、同梱の `community/assets` が必要。コマンドは `C:/AI-Sprint/workspace/MC-002` で実行する。通常起動にモデルディレクトリや外部AIキーは不要。

```powershell
.\community\scripts\start.ps1 -Build
```

ビルド済みなら `-Build` を省く。保存volumeを接続したまま起動し、schema 8/9のデータは追加移行でschema 10へ進む。移行前に下記の一括保全を行う。未知のスキーマ版は起動時に拒否する。

```powershell
docker compose -p kou-community -f community/compose.yaml ps
docker compose -p kou-community -f community/compose.yaml logs --tail 50 app
docker compose -p kou-community -f community/compose.yaml stop
```

`stop` は新版だけを停止する。`down -v` は保存内容を削除するため通常の終了には使わない。旧8080系のソース整理と、旧Dockerイメージ・コンテナー・保存volumeの削除は別の操作であり、現在の手順は旧Docker資源を削除しない。

## 保存とバックアップ

appは `/app/data/community.db` と `/app/data/media` に保存する。写真は静的公開せず、所有者と現在の所属を検証するAPIを通して配信する。

`full_snapshot.py` はDBと写真を同じ停止期間に保存する。実行前に画面操作・書込みを止める。`--allow-stop` は新版appの短時間停止と、その後の再開を許可する指定。旧版は停止しない。

```powershell
.\.venv\Scripts\python.exe community/scripts/full_snapshot.py backup --allow-stop
```

保存先は `community/backups/日時-識別子/`。完了したmanifestに、各ファイルのSHA-256、SQLite完全性・外部キー・表件数、アプリのイメージIDを記録する。モデルmanifestは存在するときだけ補助メタデータとして保持し、ない場合はnull。旧形式のバックアップも引き続き読める。モデルの読込みや推論は行わない。

検証・隔離復元では、作成された保存先を明示する。

```powershell
.\.venv\Scripts\python.exe community/scripts/full_snapshot.py verify --snapshot community/backups/保存先名
.\.venv\Scripts\python.exe community/scripts/full_snapshot.py restore --snapshot community/backups/保存先名
```

復元先は毎回新しい `kou-community-restore-…` volume。空でない先への上書き、現行volumeの削除、Composeの保存先切替は行わない。復元後のアプリ操作・利用者データの正しさ・復元時点以後の権限取消の再反映は、ファイル一致とは別に確認する。バックアップには認証データと写真が含まれるため、Git・配布用ソース・クラウド調査へ含めない。

## 現行の検証

バックエンドの受入は `test/backend`。主な対象は次のとおり。

| 対象 | 試験 |
|---|---|
| 開催、先達、相互確認、ポイント、特典、競合、追加移行 | `test_daytrip.py` |
| 推論・ネットワーク不要の起動、手動タグ、旧jobs保持、削除再試行 | `test_image_guidance.py` |
| 認証、権限、入力画像の検証・再符号化、保存 | `test_api.py` |
| 訪問記録、公開範囲、画像位置確認、保存・再起動 | `test_journal.py` |
| 本人別の再開と退出時の失効 | `test_personalization.py` |
| バックアップの任意モデルメタデータと旧形式読取り | `test_snapshot_metadata.py`（Docker・実volume操作なし） |

```powershell
New-Item -ItemType Directory -Path test/fixtures/runtime -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest test/backend -q --basetemp=C:/AI-Sprint/workspace/MC-002/test/fixtures/runtime/current-api
```

`test/fixtures/runtime` は隔離試験専用。実DBや写真の保存先に指定しない。各試験の適用範囲は成果物で区別する。

- [日帰りの境界修正後27試験](../outputs/daytrip-boundary-after.xml)：プラン改訂後の旧同意の拒否、事業者の競合後再取得も含む。
- [schema 10・未利用枠返還の26試験](../outputs/daytrip-release-holds-tests.xml)：日帰り25件と訪問記録の再起動確認1件。
- [モデルソース整理後の38試験](../outputs/model-source-cleanup-tests.xml)：画像案内、API、旅の記録。
- [バックアップメタデータ4試験](../outputs/snapshot-metadata-tests.xml)：モデルmanifestなしの保全と旧形式の読取り。実バックアップ/復元の試験とは分ける。
- [全現行Pythonの静的測定](artifacts/quality/daytrip-final/summary.json)：55モジュール、Ruff 0、Bandit Medium 19/High 0、複雑度14件。既存指摘や未達を隠さず、対象変更による件数変化を品質点へ換算しない。

全体試験・対象試験・画面確認は別の結果で、同じ試験を合算して成功数を水増ししない。大会点や実再訪効果は自動試験の件数から算出しない。

## 実行時の境界と資産

`app` は外向き通信を持たないinternal networkに接続し、非root・read-only rootfsで動作する。`gateway` は127.0.0.1:8081に入口を公開する。画像・フォント・アプリ内APIはローカル提供。gateway全体の外向き通信をOSファイアウォールで遮断したという意味ではない。

書込みはOriginとCSRFを確認する。写真の上限は12MiB/2000万画素、静止JPEG・PNG・WebP。配信画像はEXIFを除去し、位置候補は本人の事前許可がある場合だけ読み取る。削除再試行は論理削除済み写真だけを対象にし、残す写真・カバー画像・保存先外のファイルを削除しない。

現行の通常起動に使わない旧分類器、モデル専用依存、旧モデル/旧コンテナー構成の検証スクリプト、常時スキップの実モデル試験は撤去した。スキップ削除を試験成功へ換算しない。モデル重み・取得根拠・ライセンス・写真素材と旧試験の成果物は保持する。以前のschema 1〜2やモデル推論の実測は [CHANGELOG.md](../docs/CHANGELOG.md)と対応する歴史的成果物を参照し、現行の動作証拠には流用しない。
