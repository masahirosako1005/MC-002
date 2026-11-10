# EV02 S02 / S04：本人のパスワード変更とローカル照合

更新日：2026-11-10。対象は現行ルート `backend/` の本人認証変更機能。初期 ASVS 台帳は初期観測として保持し、この文書を差分証拠とする。並行実装中の現地 VR / おみくじ機能はこの評価に含めない。実利用者の再訪効果や大会の得点は測定していない。

## 契約と保護範囲

- `POST /api/account/password` の JSON は `current_password` と `new_password` のみ。本人 ID は受け取らず、認証済みセッションから決める。現在値は 1〜128 文字、新しい値は 12〜128 文字。空白や Unicode を保存・認証前に改変しない。
- 通常 Cookie と Stage Bearer の既存認証、Origin 制限、CSRF 検証を使う。入力は `SecretStr`、不正な入力の応答には値を含めない。新しいパスワードの確認入力は UI 内で照合する。
- 現在のパスワード違い、同一パスワード、新規則違反は 422。無効・期限切れ・競合で失効したセッションは 401。422 は既存 UI の自動ログアウト条件にせず、入力を訂正できる。
- 現在値の照合と新しいハッシュ計算は DB トランザクション外。既存の共通 KDF 制限を使用する。書込み時には `BEGIN IMMEDIATE` 内で token の所属 table / user / expiry / CSRF と、user の salt / hash / login_enabled / username を再検証する。計算中のログアウト、期限切れ、別のパスワード変更、無効化を上書きしない。
- fresh salt と新 hash の保存、本人の `sessions` と `stage_sessions` の全削除を同じトランザクションで実行する。失効処理が失敗した場合はパスワード変更もロールバックする。他人の認証情報とセッションは変更しない。
- 成功は `200 {"ok":true,"reauthentication_required":true}`。変更を行った画面も再ログインが必要。Cookie の削除応答は Cookie 認証の要求だけに付ける。Stage に併存する別の人の Cookie を消さない。同じ人の別画面は次の API 要求で失効を検出するため、既に画面に描かれた内容を即時遠隔消去する機能ではない。
- 専用の接続元単位の上限は 1 分 5 回。これは現在の単一プロセス・ローカル運用向けの既存メモリー内制限。多プロセスや公開配備にまたがる共有制限を提供したとはしない。

実装：`backend/app/account/{schemas,service,router}.py`。既存 `main.py`、`security.py`、`residence/service.py` への接続と共通 KDF は backend 担当が所有。アカウント UI は frontend 担当の別証拠で確認する。

## 既知の弱いパスワードの照合

`backend/app/password_policy.py` を新規登録と本人によるパスワード変更に適用する。既存アカウントの通常ログイン、固定初期資料のパスワードを強制変更しない。

SecLists の作者公式リポジトリ、固定 commit `a1a06ab57c3f4efc450d80738a72c11597aac81a`、MIT license を使用した。

