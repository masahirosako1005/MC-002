# 日帰り版：Bandit B608の19件の判定

2026-11-10。現行Python全55モジュールの測定結果に対する読取レビュー。**19件すべてについて、現在の呼出経路から利用者の文字列がSQL構文へ挿入される経路は確認しなかった。** 固定された識別子・条件句・DDLの文字列構築を検出したものと判断する。「既存だから安全」という判断ではない。抑制追加、ルール変更、製品コード変更は行っていない。

## 測定と対象

Bandit 1.9.4、全 `community/backend/app`、`--ignore-nosec`。B608（文字列構築によるSQL注入の疑い）がMedium 19件、High 0件、解析エラー0件。ConfidenceはMedium 7件・Low 12件。検知数は19のまま保持する。

根拠は [生結果](../community/artifacts/quality/daytrip-final/bandit.json)と[条件・ソースSHA-256](../community/artifacts/quality/daytrip-final/summary.json)。下記5ファイルの現在のSHA-256が測定記録と一致することを確認した。テスト、補助スクリプト、依存パッケージ、フロントエンドはこの判定の対象外。

## 入力経路の確認

| 対象・件数 | 構文に結合する部分と値の経路 | 評価・根拠 |
|---|---|---|
| [security.py](../community/backend/app/security.py):37、1件 | `current_session` の `table` はコード内の `stage_sessions` / `sessions` の二択。Authorizationの有無で分岐するが、ヘッダーの文字列自体を表名へ代入しない。トークンのhashと期限は `execute(sql, tuple)` の `?` へ渡す。 | 固定表名の選択による検出。悪いBearer形式は認証失敗としCookieへフォールバックしない。トークン内容がSQLとして再解釈される箇所はない。 |
| [main.py](../community/backend/app/main.py):153、1件 | `logout` の表名も同じ二択。削除対象は認証済みsessionのtoken_hashを `?` へ渡す。 | 固定表名の選択による検出。`authenticated` とCSRF検証を通した後に実行し、任意の表名やWHERE式をHTTPから受け取らない。 |
| [marketplace/service.py](../community/backend/app/marketplace/service.py):164,169,173,175、4件 | `messages` の表/列は `party_messages` / `party_id` または `consultation_messages` / `consultation_id` の固定組。呼出元 [router.py](../community/backend/app/marketplace/router.py):72,76,104,108が `party` / `consultation` を定数で渡す。scope_id、本文、著者、時刻、取得IDはすべて `?` へ渡す。 | 固定識別子の選択による検出。問い合わせ前に講の所属、または相談の共有継続と担当事業者/講所属を検証。再送結果IDも本人・操作・送信キーに対応する保存行から取得し、パラメーターとして渡す。本文やURLのIDを識別子へ流用しない。 |
| [service.py](../community/backend/app/service.py):32、1件 | `invalidate` は `cid` の有無で固定文字列 ` AND community_id=?` を付けるだけ。`uid` と `cid` は引数タプルで渡す。 | 固定条件句の選択による検出。退出・本人の投稿/関心変更から呼ばれ、利用者のcommunity_idをSQLの文字列へ連結しない。条件なしの分岐も本人の提案に限る。 |
| [personalization/schema.py](../community/backend/app/personalization/schema.py):30,34,38,40,44,47,49,53,55,58,61,64、12件 | `_reset_all`、`_reset_circle`、`_provider_guard` はソース内の固定SQL。`DEFAULT_FILTERS` は空文字と固定の `all` 値から構成するJSON定数。HTTPの検索語、DBのfilters_json、環境変数をDDLへ組み込まない。`NEW` / `OLD` はSQLiteトリガーの行値参照であり、SQL文字列の生成ではない。 | 固定DDLの組立てによる検出。12件は12個の独立した注入入口ではなく、講退出トリガー内で同じ式が複数検出された箇所も含む。起動時の移行で固定DDLを実行し、利用者の保存条件は別のパラメーター化SQLで処理する。 |

## 残るリスクと判定の限界

- 現在の19件を、未確認の実脆弱性19件や「修正して0件」と表現しない。今回確認した入力経路に限り、利用者入力によるSQL注入としては非該当と判断した。
- 今後、表名・列名・条件句をリクエスト、DB本文、外部設定から選ぶ設計へ変える場合は再レビューが必要。値のプレースホルダーは識別子を保護しないため、固定の許可リストを維持する。
- `DEFAULT_FILTERS` を任意の文章や利用者設定へ置換してDDLへ連結すると、この判断は成立しない。現在の固定値には引用符の持込み経路がないことを確認した。
- 認可の正しさ、共有失効、CSRF、復旧、XSS、依存脆弱性などはB608だけで保証できない。この読取レビューでは新しい攻撃用入力の網羅試験や外部侵入試験は行っていない。既存の権限・保存試験の成功を、それらの全面的な検証へ拡張しない。
- ソースまたはSQLiteファイル自体を任意に変更できる攻撃者、未知のSQLite/依存パッケージの脆弱性は今回の入力追跡の対象外。

実際の注入経路は見つからなかったため、コード凍結を維持した。大会評価・固定C1の加点には使用しない。
