# 現在の整理状況 — ルート構成への移設後

2026-11-10の最終配置は **ルート `frontend/` と `backend/` が現行ソース** です。本文の古い削除一覧に同名パスがあっても、再実行しないでください。移設前と現在では内容が異なります。

76パスを上書きなしで移動しました。旧root backendのテスト残骸は `test/fixtures/runtime/legacy-root/backend-root`、旧root frontendの依存/ビルドは `artifacts/retired/legacy-frontend` に分離。現行communityの試験残骸もtest配下へ集約。現行コード・素材・運用はrootへ、契約はdocs/contracts、保存物はbackups、既存証拠はartifacts/communityへ移しています。

**削除は未完了です。** 不要物と、移設後に空になったcommunity/scripts・community親の削除要求は、自動承認レビューが実行前に拒否しました。別手段で迂回していません。過去の『50対象残存』は移設前の配置の監査であり、現在のパスは移動記録で追跡します。

- [現行構成と保護対象](FOLDER-STRUCTURE.md)
- [76パスの移動記録](../artifacts/root-layout-move-result.json)
- [独立参照監査](../artifacts/folder-reference-audit.json)
- [削除拒否時の記録](../artifacts/folder-cleanup-test-result.json)

DB・写真・モデル・バックアップ・秘密情報・Git履歴は削除していません。以下は過去の判断と実施経緯です。

---

# 現行ソースへの整理：独立棚卸し

## 主担当による実施状況

### 最新：テスト一時領域・キャッシュの整理（2026-11-10）

先の非削除移動により、ルート `.backend-test-tmp` と `.test-work` は `test/fixtures/runtime/legacy-root/` 配下にある。607ファイル・309,835,354 bytesの前後ハッシュ、件数、容量、相対パスを照合済みで、元の2パスは存在しない。[移動証拠](../artifacts/test-relocation-result.json)を保持する。

利用者の改めての明示削除依頼に基づき、移動先2フォルダーを含む旧試験一時領域28・Python bytecodeキャッシュ19・pytest/Ruffキャッシュ3の計50フォルダー（1,542ファイル・566,089,799 bytes）を監査した。絶対パスはすべてPJ内、祖先と子孫の再解析ポイント0、試験・品質計測プロセス0。動画Pythonが稼働中のため `community/scripts/__pycache__` は除外した。依存環境・実DB・バックアップ・モデル・volume・動画素材・検証証拠は削除対象外。

確認済み対象へのPowerShell削除要求は、自動承認レビューがプロセス開始前に `blocked by policy` と拒否した。詳細理由は提示されなかった。**今回の削除0件、残存50件**を存在確認済み。別手段や対象分割、移動での迂回は行っていない。削除コマンド内で予定していたDockerマウントの再確認も実行されておらず、実施済みとは扱わない。[最新結果](../artifacts/folder-cleanup-test-result.json)と[対象別監査](../artifacts/folder-cleanup-test-inventory.json)を正本とし、下記の32対象等は当時の履歴として区別する。

再生成防止は標準入口へ反映した。pytestの一時領域・キャッシュは `test/fixtures/runtime/` に限定し、root `pytest.ini` を標準入口として維持する。`test/run.py`、`scripts/quality_check.py`、バックエンド品質計測は子Pythonのbytecode書出しを抑え、バックエンド品質計測のRuff・複雑度呼出しは `--no-cache` を使う。変更後の対象15試験は0.08秒で成功した（[XML](../artifacts/folder-cleanup-test-tests.xml)）。重い全体試験は再実行していない。確定済みの品質レポート・画面等は `artifacts/` / `community/artifacts/` に保持する。

### テスト配置の統一と残存一時領域（2026-11-10追補）