| 固定公開原本 | SHA-256 | 長さ条件を満たす casefold 後の種類数 |
| --- | --- | ---: |
| [xato 100 万行版](https://github.com/danielmiessler/SecLists/blob/a1a06ab57c3f4efc450d80738a72c11597aac81a/Passwords/Common-Credentials/xato-net-10-million-passwords-1000000.txt) | `424a3e03a17df0a2bc2b3ca749d81b04e79d59cb7aeec8876a5a3f308d0caf51` | 46,146 |
| [NCSC 由来の公開一覧](https://github.com/danielmiessler/SecLists/blob/a1a06ab57c3f4efc450d80738a72c11597aac81a/Passwords/Common-Credentials/100k-most-used-passwords-NCSC.txt) | `c2e5696882c603b76bb67a47ee970897e5a76fc4c3f5547abe3d0ca340c576e0` | 1,197 |

取得は公開ファイルに対してのみ行い、プロジェクトのコード・利用者の入力を送信していない。原本の UTF-8 を行単位に分割し、元の文字列が 12〜128 Python Unicode codepoint のものを選び、照合用に casefold した集合の和を取る。その UTF-8 SHA-256 を昇順で LF 区切りにした派生物のみ同梱する。原本全文の重複コピーは保存しない。

- 派生物：`backend/app/account/data/common-passwords.sha256`、46,825 件、3,043,625 bytes。
- 派生物 SHA-256：`466d943ca1e1a67b32cff070a41a4d99bee8db86347ad422cbae1ed976b7cd7c`。
- [MIT 許諾文の固定原本](https://github.com/danielmiessler/SecLists/blob/a1a06ab57c3f4efc450d80738a72c11597aac81a/LICENSE) を `LICENSE-SecLists.txt` として保持。SHA-256 は `3dbdc93d5f8829de0941744841730a09c106d0732e5ae0e98ca1d77be7ded66c`。
- 出典・原本件数・変換規則・全ハッシュは同じフォルダの `provenance.json`。起動時に固定 SHA と件数と形式を検査し、不足・破損時に空リストで続行しない。
- アカウント ID、ID + local / password、サービス名の単純な数字・区切り文字つき候補も拒否する。これは文脈に基づく補助規則であり、本人に関する情報を収集・推測する仕組みではない。名前を含む十分に長い別の文章を一律拒否しない。
- casefold と区切り文字の除去は弱さの照合だけに使う。保存する KDF と現在値の検証には元の文字列をそのまま渡す。外部問い合わせや PW / token / body のログ出力を追加しない。

この一覧は固定された過去の公開集合である。すべての漏洩パスワード、最新の漏洩、他サイトでの再利用、日本語固有の弱い候補を網羅していない。ASVS 6.2.4 の既知候補照合、6.2.11 の限定的文脈拒否を確認できても、ASVS 全面適合や漏洩パスワードの網羅的な検知とは主張しない。6.2.12 への証拠は上記の固定集合との照合範囲に限る。SHA-256 一覧自体は公開弱語彙の再現用データであり、利用者の保存パスワード方式ではない。

## 検証履歴

初回：`python -m pytest test/backend/test_account_security.py -q --tb=short`、**28 passed / 1 failed、27.42 秒**。失敗は `test_local_policy_rejects_common_contextual_and_out_of_bounds[PASSWORD123456-owner]` の `Failed: DID NOT RAISE <class 'fastapi.exceptions.HTTPException'>`。先頭 3,000 件だけを採る最初の案では既知の単純候補を取りこぼした。

改善：元の全長さ適合候補を採り、同じ固定版の NCSC 由来一覧を加えた。元の 100 万行だけにも上記候補が存在しないことを確認したため、件数拡大だけで解決したとは記録しない。失敗した入力と期待値を維持して再検証する。

改善後は **29 passed、23.88 秒**。固定 SQL 文への整理後、他担当との一時領域の衝突を避けて `--basetemp=test/fixtures/runtime/ev02-account-final-1411 -o cache_dir=test/fixtures/runtime/ev02-account-cache-final-1411` を付けた最終の専用試験も **29 passed、26.59 秒**。Ruff は固定 `quality/ruff.toml` で指摘なし。Bandit は新規 `account/` と `password_policy.py` に対して指摘なし。除外・抑制を追加していない。

対象は本人変更、両種セッション失効、他人保持、旧値違い・同一値・既知値・文脈値の拒否、途中のログアウト・期限切れ・無効化・PW/CSRF 変更競合、DB 失敗時の原子性、table 間 token 分離、Unicode / 長さ境界、一覧改ざん検知、実アプリ API / CSRF / Origin / 入力値非露出 / 新規登録との規則共有 / 頻度制限。全体 pytest、Docker、実画面検証をこの担当は重ねていない。

`account/data/.gitattributes` の `-text` により Git checkout 時の改行変換を無効にした。派生一覧のフィルタ適用前後の Git blob ID はともに `c84cd316123c46a934b568962e18e91713f42e95`。他の同梱ファイルも text 属性 unset を確認した。`Dockerfile` は `backend/app` 全体を COPY するため派生一覧を含む。既存 `.dockerignore` の `**/password*` が新 policy モジュールを除外する問題を発見し、主担当が末尾に `!backend/app/password_policy.py` の限定例外を追加したことを確認した。既存の秘密情報除外規則自体は維持。実 Docker build の確認は主担当へ引き継ぐ。

## S05 / S06 と未達事項

S05 の認証監査は別の中規模変更を要する。専用 DB 表と保持上限・参照権限・イベント一覧が必要。PW、token、CSRF、会話・リクエスト本文を保存しない。成功だけでなく失敗を記録する必要があり、認証失敗で rollback するトランザクションの中だけに監査行を書いても残らない。安全な別 transaction と書込み失敗時の扱いを設計し、ログ自体の濫用・肥大化を検証する必要がある。

S06 の idle timeout も別の中規模変更を要する。両セッション表の `last_seen` 追加・既存行移行・書込み頻度の制限・期限切れの並行操作拒否が必要。API の自動取得を人の操作として扱うと不在でも期限が延び続けるため、操作の定義と再認証時の UI を合わせて決める。既存の絶対有効期限はあるが、本変更で idle timeout を追加したとはしない。

パスワードを忘れた場合の回復、セッション一覧・選択失効、認証操作の通知、MFA、監査、idle timeout は今回の小さい変更の完了条件に含めない。パスワード変更時の本人の全失効を、これらすべての実装済みと扱わない。初期 ASVS の 7.5.1 は変更機能の追加で適用範囲が変わるため、最終台帳更新時に再判定が必要。
