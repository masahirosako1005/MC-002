# 削除済み写真のバックアップ・復元検証

対象: CQ15 / 2026-11-09。実行結果は `community/artifacts/deletion-restore.json` を正本とする。2026-11-09 16:52 JST の実行で11項目すべて成功（約7.2秒）。RuffとPython構文検査も成功した。稼働中のアプリ・保存volumeは変更していない。

## 検証すること

`test/integration/verify-deletion-restore.py` は、実アプリの初期化と Service を使って検証専用 DB を作る。合成画像を3件投稿し、公開済み1件を保持、下書き1件と公開済み1件を削除する。削除処理を SQL で模倣せず、実際の `delete_post` による論理削除・画像ファイル削除を通す。

既存 `community/scripts/snapshot_worker.py` をそのまま使い、バックアップ・検証・新しい空領域への復元を実行する。確認範囲は次のとおり。

- 未チェックポイントのコミット済み WAL を含むバックアップ。
- 全アプリケーション表の件数と全行の SHA-256 一致。`settings` も除外しない。
- 削除済み写真2件の `deleted=1`、投稿の `deleted` 状態、候補タグ消去、写真ファイル不在。
- 復元後も実 Service の画像読取が削除済み写真に404を返すこと。
- 保持した写真の公開状態、実 Service からの読取、画像バイト列の SHA-256 一致。
- manifest・ファイル一覧・画像ハッシュ・DB整合性の既存検証。
- 空でない復元先への二度目の復元拒否と、その後の全行一致。

## 隔離と再実行

プロジェクトの Python で `test/integration/verify-deletion-restore.py` を実行する。Docker のローカル構築済み app イメージが必要。イメージ取得は `--pull=never`、補助コンテナはネットワークなし、読み取り専用ルート、権限削減、メモリ256MB、CPU1個で実行する。アプリの停止・起動や実運用 volume のマウントは行わない。

毎回 `community/artifacts/snapshot-tests/deletion-restore-<乱数>/` に source / snapshot / restored を新規作成する。source は補助コンテナに読み取り専用で渡す。既存領域を消して使い回さない。検証用DB・写真は Git 管理外、公開する結果には原文・認証情報・写真識別子を含めず件数とハッシュを記録する。

## 限界と保守状態

この試験は合成データによる実復元であり、稼働中の実データを復元した実績や、電源断・OS障害の耐性を示すものではない。全行の厳密比較は復元直後に行い、復元後のアプリ再起動は含めない。

削除ファイル再処理のカーソル `settings.deleted-media-cleanup-cursor-v1` は、起動時の保守処理により変化し得る。別の再起動保持試験で差が出た場合はこのキーだけを保守状態として区別し、`settings` 表全体を比較対象から外さない。本試験の source / snapshot / restored 比較ではこのキーも完全一致を要求する。