現行の試験ソース・fixture・実行時一時領域は `test/` 配下に統一する。pytestの一時DB/画像/キャッシュは `test/fixtures/runtime/` の子ディレクトリに限定し、`test/conftest.py` が旧ルートへの指定や範囲外への解決を実行前に拒否する。PJ直下の `pytest.ini` は通常の探索対象を `test/backend` と `test/tooling` に絞る標準入口として保持し、`test/run.py` と `scripts/quality_check.py` も明示して使う。確定済みの試験XML/JSONや画面は検証証拠なので、`artifacts/` / `community/artifacts/` に保持し、参照を切る移動は行わない。

旧 `.backend-test-tmp`、`.test-work`、旧pytestキャッシュ、ソース移設後の旧tests内キャッシュ等を32フォルダー監査した。合計1,377ファイル・563,218,474 bytes（約537 MiB）。解決済みパスはPJ内、再解析ポイントと読取不能ディレクトリは0、稼働試験プロセスと対象に重なるDockerマウントも検出しなかった。運用DB・写真・バックアップ・秘密・旧配布物・動画の一時領域は今回の処理対象から除外した。

この時点の32フォルダーの削除要求は自動承認レビューがプロセス開始前に `blocked by policy` と拒否し、詳細理由は示さなかった。当時は削除0件・残存32件で整理完了とはしなかった。この時点では別手段での削除・移動や対象を分割した再試行は行っていない。後続の記録・再検証をまとめた非削除コマンドも拒否されたため、その実行結果は成功根拠に含めない。後に別途許可された2フォルダーの非削除移動と、最新の再監査結果は上記を参照。

保存先制限と品質runnerの対象試験は15件成功（0.25秒）、標準runnerの収集も成功した。重い全体試験は再実行していない。新規2ファイルのRuff指摘は0、変更した既存runner2ファイルの4指摘は変更前と同数で、新規指摘0。

証拠：[対象別監査](../artifacts/test-layout-cleanup-inventory.json)、[実施・拒否・残存記録](../artifacts/test-layout-cleanup-result.json)、[15試験XML](../artifacts/test-layout.xml)、[標準runner収集](../artifacts/test-runs/20261110T040053Z-bd67c03a/result.json)。下記の旧棚卸し表は当時の配置を含むため、現行の試験配置は本追補と [test/README](../test/README.md) を優先する。

### 指定2フォルダの当初の削除要求（2026-11-10・履歴）

`.test-work` は日帰り・投稿・番付等の過去の試験用DB/画像、`.backend-test-tmp` は旧アプリのpytest一時保存先。いずれもアプリ起動に不要。現行ソースの通常試験は `test/fixtures/runtime` に統一済みで、旧パスの残存参照は除外設定・過去の検証記録に限る。

利用者の明示削除指示を受け、絶対パスがこのPJ内にあることと再帰先のリンクがないことを確認した上で、PowerShellの削除を要求した。しかし実行前の自動承認レビューが `blocked by policy` と拒否し、詳細理由は示さなかった。両フォルダは未削除。別手段での迂回は行わずCP65を未完了で維持する。試験結果XML/JSONは削除対象の一時DBとは別の監査証拠として保持する。

2026-11-10：Git管理下の旧アプリ・旧テスト・旧生成器等80ファイルを `git rm` で撤去。ルートComposeを現行communityへ委譲し、QA依存と検証コードは最終的にtest/browser・test/integrationへ集約した。削除対象全件の一括削除と、未追跡ZIP/bundle等の個別削除は自動承認審査から `blocked by policy` と拒否された。詳細理由は提示されていない。別の手段でこの拒否を回避せず、未追跡の旧配布物・旧依存/ビルドキャッシュ等は残存として記録する。

各対象の存在状態は [実施記録](../outputs/cleanup-verified-paths.json) に保存。CP65は全件削除完了とはしない。DB・写真・Git履歴は維持。以下の表は元の監査判断であり、現状は実施記録を優先する。

2026-11-10。最新の利用者指示「関係なくなったソースを削除し、現在使うソースだけを残す」を対象とする。従来の旧版ソース保持方針はこの指示で変更された。監査担当は読取と本記録の作成のみ実施し、削除・移動・起動・停止・DB操作はしていない。削除の最終実施は主担当。

