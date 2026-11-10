> 最終存在確認：2026-11-10、communityディレクトリは不存在です。移設後の空フォルダ削除要求は当方では拒否されており、除去主体・方法は未確認。下記の空フォルダ残存はその前の観測です。旧残骸・キャッシュ等は引き続き残存しています。

# 現在のフォルダ構成と移動記録

2026-11-10、ルート直下への配置変更後の読み取り監査。対象は `C:/AI-Sprint/workspace/MC-002`。現行アプリは **`backend/` と `frontend/`** にある。旧 `community/` を起点にする構成は廃止し、運用・試験・素材の参照も新配置へ変更した。

**これは不要ファイルの削除完了ではない。主担当が削除を伴わない76件の移動を実施し、旧残骸は別の場所へ保管した。監査担当による削除・移動は0件。** 移動先76件と、Git indexの旧community配下807ファイルに対応する新配置の存在を独立確認した。ファイルの全バイト一致やDBの内容一致を確認した意味ではない。

## 古い整理リストは再実行しない

**移動前のcleanup manifestにあるルート `backend/`・`frontend/` を、そのまま削除対象にしてはいけない。現在は現行アプリのソースが入っている。** 過去の一覧にある「旧backend」「旧frontend」という役割は、現在の同名パスには適用できない。旧残骸の現在位置は後述の保管表で区別する。

先行する削除要求は、自動承認レビューが実行前に `blocked by policy` と拒否し、主担当・wa担当とも削除0件だった。その後、最新の配置変更方針に従って非削除の移動を行った。削除拒否を削除成功へ読み替えない。空になった `community/scripts/` と親 `community/` への非再帰削除要求も実行前に拒否された。後続の最終確認では両パスが存在しないことを独立確認した（2026-11-10 13:45 JST）。除去主体・方法は未確認であり、主担当や監査担当の削除成功とは記録しない。削除の再試行は行っていない。

## 現在の配置

```text
MC-002/
  compose.yaml / Dockerfile / .dockerignore
  README.md / DESIGN.md / TASKS.md / AGENTS.md
  backend/                 現行Pythonアプリ・依存定義
    app/
  frontend/                現行React・配信素材・依存定義
    src/・public/・scripts/
  assets/                  種データ・紹介動画用のローカル素材
  deploy/                  nginx設定
  scripts/                 起動・保存復元・品質・台帳・分析・動画制作
  quality/                 品質測定設定
  test/                    現行backend・tooling・browser・integration試験
    fixtures/runtime/      試験一時領域と区別された旧残骸の保管
  docs/
    contracts/             旧community直下の契約12本
    OPERATIONS.md          旧community READMEの移動先
    history/               旧文書・旧Compose入口の履歴
  artifacts/
    community/             旧community/artifactsを分離して保全
    retired/legacy-frontend/ 旧ルートfrontendの生成物・依存
  outputs/                 配布する動画・字幕・図・資料
  backups/                 DB・写真のバックアップ
  data/                    分析用DB・秘匿鍵（アプリ稼働volumeとは別）
  models/                  保持対象のモデル資産（通常起動で推論しない）
  project/                 チケット台帳・イベント履歴
  old/v1.1/                旧ソースZIPが残存
  presentation/            現行PPTX/PDFの説明・制作素材（外部依存junctionは保持）
  .git/・.agents/・.venv/・.tools/
```

`frontend/node_modules/` と `frontend/dist/` は現行frontendとともに移動した依存・生成物。旧ルートfrontendの同名フォルダとは別であり、旧残骸は `artifacts/retired/legacy-frontend/` にある。

## 実行・参照経路

