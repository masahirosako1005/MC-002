# 評価基準と実装・試験の対応

基準本文確認日：2026-11-09。本文を確認した版・要求IDに限定して使用する。これは採用項目の検証計画と対応表であり、認証、ASVSの特定レベル全体、WCAG AA全体、CIS全体への適合宣言ではない。結果の正本は [EVALUATION.md](EVALUATION.md) と各試験証拠。

## 記録方法

各項目は「合格／不合格／未検証／非該当」を記録し、測定日、コードの版、対象画面・API、端末、条件、証拠ファイルを添える。実装があるだけでは合格にしない。適用項目数＝合格＋不合格＋未検証。非該当は別に数え理由を示す。

表は各規格から選んだ確認対象を示す。実施済みの証拠は末尾の「実測との対応」と[受入記録](ACCEPTANCE.md)に集約し、規格の全条件を満たしたという意味での合格数へ換算しない。

## OWASP ASVS 5.0.0

要求IDは5.0.0の公式タグ本文で照合。表の説明は今回の対象範囲に絞った要約であり、原文の全条件を置き換えない。

| 本文の要求ID | 今回の確認対象 | 実装・試験との対応／合格証拠 |
|---|---|---|
| 2.2.1、2.2.2 | 型・範囲・許可値の検証をサーバーで実施 | `backend/app/models.py`、`test_forged_or_invalid_answer_rejected`、`test_recommendation_invalid_queries`。不正入力で保存状態が変わらない |
| 2.3.1 | 必要な順番を飛ばせない | `service.py`の訪問確認。訪問せず挑戦を開始して拒否されること |
| 2.3.3 | 業務更新を全体で成功・失敗させる | `database.py`、`test_transaction_failure_rolls_back_completion_and_can_retry`、`test_visit_and_trophy_fail_together` |
| 2.4.1 | 過剰な呼出しを制限 | `security.py`、`test_payload_limit_and_rate_limit`。上限超過、再試行案内、資源消費の上限 |
| 3.2.2 | 文字列を安全に表示 | Reactの通常テキスト描画。保存理由等へHTML文字列を入れ、実行されず文字として表示されること |
| 3.3.2、3.3.4 | CookieのSameSiteとHttpOnly | `main.py`のCookie設定、`test_csrf_origin_json_host_and_cookie`。セッショントークンをJSONへ返さないことも確認 |
| 3.4.3、3.4.4、3.4.6 | CSP、MIME推測防止、埋込み制限 | `security.py`。通常・エラー応答にヘッダー確認。3.4.3の最低条件には`object-src 'none'`と`base-uri 'none'`がある |
| 3.5.1、3.5.3 | CSRF防止、状態変更のHTTPメソッド | Origin＋CSRFトークン、POST/DELETE。欠落・不正Origin・他セッションのtokenを拒否し、GETで更新しない |
| 7.2.1、7.2.3 | サーバー側セッション検証、推測困難な参照token | `main.py`、`security.py`。CSPRNGで32バイトを生成、期限と照合を確認。文字数だけで乱数品質を判断しない |
| 8.2.2、8.3.1 | データ所有者の認可を信頼できる層で実施 | `service.py`、`test_ownership_and_authentication_boundaries`。他人の挑戦・候補IDを指定しても読取・更新できない |
| 16.2.5 | 秘密・個人情報をログへ不用意に残さない | セッション、CSRF、訪問コード、CSV個票を出力しない。例外時と通常時のログを検査 |
| 16.5.1、16.5.3 | 内部情報を隠して安全に失敗 | `main.py`の例外処理、DB障害試験。SQL・スタック・tokenを返さず、失敗で権限を通さない |

ASVS一次資料： [V2 入力・業務処理](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/en/0x11-V2-Validation-and-Business-Logic.md)、[V3 ブラウザー](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/en/0x12-V3-Web-Frontend-Security.md)、[V7 セッション](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/en/0x16-V7-Session-Management.md)、[V8 認可](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/en/0x17-V8-Authorization.md)、[V16 ログ・例外](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md)。