## 境界の結論

現行アプリは `C:/AI-Sprint/workspace/MC-002/community`。同ディレクトリのComposeはプロジェクト `kou-community`、8081、名前付きvolume `kou-community_community-data` を使う。Dockerfileがコピーするのは同ディレクトリの `backend/app` と `frontend` で、画像素材は `community/assets` の読取専用bind。ルート直下の `backend` / `frontend` / `deploy` は現在のビルドから参照されない。

調査開始時のルートCompose/Dockerfileは旧 `tang-you-chi`・8080・`journey-data` 用だった。主担当がルートComposeを `community/compose.yaml` のincludeへ置換し、READMEも現行専用に更新した。最終読取で置換を確認したため、ルートCompose/READMEは保持する。主担当はCompose設定のname/build/8081/volumeが現行と同じことも検証済み。現行コンテナー、データvolume、旧データvolumeの削除はソース整理に含めない。

## 削除対象のソース・重複配布物

以下は監査で確認した絶対パス。削除済みを意味しない。ディレクトリ削除前には主担当が解決済みパス、再解析ポイント、保護対象の混入を再確認する。

| 絶対パス | 判定・根拠 |
|---|---|
| `C:/AI-Sprint/workspace/MC-002/backend/app` | 旧水門/謎解き/収集アプリ。現行communityからのimport/build参照なし。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/backend/tests` | 旧API/収集テスト。現行 `community/backend/tests` と別。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/backend/requirements.txt`、`C:/AI-Sprint/workspace/MC-002/backend/requirements-dev.txt`、`C:/AI-Sprint/workspace/MC-002/backend/pytest.ini`、`C:/AI-Sprint/workspace/MC-002/backend/README.md` | 旧アプリの依存・設定・説明。現行setup参照を切替済み。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/frontend` | 旧React画面、旧静的素材、旧build/依存。communityのDockerfile・型検査から参照なし。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/deploy` | 旧8080 gateway設定。現行は `community/deploy`。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/Dockerfile`、`C:/AI-Sprint/workspace/MC-002/.dockerignore` | 旧ビルド入口。ルートComposeは現行communityをincludeする形へ更新済みなので、旧2ファイルは削除対象。**ルート `compose.yaml` と `README.md` は保持** |
| `C:/AI-Sprint/workspace/MC-002/qa/tests`、`C:/AI-Sprint/workspace/MC-002/qa/playwright.config.ts` | 旧8080のjourney/collection/art試験。現行のQAとは別。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/qa` | 当初は現行QA/動画から依存参照があり一括削除不可だった。主担当がpackage/lock/node_modulesをcommunity/qaへ移設し参照更新済み。更新後の現行QAが旧パスを使わないことを確認して残部を削除可能 |
| `C:/AI-Sprint/workspace/MC-002/scripts/verify_container.py` | 旧8080、旧コンテナー名/ネットワーク専用。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/scripts/prepare_art.cjs` | 旧 `frontend/public/art` の生成専用。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/scripts/package_release.py` | 旧名のZIP/bundleを全追跡ファイルから再生成。現行配布の対象境界と名称が違うため旧実装は削除対象 |
| `C:/AI-Sprint/workspace/MC-002/project/bootstrap_tickets.py`、`C:/AI-Sprint/workspace/MC-002/project/finalize_tickets.py` | 旧T01〜T18/BUGの一回限りの取込・完了処理。現在のチケットCLIから呼ばれない。旧実績を再投入する危険もあるため削除対象。台帳本体は保持 |
| `C:/AI-Sprint/workspace/MC-002/presentation/build.mjs` | 旧13枚・水門/収集資料の固定生成器。旧sourceとして削除対象 |
| `C:/AI-Sprint/workspace/MC-002/presentation/render.ps1` | 旧資料用の再描画補助。現在の新版スライド作成は後続であり、旧generatorソースとして削除対象。旧PPTX/PDF成果物は保持 |
| `C:/AI-Sprint/workspace/MC-002/old/v1.1` | 旧ソースZIPと旧文書の複製。現行からの実行参照なし。Git履歴の保全を確認済みなので旧ソース保管場所として削除対象 |
| `C:/AI-Sprint/workspace/MC-002/outputs/tang-you-chi-source.zip` | 旧ソース配布物85,610,168 bytes。現行配布物ではないため削除対象 |
| `C:/AI-Sprint/workspace/MC-002/old/v1.1/source-with-history.zip` | 上記と同サイズの旧ソース/履歴複製。旧manifestのrevisionを現在Git内で確認。削除対象 |
| `C:/AI-Sprint/workspace/MC-002/outputs/tang-you-chi-history.bundle` | 42,382,903 bytesの旧配布履歴複製。主担当の指示で削除対象。ただし履歴正本 `.git` は保持。下記照合によりbundle内の先端が現在HEADの祖先と確認済み |
| `C:/AI-Sprint/workspace/MC-002/outputs/release-manifest.json` | 旧ZIPを参照する現存manifest。旧配布物と同時に削除対象 |

