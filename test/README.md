# 現行テスト

実行する試験のソースはこの `test/` にまとめる。アプリの実装はPJ直下の `frontend/` と `backend/`、運用補助は `scripts/`、実行結果は `artifacts/`、合成テストデータは `test/fixtures/` に置く。実DB・写真・バックアップをfixtureへ移さない。

| 場所 | 対象 | 稼働アプリへの操作 |
|---|---|---|
| `backend/` | API、認証、所属、投稿、講、事業者、訪問、日帰り、移行、再開状態 | なし。隔離した合成DBとASGIを使用 |
| `tooling/test_*.py` | チケット台帳、CSV取込、品質確認ツール | なし。合成入力と一時台帳を使用 |
| `tooling/check_board.cjs` | ローカルのチケットボード表示 | ボードを読むだけ。Edgeを使用 |
| `browser/verify-*.mjs` | 実際の画面、左右認証、操作、表示、共有 | 8081の稼働アプリを操作。合成アカウントを使用 |
| `browser/capture-*.mjs` | 画面証拠の取得補助 | 8081へログイン/閲覧。自動回帰の一括対象には含めない |
| `integration/test_snapshot.py` | WALを含む合成DB/写真の保全・隔離復元 | 既存イメージで一時コンテナーを使用。稼働volumeを操作しない |
| `integration/verify-deletion-restore.py` | 削除済み写真と保持写真を隔離復元して照合 | 合成fixtureと一時コンテナーだけ |
| `integration/audit-personalization.py` | 現在DBの件数/整合性監査 | コンテナー内から読取専用。件数/真偽値のみ出力 |
| `integration/verify_journal_storage.py`、`verify_journal_snapshot_rows.py` | 移行/再起動前後の保存照合 | 明示したモードと保存先で個別実行。通常一括試験には含まない |
| `integration/daytrip_snapshot_compare.py`、`verify_enrichment.py` | 保存物2版の全行/画像比較 | PJ内バックアップを読取。実DBは変更しない。引数付き個別実行 |
| `browser/verify-journal-restart.mjs` | 再起動前後の保存確認 | 稼働アプリの再起動あり。integrationグループに含む |

## 一括実行

PJ直下で実行する。事前に `scripts/setup-local.ps1` で依存を準備できる。テスト入口はビルド・インストール・アプリ起動を自動実行しない。

```powershell
# 既定：隔離したPython試験＋ブラウザーソースの構文/依存確認
.\.venv\Scripts\python.exe test/run.py

# 試験の検出と構文確認。実アプリの操作は実行しない
.\.venv\Scripts\python.exe test/run.py --collect-only

# 一覧
.\.venv\Scripts\python.exe test/run.py --list

# 対象を絞る
.\.venv\Scripts\python.exe test/run.py --suite unit
.\.venv\Scripts\python.exe test/run.py --suite browser --case verify-login
.\.venv\Scripts\python.exe test/run.py --suite integration --case test_snapshot
```

`--suite browser` は再起動検査を除く画面試験とボード検査を順に実行する。`--suite integration` は保存/復元、読取監査、再起動検査を順に実行する。`--suite all` はlocal・browser・integrationを実行する。ブラウザー/全体/再起動検査は同じPCでの操作・投稿編集中や他の試験と重ねない。既存の回帰シナリオには作成した講や投稿を保存/取消するものがあるため、ローカルの検証アカウントで行う。

`--collect-only --suite all` はPython試験と構文確認に加え、実アプリ用試験のファイル一覧を確認する。実アプリ用試験は `not_executed` に明記する。構文・依存・収集の成功を画面操作の成功に数えない。

## 個別実行

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c pytest.ini test/backend -q
.\.venv\Scripts\python.exe -B -m pytest -c pytest.ini test/tooling -q
.\.venv\Scripts\python.exe -B -m pytest -c pytest.ini test/backend/test_daytrip.py -q
node test/browser/verify-login.mjs
node test/tooling/check_board.cjs

