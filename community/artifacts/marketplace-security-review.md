# 三役・中央画面の独立セキュリティレビュー

確認日：2026-11-09。対象はReact/TypeScriptの三役・stageと、Python/FastAPIの追加API・schema 2移行。ローカルHTTP/合成アカウント/架空商品という前提を維持する。

**結論：中重大の認可・整合性の問題2件を指摘し、担当者による修正と回帰試験の証拠を確認した。現時点で未修正の高・中重大の問題は見つかっていない。新Dockerのschema 2移行、14表の再起動保持、schema 2のDB＋写真の隔離復元は実測確認済み。左右2画面の実ブラウザー検証は主担当が継続中。**

このレビューはコードの読取り、契約との照合、担当者の保存結果の確認である。レビュー担当が追加APIの全試験を再実行したという意味ではない。コードは変更していない。FastAPI、React、一般JavaScriptのセキュリティ指針から、所有者・役割の認可、Cookie/CSRF、短期トークン、CSP、postMessage、ログの境界を採用した。

## 指摘と修正

### MS-01 / P2：無効化した事業者の権限が兼任アカウントに残る

- **修正前の条件**：事業者staffである同じ利用者が、ある旅行計画の一般メンバーも兼任する。事業者を無効化すると、相談へのアクセスは旅行者メンバーとして認められる。一方、`can_close`の検索がstaff行のactiveだけを見ていたため、非代表者でも事業者権限で閉鎖できた。
- **影響**：閲覧権限しか残らない利用者が相談を閉じ、正当な相談を妨げる。別社・一般第三者の情報漏えいとしては分類していない。
- **修正**：`backend/app/marketplace/service.py:276`のstaff検索をprovidersとJOINし、staffと事業者の両方のactiveを要求。認可の入口`service.py:269`と条件を揃えた。
- **証拠**：`backend/tests/test_marketplace.py:195`の`test_disabled_provider_staff_cannot_close_as_ordinary_traveler`。兼任状態を合成fixtureで作り、読取り200・can_close=false・閉鎖404・open維持を確認。担当者の対象実行1 passed/0.85秒、その後の通常全体試験にも含まれる。
- **状態**：修正コードを読取り確認済み。担当者のHTTP回帰試験成功。新Docker/ブラウザーでの同条件再現は未実施。

### MS-02 / P2：退出拒否と計画作成の競合

- **修正前の条件**：代表者がopen計画を持つかの確認がmainの読取トランザクション、退出更新がServiceの別writeトランザクションだった。その間に別要求が旅行計画を作成できた。
- **影響**：open計画を残したまま代表者が退出し、計画が通常の画面から参照できない状態になり得る。
- **修正**：`backend/app/service.py:83`で、既存の`BEGIN IMMEDIATE`内に代表者チェックと所属更新をまとめた。`backend/app/marketplace/service.py:99`の計画作成も同じwrite lockを取得するため、所属確認・計画作成と退出が直列化される。
- **証拠**：`marketplace-backend-verification.json`の`subsequent_concurrency_test`。担当者の競合回帰1 passed/1.37秒。計画作成と退出のどちらか一方だけが成功し、代表者が退出済みのopen計画を残さないことを検証。
- **状態**：修正コードと保存記録を照合済み。レビュー担当による負荷・大量並行試験ではない。

## 確認した境界