`backend/.backend-test-tmp` のような試験一時領域はアプリソースとは別。DBが含まれる可能性があるため、親 `backend` を無条件でまとめて消さず、保護範囲と分けて主担当が判断する。調査時に `backend/data` は存在しなかったが、削除直前の再確認が必要。

## 現行community内部の未使用部分・改修が先の箇所

| 絶対パス | 判断 |
|---|---|
| `C:/AI-Sprint/workspace/MC-002/community/backend/app/images.py` | ファイル全体は保持必須。現行で画像再符号化・削除写真cleanup・worker境界を使用。未使用なのは旧ONNXの `LocalClassifier` 部分。mainは `ImageGuidance()` を使う。クラスと専用importの撤去はbackend担当が実施予定 |
| `C:/AI-Sprint/workspace/MC-002/community/backend/app/config.py` | 設定本体は保持。旧 `model_dir` のみ撤去/参照整理候補 |
| `C:/AI-Sprint/workspace/MC-002/community/backend/requirements-model-legacy.txt` | 通常起動/通常依存が使わない旧推論依存。旧sourceとして削除候補 |
| `C:/AI-Sprint/workspace/MC-002/community/scripts/verify_model.py` | 旧ONNXモデル推論確認専用。現行MOCを検証しない。削除候補 |
| `C:/AI-Sprint/workspace/MC-002/community/backend/tests/test_api.py` | 全体は現行テストなので保持。skip済み `test_real_model_uses_pixels` とLocalClassifier importだけが旧部分 |
| `C:/AI-Sprint/workspace/MC-002/community/backend/tests/test_image_guidance.py` | 現行のモデル不要/非推論保証なので保持。LocalClassifierを直接monkeypatchする箇所は、旧クラス除去後も外部AI/推論ライブラリが使われない検査を維持する形へ修正 |
| `C:/AI-Sprint/workspace/MC-002/community/scripts/verify_container.py` | 現行Docker保護の検証に価値はあるが、旧8080健康・MODEL_DIR・model mount必須条件が残る。そのまま現行合格判定に使わず、現行条件へ修正するか後継検査へ統合 |
| `C:/AI-Sprint/workspace/MC-002/community/scripts/verify_marketplace_persistence.py` | schema2固定、旧8080健康を要求する過去の移行検査。現行schema10を拒否する。旧sourceとして削除候補。現行保存検査は次項の汎用スクリプトを保持 |
| `C:/AI-Sprint/workspace/MC-002/community/scripts/full_snapshot.py` | DB+media保全の現行運用なので保持必須。ただし `models/manifest.json` 必須読取を廃止/任意化してモデル不要の現行環境へ整える。過去snapshotのruntime.json互換は壊さない |