# 稼働アプリを再起動する検査。現行の期待版は11
node test/browser/verify-journal-restart.mjs --schema 11
```

root `pytest.ini` がPythonの参照先と通常対象を指定する。通常のpytestはbackend/toolingだけを収集し、Dockerを使うintegrationは自動実行しない。API試験同士の `conftest` /補助関数importはbackend配下で維持する。

`pytest.ini` は旧版や依存まで探索を広げないため、PJ直下の標準入口として保持する。`test/run.py` と `scripts/quality_check.py` もこの設定を明示して実行する。`test/conftest.py` は一時領域・pytestキャッシュを `test/fixtures/runtime/` の子ディレクトリに限定し、旧 `.backend-test-tmp` / `.test-work` 等への指定を実行前に拒否する。独自の `--basetemp` もこの範囲内に置く。

標準の試験・品質runnerは子プロセスへ `PYTHONDONTWRITEBYTECODE=1` を渡し、ソース内の `__pycache__` を再生成しない。直接pytestを起動する上記手順も `-B` を付ける。バックエンド品質計測のRuff・複雑度検査は `--no-cache` を使い、ルート `.ruff_cache` を再生成しない。

ブラウザー依存の正本は `test/browser/package.json` とlockファイル。導入だけなら `npm.cmd ci --prefix test/browser`。紹介動画もこの依存を使う。`scripts/create_intro_video.mjs` は動画の運用生成器なのでtestへ移さない。

## 保存先と結果の扱い

- 一括入口のログ/JSON/JUnit：`artifacts/test-runs/<日時-識別子>/`。
- 画面証拠：`artifacts/browser/`。ボードは `artifacts/tooling/board/`。
- 合成保存/復元の結果：`artifacts/storage/`。
- 一時DB/画像/台帳：`test/fixtures/runtime/`。一括入口は実行ごとに別フォルダを使う。
- 直接pytestの一時領域：`test/fixtures/runtime/pytest-current`。pytestが再作成する専用領域であり、保存したい資料を入れない。
- 旧 `community/artifacts/` は内容を保持して `artifacts/community/` へ移動済み。再起動の運用helperは履歴を `artifacts/community/restart/` に出す。旧キャッシュの残存状況は下記監査記録で区別する。

`result.json` はコマンドごとの終了コード・時間・ログ先と実行/収集の区別を残す。失敗・起動不可・時間超過があれば成功にしない。新しい投稿UIなどでシナリオのラベルや操作が変わった場合は該当試験も更新し、古い画面試験の結果を現在版の成功として流用しない。

2026-11-10の統一確認では、保存先制限と品質runnerの15試験・標準runnerの収集が成功した。その後、明示されたルートの `.backend-test-tmp` と `.test-work` は `test/fixtures/runtime/legacy-root/` の同名フォルダーへ移動し、607ファイルの前後ハッシュ・件数・容量が一致した。元の2パスは残っていない。この移動は削除ではない。[移動記録](../artifacts/test-relocation-result.json)を参照。

この後の削除依頼で、一時領域28・bytecodeキャッシュ19・ツールキャッシュ3の計50フォルダーを再監査したが、自動承認レビューが実行前に `blocked by policy` と拒否した。詳細理由は示されず、この時点の削除0件・残存50件（1,542ファイル、566,089,799 bytes）。別方式・分割・移動での迂回は行っていない。当時稼働中の動画処理と共用していた `community/scripts/__pycache__` は対象から除外した。再生成防止変更後の対象15試験は成功（0.08秒）。[削除要求時の結果](../artifacts/folder-cleanup-test-result.json)、[当時の対象一覧](../artifacts/folder-cleanup-test-inventory.json)、[15試験XML](../artifacts/folder-cleanup-test-tests.xml)を参照。

現行ソースをPJ直下へ統合する後続指示で、親担当が物理移動を実施した（[移動記録](../artifacts/root-layout-move-result.json)）。旧ルートbackendの残骸は `test/fixtures/runtime/legacy-root/backend-root/`、旧community内の試験一時領域も `test/fixtures/runtime/legacy-root/` 配下に分離している。過去の削除・移動記録内のパスは当時の証拠として書き換えない。品質比較は旧 `community/backend/app/` と新 `backend/app/` を同じ識別子に正規化し、配置変更だけを新規指摘や解消と数えない。