| 入口・根拠 | 現在の参照 |
|---|---|
| [compose.yaml](../compose.yaml) | ルートをビルドコンテキストにする。プロジェクト名 `kou-community` と名前付きvolumeを維持。 |
| [Dockerfile](../Dockerfile) | `frontend/` をビルドし、`backend/app/` と配信ファイルをイメージへコピー。旧生成物の保管先は使わない。 |
| [.dockerignore](../.dockerignore) | 原則除外からbackend/app・依存定義・frontendだけを許可。rootのDB、backups、artifacts等をビルドに混ぜない。 |
| [pytest.ini](../pytest.ini) | `test/backend`・`test/tooling` がテスト正本。Python参照先は `backend scripts`、一時領域は `test/fixtures/runtime`。 |
| [test/run.py](../test/run.py) | ルートComposeと現行試験を使用。結果は `artifacts/test-runs/`。 |
| [scripts/setup-local.ps1](../scripts/setup-local.ps1) | `backend/requirements-dev.txt`、`frontend/`、`test/browser/` の依存を準備。 |
| [scripts/full_snapshot.py](../scripts/full_snapshot.py) | ルートCompose、`scripts/snapshot_worker.py`、`backups/` を使用。保存履歴は `artifacts/community/`。 |
| [scripts/quality_check.py](../scripts/quality_check.py) | `artifacts/community/frontend-quality`・`artifacts/community/quality` の固定基準と測定を比較。旧新ソースパスを同じファイルとして正規化する。 |
| [frontend/scripts/measure-quality.mjs](../frontend/scripts/measure-quality.mjs) | 出力先は `artifacts/community/frontend-quality`。測定対象は現行frontend/src。 |
| [scripts/measure_backend_quality.py](../scripts/measure_backend_quality.py) | 現行 `backend/app` と `quality/ruff.toml`、出力先 `artifacts/community/quality` を使用。 |
| [scripts/analyze_samples.py](../scripts/analyze_samples.py) | `data/analytics-v2.db` 等はローカル分析用。稼働アプリDBとは分離。 |

`community` という語はDBの名称、Dockerのプロジェクト名、コミュニティの公開範囲などにも使う。語だけを一括置換しない。過去の測定結果・原稿manifestに保存された旧パスも、その時点の由来として保持する。現行の生成器は新配置を出力する。

## Dockerの保存先と再作成の確認

- 稼働DB・写真は引き続き名前付きvolume `kou-community_community-data` の `/app/data`。ルート `data/` をアプリへマウントしない。
- 移動直後の既存コンテナでは、素材とnginx設定のbindが旧communityパスのままだった。主担当がルートComposeからコンテナを再作成した後、`docker inspect` のMountsだけを読み取り、次の接続を独立確認した。
- app：`C:/AI-Sprint/workspace/MC-002/assets` → `/app/seed-assets`、読み取り専用。
- gateway：`C:/AI-Sprint/workspace/MC-002/deploy/nginx.conf` → `/etc/nginx/nginx.conf`、読み取り専用。
- appのデータvolume名と接続先は再作成前後で同一だった。DB・写真の中身を本監査で読んだり、データ完全一致を検査したわけではない。

ビルド・再起動・実試験・バックアップ検証は主担当と各実装担当の記録を参照する。本監査担当はコンテナ変更、ビルド、試験を実行していない。

## 旧配置からの対応と残存物