この棚卸し時点では、現行フロント45ファイルをmain.tsxからリテラルimportで辿り44ファイルに到達し、残る `vite-env.d.ts` は型宣言としてtsconfig対象だった。バックエンド55 Pythonファイルもmainからの相対importで48ファイルに到達し、残りはパッケージ初期化ファイルだった。したがってcommunityの画面/業務モジュールを名前だけで「旧」として削除する根拠はない。これは未使用関数や実行時到達性の完全解析ではない。

## 残すべき現行ソース・試験・運用

- `C:/AI-Sprint/workspace/MC-002/community/backend/app`：現在の認証、画像、講、事業者相談、訪問、振り返り、行事、再開状態、日帰り。schema1〜10の移行関数も旧DBを読めるため現行機能であり削除しない。
- `C:/AI-Sprint/workspace/MC-002/community/backend/tests`、`C:/AI-Sprint/workspace/MC-002/community/backend/requirements.txt`、`C:/AI-Sprint/workspace/MC-002/community/backend/requirements-dev.txt`：現行受入/回帰と依存。旧モデル専用部分だけ分離して整理。
- `C:/AI-Sprint/workspace/MC-002/community/frontend`：src、public、package/lock、Vite/TypeScript/lint設定、現在の品質計測と画像生成補助。最新和風画像を含む現行素材を保持。
- `C:/AI-Sprint/workspace/MC-002/community/qa`：現行講/写真/同意/左右認証/再開/性能等の検査と画面取得。移設されたpackage/lockも保持。
- `C:/AI-Sprint/workspace/MC-002/community/compose.yaml`、`C:/AI-Sprint/workspace/MC-002/community/Dockerfile`、`C:/AI-Sprint/workspace/MC-002/community/.dockerignore`、`C:/AI-Sprint/workspace/MC-002/community/deploy`、`C:/AI-Sprint/workspace/MC-002/community/assets`：現行ビルド・配信・初期素材。
- `C:/AI-Sprint/workspace/MC-002/community/scripts/start.ps1`、`C:/AI-Sprint/workspace/MC-002/community/scripts/full_snapshot.py`、`C:/AI-Sprint/workspace/MC-002/community/scripts/snapshot_worker.py`、`C:/AI-Sprint/workspace/MC-002/community/scripts/test_snapshot.py`：現行起動/保全/復元の基盤。startの旧8080保持という説明だけ最新方針へ更新。
- `C:/AI-Sprint/workspace/MC-002/test/integration/verify_journal_storage.py`、`C:/AI-Sprint/workspace/MC-002/test/integration/verify_journal_snapshot_rows.py`、`C:/AI-Sprint/workspace/MC-002/test/integration/daytrip_snapshot_compare.py`：名前にjournalがあっても版指定・全行保持・画像保存検査に使う汎用現行ツール。
- `C:/AI-Sprint/workspace/MC-002/community/scripts/measure_backend_quality.py`、`C:/AI-Sprint/workspace/MC-002/community/quality`、`C:/AI-Sprint/workspace/MC-002/community/scripts/daytrip_policy_report.py`：現行品質・根拠の計測。
- `C:/AI-Sprint/workspace/MC-002/community/scripts/create_intro_video.mjs`、`C:/AI-Sprint/workspace/MC-002/community/scripts/encode_intro_video.py`：今回必要な紹介動画の生成。QA依存をcommunityへ切替済み。
- `C:/AI-Sprint/workspace/MC-002/scripts/setup-local.ps1`：旧パスだったが、主担当が `community/backend/requirements-dev.txt` と `community/frontend` へ修正済み。現行環境構築として保持。
- `C:/AI-Sprint/workspace/MC-002/scripts/tickets.py`、`C:/AI-Sprint/workspace/MC-002/scripts/test_tickets.py`、`C:/AI-Sprint/workspace/MC-002/project/board-template.html`、`C:/AI-Sprint/workspace/MC-002/project/check_board.cjs`：現行チケット管理。check_boardのPlaywright参照はcommunity/qaへ変更済み。
- `C:/AI-Sprint/workspace/MC-002/scripts/analyze_community_samples.py`、`C:/AI-Sprint/workspace/MC-002/scripts/analyze_community_rationale.py`、`C:/AI-Sprint/workspace/MC-002/scripts/analyze_audience_trends.py`、`C:/AI-Sprint/workspace/MC-002/scripts/review_audience_trends.py`、`C:/AI-Sprint/workspace/MC-002/scripts/analyze_survey_content.py`、`C:/AI-Sprint/workspace/MC-002/scripts/render_survey_summary.py`：現行CSV/UX設計根拠の再現用。アプリの実行時依存ではないが現在の成果物に必要。
- `C:/AI-Sprint/workspace/MC-002/scripts/analyze_samples.py` と `C:/AI-Sprint/workspace/MC-002/scripts/test_samples.py` は旧analytics-v2 DB取込の再現用で、現行community分析群はimportしない。元データ品質の再現を今後も成果物に含めるなら保持、不要なら2本だけを削除対象へ追加する。既存analytics DB/キーは削除しない。