| 観点 | コード上の確認と根拠 | 状態・範囲 |
|---|---|---|
| 選択前は事業者へ見せない | `marketplace/service.py:233`のpreviewは確認用DTOだけ返す。`service.py:250`の明示選択後にselection/consultationを同じwrite transactionで作る | 担当者の選択前一覧0件・内部会話404・プレビュー後も一覧0件のHTTP試験あり |
| 共有項目を限定 | shared_conditionsは人数・泊数・予算額/単位/範囲・日付だけ。元写真・内部会話・元コミュニティ名・個人の好みはsnapshotへ入れない。share_noteは本人が共有確認した自由文 | allowlistを読取り確認。本人が自由文へ書いた機密を自動的に除去・保証する機能ではない |
| 別会社・別計画のID指定 | `service.py:21`のstaffと`service.py:24`のpartyは現在のDB所属を確認。公開前プランの読取・変更、相談の読取/投稿で認可。入力role/user_idを権限として使わない | 別社・計画外メンバー・staff解除の担当HTTP試験あり。MS-01修正も確認 |
| 選択の再送と原子性 | `service.py:250`のselection/consultation/operation_keysは一括保存。1計画1activeの一意制約。入力hashが違う同一キー、古い条件・プラン版は409 | 担当者の故障注入で選択だけ残らず、再送結果・過去snapshot保持も試験 |
| BearerとCookieを区別 | `backend/app/security.py:23`はAuthorizationがあればstage_sessionsのみを照会。誤り/期限切れでもCookieへ戻らない。Cookieはsessionsだけを照会 | 担当者の誤Bearer/Basic・Cookieへstage tokenを入れる試験・別画面CSRF/期限失効試験あり |
| 短期ログインとログアウト | `backend/app/main.py:104`は同じパスワード検証で30分tokenを発行。乱数32byte、DBはhash。Set-Cookieなし。Bearer logoutはstage_sessionsのみを削除 | Cookieの維持・もう片方の画面の接続維持を担当HTTP試験で確認 |
| ブラウザー内のキー保存 | `frontend/src/api.ts:1`のモジュール変数、stage fetchはcredentials:omit。URL・localStorage/sessionStorage・postMessageへtokenを入れない。clearSession→setCsrf空値でBearerも消去 | コード確認。ページの再読込み後はキーを復元せず再ログインが必要 |
| 認証付き画像 | `frontend/src/api.ts:115`は固定形式の相対media URLだけへBearer付きfetch。`ui.tsx`はBlob URL化し、離脱時にabort/revoke | CookieとBearerが混ざるimgタグ直読を避ける。分離した実ブラウザーで画像表示・事業者/匿名拒否を確認済み |
| CSPの例外は2つのHTMLだけ | `backend/app/security.py:82`のsecure_sendでGET/HEAD、text/html、完全一致`/stage/visitor`または`/stage/provider`だけSAMEORIGIN/self。API・通常画面・末尾スラッシュはDENY/noneを維持 | 担当者のmiddleware試験あり。inline/evalや外部originへの許可を追加していない |
| 中央画面への通知 | `frontend/src/api.ts:39`のpostMessageは固定origin、source/type/statusのみ。`Stage.tsx:32`はorigin・2つのcontentWindow・型/許可イベントを検証。Reactのテキスト描画 | 写真・会話本文・氏名・token/passwordを通知へ入れない。実イベント連動と改変通知拒否を8段階のブラウザー試験で確認済み。CP26では中央表示を上部の固定文見出しへ変更 |
| ログ | mainのエラーloggerは例外クラスだけ、入力値やSQLを出さない。nginx access_log off、uvicorn no-access-log。QAは結果・生成対象IDを記録し、キーを出力しない | コード上の確認。OS全ログ、すべての例外や将来追加する計測を監査したものではない |
| 移行と復元 | `marketplace/schema.py:30`はschema 1→2のDDL/seed/versionを同じwrite transactionで追加。未知版は拒否、version2は再seedしない | 担当者が移行再実行・中途DB失敗rollback・DBコピー復元を試験。レビュー担当が稼働volume移行、14表再起動保持、schema2＋写真の新規隔離volume復元も確認 |

## 証拠の区別

- [marketplace-backend-verification.json](marketplace-backend-verification.json)：担当者の通常API全体30 passed/23.84秒、実モデル1件deselected。その後の競合回帰1 passed/1.37秒。30件の一回と追加対象1件を、31件の一回の全体試験とは記載しない。先行26件・対象13件の記録も同ファイルに保持。
- [model-verification.json](model-verification.json)：最新三役イメージでLinuxの実画素推論4枚を再確認。新しい条件照合や会話抽出の意味理解、三役のセキュリティを証明する記録ではない。
- [稼働volume移行](schema2-migration-container.json)：レビュー担当がschema 1→2 / 29表を実測。既存講2件・参加者6件・投稿7件・media7件・所属201件の件数と全行ハッシュが一致。[コンテナー検証](container-verification.json)は新イメージ20項目成功、今回は再起動保持試験を省略。旧8080は継続稼働。
- [schema2保持・保全・隔離復元](schema2-persistence.json)：レビュー担当が主担当の画面操作を止めた時間に実施。2講・6参加者、旅行計画/条件/内部会話/選択/相談/返信各1件・冪等キー3件を含む14表で、停止再開前後の全行SHA一致。DB＋写真9ファイル4,096,394 bytes、全29表を新規隔離volumeへ復元し、全ファイルSHA・DB完全性・外部キー・件数一致。現行volume不変、8080/8081とも復帰後healthy。復元先API・画面を起動した試験ではない。
- [移行前バックアップ](full-snapshot-20261109T054156496503Z.json)、[検証](full-snapshot-20261109T054201813688Z.json)、[隔離復元](full-snapshot-20261109T054204273733Z.json)：レビュー担当が前工程で実施したschema1のDB＋mediaの保全。9ファイルのSHA・DB完全性・15表件数一致。現行volumeを置換していない。schema2の成功と混同しない。
- 同一originの左右iframeは、認証状態を分ける操作上の構成である。互いに信頼できないサイトを隔離するセキュリティ境界ではない。共通コードにXSSがないことの全面保証はしていない。

## 残る確認・運用上の条件

1. schema2移行、選択・相談・冪等キーを含む再起動保持、DB＋写真の隔離復元は確認済み。復元volumeから実際にAPI・画面を起動する復旧訓練は未実施。
2. stageの左右ログイン・片側logout・認証画像・通常Cookie維持・API responseのframe拒否と、上部見出し通知の送信元チェックは `stage-security-browser.json` の8段階で確認済み。自然な30分経過はバックエンド試験の範囲。利用者の通常Edgeの応答停止はCP27で調査中。
3. DBスナップショットの復元は、その時点の所属・承諾・失効情報も戻す。復元後の実運用切替では、取り消した所属/相談/セッションを再度無効にする手順を定める。今回のrestoreは隔離volumeだけであり、旧tokenを稼働環境へ復活させていない。
4. 合成アカウントの初期パスワード、HTTP localhost、単一プロセスのrate limitという前提。実利用者の情報を使う本運用や、インターネット公開の安全性まで合格とはしない。

追加の修正・結合結果が出たらこの文書へ追記する。規格名だけで認証・全面適合、脆弱性不存在を主張しない。
