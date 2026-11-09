# 通常実行とSQL指摘の独立レビュー（CP45・Q1）

2026-11-09。対象は今回の通常実行への変更とBandit B608の入力経路。製品コードを変更せずに読んだレビューであり、全脆弱性の不存在やDocker受入完了を宣言しない。CP47のDDLのみレビュー担当自身が実装したため、その箇所は自己確認と主担当の別確認を組み合わせる。

## CP45：推論を使わない写真案内

- `main.py` は `ImageGuidance()` を生成し、`LocalClassifier` を生成しない。旧モデルコード/資産は残すが、通常依存からONNX/NumPyを除き、Dockerのモデルbindと起動前提を外す。旧classifier内の遅延importが存在することと、通常経路で実行されることを区別した。
- `ImageGuidance.inference_enabled=False`、`session=None`。workerのstartはこの状態ではthreadを起動せず、onceも推論へ進まない。外部AI/APIクライアントの追加やキーの探索はない。
- `photo_guidance` は同梱公開素材4枚のバイト列SHA一致だけを事前設定タグに対応付ける。任意写真/別バイト列/ファイル名偽装はmanual空候補。scoreを新たに作らない。画像認識や生成AI推論と称さない。
- uploadは従来のサイズ/形式/画素検証・再符号化成功、必要な場合だけEXIF位置opt-inを処理した後でrawのSHAを調べる。未検証大容量の別解析経路は追加しない。元EXIFを共有画像に残さない。
- 新規manual/guidedは終端状態。旧queued/running/failed/succeededは読込応答でmanualへ投影するが、旧jobsの状態・タグ・score・model_versionを書換えない。旧候補は保存済み候補というmethodで区別する。本人の選択済み投稿タグ/関心を上書きしない。
- 他者feedはanalysis tagsを空にし、methodを `author-selected-tags`、model_versionをnullへ固定する。本人用候補や旧model情報を他者へ出さない。media/analyzeの本人認可と既存CSRFを維持する。
- 講条件、候補保存、事業者の参加承諾、見積の版別双方確認は既存の実保存経路を維持する。画像推論を止めることをアプリ全体の架空成功へ置き換えない。

## 発見した問題と修正確認

最初の変更では `AnalysisWorker.once` の先頭returnが、deleted mediaの物理ファイル再削除も止めていた。投稿削除のunlinkが一時失敗すると、論理閲覧拒否は効くが既存の再試行が消える点を担当へ指摘した。

修正版は `cleanup_deleted_media` を推論から独立させ、startup、明示削除後、onceの推論guard前から呼ぶ。対象はDBで既にdeleted=1の最大32件、storage_keyは32桁hexのjpgに限定し、resolveしたpathがmedia_dir内にあることも確認する。live media、covers、ディレクトリ外を対象にしない。cursorにより古いmissingファイルが後続対象を塞がない。失敗本文/ファイル名をログに出さない。

`test_deleted_photo_cleanup_retries_at_start_without_inference_and_keeps_live_media` は、一時的なunlink失敗中でもAPI閲覧拒否、その後の新app lifecycleで対象ファイル削除、live写真保持、推論thread未起動を検査する。独立レビューではコードと試験内容を確認した。実行結果は主担当/実装担当の最新試験記録と照合する。

`settings` の `deleted-media-cleanup-cursor-v1` は保守用の新しい値で、削除行が32件を超える場合は起動ごとに変わり得る。再起動保全比較ではこのkeyを利用者の保存内容と分ける。settings全表や他の業務表を広く除外して保全を偽装しない。

## Bandit B608：19件の入力経路

現在の `community/backend/app` 全体を `--ignore-nosec` で再走査し、B608が19件であることを再現した。固定の識別子/SQL断片の結合にも検出されるため、件数だけでSQL注入と判断せず、結合元と値の渡し方を追った。抑制設定で結果を消していない。

| 箇所 | 件数 | 結合元と認可 | 判定 |
|---|---:|---|---|
| `security.current_session` | 1 | tableはBearer有無に応じた `stage_sessions` / `sessions` のリテラル二択。header文字列をtable名にしない。token hash/期限はplaceholder | 外部入力のSQL構文化なし |
| `main.logout` | 1 | tableは同じリテラル二択。認証済みsessionのhashはplaceholder。誤BearerをCookieへfallbackしない既存境界を維持 | 外部入力のSQL構文化なし |
| `marketplace.service.Marketplace.messages` | 4 | table/columnは `party_messages,party_id` / `consultation_messages,consultation_id` の固定組。routeはscope定数を渡す。先にparty/consultation認可。scopeID、本文、author、再送key結果IDはplaceholder | 外部入力のSQL構文化なし |
| `service.invalidate` | 1 | 付加するWHERE句は固定の `AND community_id=?` の有無のみ。user/communityIDはplaceholder | 外部入力のSQL構文化なし |
| `personalization.schema` | 12 | trigger DDLを固定文字列で結合。`DEFAULT_FILTERS` はソース内の固定dict、reset句/guardも固定SQL。実行時入力・DB本文・HTTP値をDDLへ補間しない | 入力由来のSQL注入経路なし。自己実装箇所は主担当も別確認 |

これは当該19件についての判断であり、安全性全体をB608だけで評価しない。条件分岐やtable名の組み方を将来変更する場合は再確認する。認証、CSRF/Origin、回数制限、ログ、依存関係、保存の検証は別の証拠を維持する。

## 検証の境界

CP47の本人状態は隔離API15/15成功、新app lifecycle再読と別人分離、CAS競合、権限失効の非復活、非公開area拒否、非空移行/rollbackを確認済み。これは本レビュー担当が実行した結果。CP45の通常Docker起動、写真画面、最新の全体回帰は主担当が別途実施する。C1加点の残りは `COMMUNITY-EVALUATION-AUDIT.md` を参照する。