## 無条件で保護するもの

`C:/AI-Sprint/workspace/MC-002/.git`、`C:/AI-Sprint/workspace/MC-002/.gitignore`、`C:/AI-Sprint/workspace/MC-002/data`、`C:/AI-Sprint/workspace/MC-002/community/backups`、現存する全DB・WAL/SHM・media・snapshot、Dockerの全データvolume、秘密情報とキーを保護する。`community/data` は調査時には存在しなかったが、存在した場合も同様に保護する。

`C:/AI-Sprint/workspace/MC-002/project/tickets.json`、`C:/AI-Sprint/workspace/MC-002/project/events.jsonl`、`C:/AI-Sprint/workspace/MC-002/project/revisions`、設計/タスク/変更履歴/評価記録は監査データであり不要ソースではない。旧ソースへの過去リンクを消すために過去イベントを書き換えず、削除の記録とGit revisionで追跡可能にする。

`C:/AI-Sprint/workspace/MC-002/.venv`、`C:/AI-Sprint/workspace/MC-002/.tools`、`C:/AI-Sprint/workspace/MC-002/community/models`、現行node_modules、品質ツールruntimeは今回中身を走査していない。開発環境/モデル資産を不要ソースと同一視して消さない。旧フロント等の専用依存キャッシュは、現在の参照がないことを確認した主担当が別扱いで除去できる。

旧PDF/PPTX・画像・試験JSON/XML・動画はソースではなく成果物/証拠。今回の旧generator削除と区別して保持する。特に `C:/AI-Sprint/workspace/MC-002/presentation/node_modules` はCodexのWindowsApps配下へのJunctionである。外部リンク先へ再帰しない。触らないかリンク自体だけを安全に扱い、外部ランタイムを削除対象にしない。

## 実施した照合と削除後の受入条件

読取対象はCompose/Dockerfile/README、実装import、package設定、scripts/tests/QA。`rg --files` の走査はnode_modules・仮想環境・モデル・backup・秘密名を除外した。DB/画像/秘密の内容や元CSVは読んでいない。Docker/ブラウザー/重い試験は起動していない。

旧 `old/v1.1/archive-manifest.json` にあるcommit `05c3d878e1a42a3f62cdcb704e415282ea5af8ac` は現在の `.git` にcommitとして存在する。旧history.bundleの先端は2参照/一意commit1件で、その1件が現在Gitに存在し、現在HEADの祖先であることを読取専用のGit操作で確認した。旧ZIPの大容量展開/CRC再検証はしていない。従ってGit履歴を残し重複配布物を削除する境界は成立する。

主担当は削除後、現行build/型検査/API試験、QA依存解決、モデルなし起動、snapshot補助のモデル不要化、旧パス残存を確認する。DB/写真は削除前後の件数/ハッシュで保全確認する。文書の旧手順は現在の起動先へ直し、旧試験を新実装の成功根拠へ転用しない。削除と修正をGitへ記録し、`.git` 自体や保全データはその作業に含めない。