**適用例外と限界：** 初期構成は127.0.0.1のHTTPで動作するため、Secure Cookie／Cookie名prefix（3.3.1、3.3.3）やHSTS（3.4.1）を全面適合と扱わない。HTTP向け設定をインターネット公開環境へ流用しない。匿名セッションは実在人物の本人確認ではない。Cookieを失った場合の手帳復旧は独立した安全性検証が必要であり、復旧コードを使う場合は十分な乱数、ハッシュ保管、ローテーション、旧セッション失効、試行制限を確認する。現地コードは物理的な位置の暗号学的証明ではない。これらを隠して安全性を主張しない。

## WCAG 2.2：A・AAの採用項目

基準：[W3C Recommendation、2024-12-12版](https://www.w3.org/TR/2024/REC-WCAG22-20241212/)。AAを目標にする場合はAの項目も対象になる。以下は主要動線に対する抜粋であり、全成功基準の網羅ではない。

| 成功基準 | 合格の確認方法 | 対象・証拠 |
|---|---|---|
| 1.1.1 非テキストコンテンツ（A） | 情報を伝える図に代替説明。装飾を読み上げ対象から除外 | 地図、水門、実績アイコンの代替・隣接テキストを手動確認 |
| 1.3.1 情報と関係性（A） | 見出し・ラベル・グループが機械的に分かる | 入力label、見出し階層、fieldset等を自動＋手動確認 |
| 1.4.3 コントラスト（AA） | 通常文字4.5:1以上、大きい文字3:1以上。規定の例外は別記 | 薄色の補助文、選択状態、ボタンを計測。[公式解説](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) |
| 1.4.4 文字拡大（AA） | 200%で内容・機能を失わない | 全タブとパズルで実際に拡大。[公式解説](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html) |
| 1.4.10 リフロー（AA） | 縦スクロールの内容を320 CSS px相当幅で利用できる。二次元必須部分の例外を明記 | 横溢れ、下部タブ、ダイアログを手動確認。390pxの確認だけで代用しない |
| 2.1.1、2.1.2 キーボード・トラップ防止（A） | マウスなしで全主要操作が可能で、抜けられない箇所がない | 訪問入力、数値操作、ヒント、保存・取消、タブ移動を通す |
| 2.4.7 フォーカス可視（AA）、2.4.11 遮蔽防止（AA） | 現在位置が見え、固定フッター等で完全に隠れない | Tab/Shift+Tabで全操作を確認。[公式解説](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) |
| 2.5.8 ターゲットサイズ（AA） | 原則24×24 CSS px以上、または規定の間隔等の例外を満たす | 小さな取消・数値ボタンを測定。PJでは主要操作44px以上を独自目標とする。[公式解説](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) |
| 3.1.1 言語（A）、3.3.1・3.3.2 エラー・説明（A） | 日本語指定、入力の説明、誤り箇所と回復方法が分かる | `lang=ja`、コード不一致・通信失敗・候補なしの状態確認 |
| 4.1.2 名前・役割・値（A）、4.1.3 状態通知（AA） | 操作と状態の意味を支援技術に伝える | タブ選択、数値、保存結果のrole/aria確認と読み上げ。[公式解説](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) |

自動検査の違反0件は検査範囲内の結果であり、WCAG全体合格ではない。主要な動線の手動確認、文字拡大、キーボード、読み上げを別に記録する。動きを減らす設定はPJ追加要件として検証し、すべてをAAの必須条件と誤記しない。

## Docker：公式設定に基づく確認

[CISの公開案内](https://www.cisecurity.org/benchmark/docker)ではDocker Benchmark 1.9.0の掲載を確認したが、個別要求のPDF本文は今回取得・照合していない。以下をCISの項目番号やCIS適合率として提示しない。代わりにDocker公式仕様を根拠とするPJ独自チェックを使用する。

| PJ項目 | 実装対象 | 実測可能な確認 |
|---|---|---|
| D01 最小権限 | Dockerfileの非root利用者、composeの`cap_drop: ALL`、`no-new-privileges` | `docker inspect`、コンテナ内UIDと/proc/self/statusを確認。privilegedやDocker socketのマウントがない |
| D02 書込範囲 | 読取専用rootfs、DB volume、制限した/tmp | rootfsの書込失敗とDB保存成功。初期化と再起動がこの制約下で動く |
| D03 公開・通信範囲 | 127.0.0.1のポート、internal network | 実際のport bindingとnetwork設定、外向き通信の失敗、ブラウザーの外部要求0件 |
| D04 資源制限 | メモリ、CPU、PID上限 | inspect値と正常操作を確認。負荷時にデータ整合性を失わない |
| D05 永続化・復旧 | named volume、SQLite backup | 再起動、バックアップ、別DBへの復元後に件数・整合性を確認。volume削除を通常停止手順にしない |

Docker一次資料：[コンテナ実行・権限](https://docs.docker.com/engine/containers/run/)、[Composeサービス設定](https://docs.docker.com/reference/compose-file/services/)、[内部ネットワーク](https://docs.docker.com/reference/compose-file/networks/)。internal networkの設定だけでブラウザー側の外部アクセスまで遮断したことにはならないため、両方を検証する。

## NIST SSDF v1.1：開発工程の証拠

基準：[NIST SP 800-218、2022年2月](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf)。以下は個別の工程対応であり、アプリの安全性を保証する点数ではない。

| 要求ID | 本PJで残す証拠 |
|---|---|
| PO.4.1 | EVALUATION.mdの固定基準、提出不可条件、未検証を残すルール |
| PW.7.1、PW.7.2 | レビュー対象・方法、指摘、重要度、修正と再確認の記録。別エージェントのレビューだけで人間による評価とは称さない |
| PW.8.1、PW.8.2 | 脅威と失敗条件に基づく試験選定、API・UI・障害注入の結果と再試験 |
| PW.9.1、PW.9.2 | composeの安全な初期設定、公開範囲・権限・保存先、運用条件の説明 |

## 効果・ユーザビリティのPJ独自指標

| 指標 | 定義 | 注意点 |
|---|---|---|
| 操作課題達成率 | AまたはBを保存まで完了した試行数／全試行数 | テスト自動化の成功率と実利用者の成功率を別にする |
| 操作時間 | 課題提示から保存確認までの時間 | 端末・経験・手順・試行数を揃える。待機を除外するなら定義を記録 |
| 回復可能性 | 入力誤り・通信失敗から自力復帰できた試行数／失敗シナリオ試行数 | エラー表示の存在だけで使いやすいと判定しない |
| 再訪理由の理解 | 場所・時期・目的を本人が説明できた人数／参加人数 | 利用者試験未実施なら未測定とする |
| 実際の再訪 | 定義した別旅行機会で現地訪問を確認できた人数／対象人数 | アプリ再アクセス・候補保存・訪問コード入力を無条件に実来訪と同一視しない |

プレゼンでは、公式基準の採用項目数、合格・不合格・未検証、実測の条件を示す。PJ独自100点は基準対応の進捗指標であり、大会の点数や再訪効果の点数ではない。

## 実測との対応

| 確認範囲 | 実測・証拠 | 残る範囲 |
|---|---|---|
| 入力・認可・CSRF・原子性・復旧 | API33試験成功。`artifacts/backend-tests.txt`と`backend/tests/test_api.py` | ASVS全要求・公開運用認証は未評価 |
| 画面の自動アクセシビリティ | 主要6状態のaxe違反0。`artifacts/axe-*.json` | スクリーンリーダー実機・全WCAG手動監査は未実施 |
| 幅と拡大 | 320/390/430pxの文字サイズ操作、390pxでroot文字200%の主要3タブ。`artifacts/browser-tests.json` | 実スマホ全機種と全状態の組合せ検証ではない |
| 実行制約・保存 | 非root、権限削減、read-only実効設定、内部network、loopback公開、外向TCP失敗、再起動維持、backup整合。`artifacts/container-verification.json` | gatewayを含む全宛先・全プロトコルの網羅的遮断実験ではない |
| 依存監査 | Python runtime14依存、frontend npm監査で既知脆弱性0。`artifacts/python-audit.json`、`frontend-audit.json` | OS・Python本体・未知の脆弱性は保証しない |
| 開発過程 | 独立レビュー、修正前後の証拠、Git履歴、チケットイベント、受入条件 | 人間の監査や認証を取得したという意味ではない |
| 実際の利用価値 | A/B保存までの操作を自動試験で確認 | 実利用者の達成率・時間・満足度・現地再訪率は未測定 |