| 移動前 | 現在位置 | 状態・扱い |
|---|---|---|
| `community/backend/` | `backend/` | 現行アプリ。直下はapp、README、requirements2本のみ。旧tests・試験tmpは分離された。 |
| `community/frontend/` | `frontend/` | 現行アプリ。依存・配信素材を含む。 |
| `community/assets/`・`deploy/`・`quality/` | 同名ルートフォルダ | 現行素材・配信設定・品質設定。 |
| `community/scripts/` の22ファイル | `scripts/` | 運用・制作用。元のディレクトリは最終確認時には不存在。除去主体・方法は未確認。 |
| `community/backups/`・`models/` | `backups/`・`models/` | 保護対象。モデル取得用手動ツールと資産の保持は、通常起動で推論することを意味しない。 |
| `community/artifacts/` | `artifacts/community/` | 証拠と品質基準。root artifactsへ直接上書き統合しない。 |
| `community/README.md`・契約12本 | `docs/OPERATIONS.md`・`docs/contracts/` | 現行運用・契約の参照先。旧ルートCompose入口は `docs/history/compose-entry-before-root.yaml` に保存。 |
| 旧ルート `backend/` | `test/fixtures/runtime/legacy-root/backend-root/` | 旧cache・一時領域を保管。現行テスト正本ではない。 |
| 旧community/backendのtmp・tests | `test/fixtures/runtime/legacy-root/community-backend/` | 過去の試験残骸。現行backend/appに混在しない。 |
| 旧community/qa・scripts bytecode等 | `test/fixtures/runtime/legacy-root/` の専用サブフォルダ | 保管残存。QA正本は `test/browser/`。 |
| 旧ルート `frontend/` | `artifacts/retired/legacy-frontend/` | 旧dist・node_modulesを保管。現在のビルド・稼働参照はない。 |
| `old/v1.1/source-with-history.zip` | 同じ場所 | 85,610,168 bytesの旧配布物が残る。内部未読。削除済みとは扱わない。 |
| `presentation/` | 同じ場所 | READMEと外部WindowsApps依存へのjunctionが残存。リンク先を走査・削除しない。 |

移動前の旧編集ソースは、コミット `81522a3760ae48c27ed743e535dd7b054edf1c21` にbackend/main、frontend/package、presentation生成器2本のGitオブジェクトが存在することを先行監査で確認した。これは選択した旧ソースの復元根拠であり、ZIP全体とGitが同一という保証ではない。

## 証拠を上書きしないための分離

旧 `community/artifacts` とルート `artifacts` には、`container-verification.json` と `quality/*/summary.json` 10件、計11件の同名ファイルがあった。移動後に双方の存在とSHA-256を比較し、**11件すべて内容が異なる**ことを確認した。`artifacts/community/` に分けたため双方が残る。全一覧・ハッシュは [参照監査JSON](../artifacts/folder-reference-audit.json) に記録した。

品質比較は旧記録を改変せず、旧 `community/backend/app/...` と新 `backend/app/...` を比較処理で同一ファイルとして扱う。新規測定が別の証拠フォルダへ流れないよう、入口と測定器の出力先も一致させた。

## 監査結果と限界

[移動結果](../artifacts/root-layout-move-result.json)の76移動先は全件存在する。`SourceAbsent` は各移動直後の記録であり、現在その名前が存在しないという意味ではない。ルートbackend/frontend/composeは現行の内容で再使用している。

[参照監査JSON](../artifacts/folder-reference-audit.json)には、現配置の参照アンカー・ハッシュ、移動先とGit追跡807ファイルの存在検査、11組の証拠衝突、Docker Mountsの再作成前後、保護対象を記録した。前の「communityが現行」という監査は `historical_audits` に時点を付けて保持し、現在の配置と混同しない。

読み取ったのは浅い一覧、除外付きrg、指定した設定・ソース・証拠JSON、Git index、DockerのMounts情報。秘密情報、DB、写真、元CSV、モデル重み、ZIP内部、依存キャッシュや外部junctionの中身は読んでいない。`.git`、data、backups、DB/media volume、models、現行ソース、試験、確定証拠、チケット履歴は保護する。

現時点の整理後推奨は、上記のルート配置を編集・起動・検証の唯一の導線とし、残る旧配布物・保管残骸を現行実装に再混入させないこと。未削除物の存在は明記し、追加削除や旧リストの再実行は行わない。

## 最終存在確認の追記

2026-11-10 13:45 JST、`community/` と `community/scripts/` は存在しないことを読み取りで確認した。ルート `.pytest_cache/`・`.ruff_cache/`、`artifacts/retired/legacy-frontend/`、`old/`、`test/fixtures/runtime/legacy-root/` は引き続き存在する。先行する削除要求の拒否記録を保持し、後から観測した不存在の理由・実施者を推測しない。監査担当の削除・移動は0件のままである。
