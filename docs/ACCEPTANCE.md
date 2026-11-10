# 受入確認：AC-01〜AC-20

確認日：2026-11-09。DESIGN.mdの受入条件を、保存された結果・試験コード・実装と照合した。判定はこの文書の条件内に限る。実利用者の評価、現地再訪の効果、既存システムへの接続、規格全体への適合を意味しない。

本書は下記の保存記録とコードの照合結果。最新のバックエンド全体51件・ブラウザー・コンテナー試験は主担当による実行である。収集の独立レビュー担当が直接行ったのは軽量確認16群と対象テスト3件であり、全体試験を同担当が再実行したとは扱わない。途中の失敗記録は保持し、最新の結果と区別する。

## 照合した証拠

| 証拠 | 記録された結果・条件 |
|---|---|
| [backend-tests.txt](../artifacts/backend-tests.txt)、[API試験](../backend/tests/test_api.py)、[収集API試験](../backend/tests/test_collection.py) | 主担当の最終記録は51 passed、10.57秒。Windows Python 3.13.17。時計差替え、異常系、復旧、権限、並列操作、収集・目標・移行を含む |
| [browser-tests.json](../artifacts/browser-tests.json)、[操作試験](../qa/tests/journey.spec.ts)、[収集操作試験](../qa/tests/collection.spec.ts) | 主担当の最終記録は20成功、失敗0、skip 0、flaky 0、167.73秒。2026-11-09 04:30:48 UTC開始。Edge/Chromium、既定390×844、1 worker。手帳作成・復旧の頻度制限を保つ合計122秒の待機を含み、操作性能の測定値ではない |
| [収集の対象操作試験](../artifacts/browser-tests-collection-focused.json) | 主担当4成功、失敗0、skip 0、flaky 0、8.52秒。2026-11-09 04:28:18 UTC開始。未獲得条件・目標再読込保持、訪問後の獲得・日時・幅/拡大、保存失敗と明示再試行、選択部品のキーボード操作を含む |
| [画面の通信記録](../artifacts/browser-network.json) | 主要3画面の試験で外部HTTP要求0件・JavaScriptエラー0件。ローカルHTTPを許可し、外部要求は遮断する条件 |
| [コンテナー確認](../artifacts/container-verification.json)、[確認スクリプト](../scripts/verify_container.py) | schema 3の再確認でpassed=true。UID10001、capability 0、NoNewPrivs、read-only実効設定と書込拒否、内部ネットワーク、外部TCP接続失敗、loopback公開、DB整合を確認。再起動前後のjournalとcollection一致、バックアップ整合・8表件数一致・collection_preferences全行一致を確認 |
| [sample-tests.txt](../artifacts/sample-tests.txt)、[CSV試験](../test/tooling/test_samples.py) | 合成データで5件成功。非保持列の訂正、再取込、不正行、個人識別情報非保存、キー喪失、PJ外出力拒否など |
| [初回集計](../artifacts/sample-quality.json)、[再取込集計](../artifacts/sample-quality-repeat.json) | 元CSV5件の前後hash同一、再取込追加0件、保存件数一致、参照未一致0。個票は表示・再掲しない |
| [Python監査](../artifacts/python-audit.json)、[フロント監査](../artifacts/frontend-audit.json) | 対象とした依存に対して報告された既知脆弱性0件。Python本体・OS・全開発ツール・未知脆弱性を包括する結果ではない |
| [独立レビュー](SECURITY-REVIEW.md) | 年度表示、500ヘッダー、セッション初期化、訂正版CSVの修正を個別照合。残る条件・自然キーの限界を記録 |
| [収集の独立レビュー](COLLECTION-REVIEW.md) | 個人分離、GET非更新、目標のCSRF/入力検証、別日・季節・年越し・初回達成日、復旧、バックアップ、schema 1/2→3を確認。独立16群と対象3件（0.51秒）が成功。確認範囲で高・中重大の不具合なし |
| [採用要求の結果](STANDARDS-RESULTS.md) | ASVS/WCAGの要求ID別、Docker独自チェック、SSDF工程について、範囲内合格・一部確認・未検証・適用外を区別 |
| [発表資料の検証](../artifacts/presentation/VISUAL-QA.md)、[PPTX](../outputs/tang-you-chi-presentation-final.pptx)、[PDF](../outputs/tang-you-chi-presentation-final.pdf) | 現在版は13枚。担当者がPowerPointで全13枚を再描画・目視確認し、108文字枠の超過0、PDF13頁すべて文字抽出可能、API51件・画面20件の反映、ファイナライザー指摘/警告0・フォント検査133件成功を記録。本書担当はslide XML13件・描画PNG13件と最終PPTX/PDFのSHA-256がQA記録と一致することを確認。旧11枚はversion-11-verifiedへ履歴保存 |

アクセシビリティは既存の `axe-home/journal/next/puzzle/recovery/reduced-motion.json` に、収集の `axe-collection-earned/detail.json` を追加し、現在の8件は違反配列が空。これは指定タグで自動検出した範囲の結果。文字200%は390pxの主要3画面と430pxの収集詳細、幅試験は主要3画面と収集詳細の320/390/430pxを確認する。全幅×200%×全画面を実施したとは扱わない。

収集追加時の全体試験は[初回17/20](../artifacts/browser-tests-collection-first.json)、[2回目19/20](../artifacts/browser-tests-collection-second.json)、[3回目19/20](../artifacts/browser-tests-collection-third.json)を保持した。2回目にはコントラスト、3回目には試験側の要素指定の失敗が残っていた。修正後の収集対象4件は成功したが、全20件の最終結果とは分ける。

続く[18/20の試験](../artifacts/browser-tests-collection-rate-limit.json)では、短時間の連続実行と新規手帳数の増加によって`POST /session`が20回/分の制限に達し429となった。画面の表示不具合や認証保護の欠陥として数えず、試験条件を修正した。製品の上限は緩めず、主要画面200%試験の前へ61秒を追加し、既存の復旧待機61秒と合わせて122秒を確保した。最終再実行は20/20成功。途中の不合格と原因・修正を保持している。

今回の拡張は[公式6サービス・7機構の調査](TROPHY-RESEARCH.md)から、12記念品・3棚、段階、最初のひと組、残条件、次の行動、取得日時を設計したもの。[追加API契約](COLLECTION-API.md)のschema 3で次に狙う1点を個人設定として保存する。既存の再訪2戦略を記録と次の行動へ結び、訪問・ゲーム達成・実績・予定保存は引き続き区別する。面白さや実際の再訪の改善は未測定。

追加のセッション回帰試験は実サーバーで行った。別ブラウザーによる復旧で元のセッションを無効にし、旧画面からの保存401後、再読込で別の匿名手帳を自動作成せず、復旧操作で同じ保存記録へ戻ることを確認。同じcontextの別タブでは共有Cookie更新後の旧CSRFによる403を確認し、画面内再読込では失敗した書込を自動再送せず、明示的な再操作で両タブに同じ2件が見えることを確認した。

その後、古い復旧dialogからの回復経路を追加修正した。「別タブで引き継いだ後に古い引き継ぎ画面からも復帰できる」は、別タブでCookieを更新した後、旧CSRFの復旧要求が専用403となるとdialogを閉じて全体の再読込へ進むことを確認する。再初期化後の誤った復旧コード401はdialog内の局所エラーとして残し、正しいコードへ直すと復旧できる。BUG-003の再開・追加修正・再完了は追記イベントに残す。

キーボードの追加試験は、Tab/Enter/矢印で訪問コード入力、難易度選択、水門操作、不正答からの訂正、次季保存、手帳・次の旅の確認まで完了する。復旧dialogをEscapeで閉じた後の焦点復帰も含む。全画面の全操作を網羅する試験ではない。途中の失敗記録は `browser-tests-session-regression.json` と `browser-tests-additional-scenarios.json` に保持し、最終成功で上書きして隠していない。

## 条件別の判定

「合格」は具体的な対象と試験条件に対する判断。「条件付き合格」は確認したローカル環境・画面範囲を明示する必要がある項目。「一部確認」「未検証」は未達として残し、合格へ数えない。

| ID | 判定 | 確認した内容・条件 | 証拠 | 未確認・限界 |
|---|---|---|---|---|
| AC-01 | 合格 | 訪問コード→水門の謎→不正答/ヒント→達成→次季保存→手帳表示を操作。収集条件と次の行動、訪問後の記念品、目標保存・再読込保持も確認 | browser-tests.json「現地コードから水門の謎・実績・次季保存まで」、browser-tests-collection-focused.json、API正常系 | 次の来訪理由を実利用者が理解したか、実際に現地へ再訪したかは未測定 |
| AC-02 | 条件付き合格 | Edgeのスマホ相当幅320/390/430px、主要3画面と収集詳細で横溢れなし。主要3画面390px・収集詳細430pxでroot文字200%も確認 | browser-tests.json、browser-tests-collection-focused.json、qa/tests/*.spec.ts、画面画像 | スマホ実機・Safari・スクリーンリーダー、全画面×全拡大条件、全固定要素の遮蔽確認は未実施 |
| AC-03 | 条件付き合格 | ローカル配信で主要画面を操作し外部要求0。appはinternal network、外向きTCP試験失敗 | browser-network.json、container-verification.json、compose.yaml | 初回のツール・依存・イメージ取得には通信が必要。OS全体の物理切断試験ではない。gateway自体の全外向き通信遮断は主張しない |
| AC-04 | 合格 | appコンテナーを再起動し、同じCookieのjournalとcollectionが前後一致。目標も保持 | container-verification.json、verify_container.py、API復元試験 | volumeの明示削除や端末故障で保持される意味ではない |
| AC-05 | 合格 | 同時正答・再送・不正型/余分な得点・DB障害で状態を壊さず、正しい再試行を受け付ける。収集目標も保存失敗で旧値を保持し、明示的に再試行できる。旧セッション/旧CSRFの失敗後に書込を自動再送しない | backend-tests.txt、APIの同時送信/入力/rollback試験、browser-tests.jsonの実失効/別タブ試験、収集対象試験 | 全ての電源断・ディスク故障を網羅するものではない。実日数を待ったセッション自然失効はAPI時計差替えと区別 |
| AC-06 | 合格 | 元ファイル前後hash、非保持列、出力DB、ログ方針を確認。加工物と分析DBをPJ内へ分離 | DATA-QUALITY.md、sample-quality*.json、sample-tests.txt、SECURITY-REVIEW.md | HMACによる仮名化であり匿名化ではない。全自由記述の内容を安全性評価したわけではない |
| AC-07 | 条件付き合格 | このWindows/WSL/Dockerで導入・起動・再起動・バックアップを実施。別DBへの復元後journal・セッション・collectionを照合。schema 1/2→3移行で既存履歴を保持 | SETUP.md、backend/README.md、container-verification.json、API backup試験、COLLECTION-REVIEW.md | 別の新規PCで手順を最初から追う再現試験は未実施。ホストとコンテナーのPython版差を記録 |
| AC-08 | 合格（成果物の対応） | 要件・API・基準・反復評価と試験を対応付けた。収集追加後のPPTX/PDF13枚、API51件・画面20件の反映、全枚描画・QA記録・最終ファイルhash一致を照合 | DESIGN.md、API.md、COLLECTION-API.md、BENCHMARKS.md、STANDARDS-RESULTS.md、EVALUATION.md、presentation/VISUAL-QA.md | 発表時間未提示のため指定時間での通し確認はT18の残条件。実利用者への伝達力・収集の面白さの測定は未実施 |
| AC-09 | 合格 | 画面の日本語、具体的な動詞、エラー・空状態を確認。制作説明や指定された汎用装飾文をfrontend/srcで検索し該当なし | Guide/Journal/NextTrip/Puzzle/Recovery、画面画像、browser-tests.json | 全文章への実利用者の理解度調査は未実施。製品・都市の正式表記は利用者確認待ち |
| AC-10 | 未検証 | 主役の体験カードと補助カードの大きさ・内容量を変えた実装とスマホ表示はある | frontend/src/styles.css、home-mobile.png、next-mobile.png | 参照CSSが未提示のため「参照の形状・大小関係を保つ」照合はできない。見た目を独自に整えたことを参照一致と扱わない |
| AC-11 | 合格 | Aの次季の謎と、Bの会議周遊・海辺・任意の人生行事を保存へ接続。収集では四季の謎・上級達成と、同地点別日・海辺の四季・会議館後の別日訪問を別条件で記録 | browser-tests.jsonのA/B操作、API recommendations/plan/collection試験、FIELD-GUIDE.md、COLLECTION-API.md | 神社・海辺・営業条件は架空設定。実地域での誘導成果・実再訪の因果効果は未測定 |
| AC-12 | 合格 | 旅のしおり・旅の手帳・次の旅・戻るを主要操作で統一 | App.tsx、Guide.tsx、Journal.tsx、NextTrip.tsx、browser-tests.json | 音声で提示された製品名・副題の正式綴りは未確認 |
| AC-13 | 合格（採用範囲の追跡） | 審査軸から選定したASVS/WCAG/SSDF・Docker公式設定、実装・試験証拠まで対応付け、要求ID別に結果と未確認範囲を記録 | BENCHMARKS.md、STANDARDS-RESULTS.md、EVALUATION.md、SECURITY-REVIEW.md、本書 | 記録の追跡ができることと全要求合格は別。WCAG手動項目、全保存項目のXSS試験、CIS本文未取得などは結果表でも未検証/一部確認を維持 |
| AC-14 | 合格（照合範囲を明示） | 候補50行を照合し、期間内資料49件＝AI開発中心28・関連21、うち名前付き受賞作品40件・募集/開催等まで9件・本文未取得1件を区別。先行採用10件と追加比較資料から採否を実装へ結び付ける | CONTEST-VERIFICATION.md、CONTEST-RESEARCH-RECEIVED.md | 主対象50を達成したわけではなく22件不足。A06は期間・受賞・独立性が未確認。受賞理由の公表・作者説明・PJの推論を区別。主対象の不足補完はRSH-001へ移す |
| AC-15 | 合格（記録の定義内） | 並列/再送は実績一件。収集は同地点同日・同季節の重複を除き、初段階と最終完成を分ける。CSV同一再取込と非保持列訂正で重複しない | backend-tests.txt、COLLECTION-REVIEW.md、sample-tests.txt、sample-quality-repeat.json | CSVに元イベントIDがない。同じ自然キーの別イベントは区別できず、キー列自体の訂正同期は未提供 |
| AC-16 | 合格 | 実績INSERTへ障害を注入し、達成・実績を同時rollback。障害解除後は再回答成功。訪問・実績も一括保存 | API test_transaction_failure_rolls_back_completion_and_can_retry / test_visit_and_trophy_fail_together | SQLiteの試験可能な障害に対する確認。全ハードウェア障害・停電からの復旧保証ではない |
| AC-17 | 合格 | JSTの翌日・冬の年度・翌年、旧attempt保持、同ゲーム版の最高得点、旧年度seasonの画面表示を確認 | backend-tests.txt、browser-tests.json「過年度の謎の季節がカタログに依存せず残る」 | APIは時計差替え、画面は旧attempt応答差替えによる確認。ブラウザーから実時計を進めたフルスタックE2Eではない |
| AC-18 | 合格 | 他利用者のattempt/plan、未認証、CSRF/Origin/Host、改変score/user_id、異常型を拒否。収集・目標も所有者で分離し、未知ID・URL・余剰所有者指定を拒否 | API ownership/forged answer/CSRF試験、SECURITY-REVIEW.md、COLLECTION-REVIEW.md | ローカルOS管理者やDB直接編集、未知の攻撃全般からの隔離を意味しない |
| AC-19 | 合格（設定条件内） | 往復＋体験＋10分余裕、時間不足、火曜休業、営業終了、非公開体験を検証。将来季節は今日の周遊と区別 | API recommendations/disabled candidate試験、browser-tests.json「会議周遊の制約・保存・取消と人生行事」 | 会議館固定・徒歩設定。実際の天候/潮汐/臨時休業/歩行速度/混雑は未確認。次季候補には出発前確認を案内 |
| AC-20 | 条件付き合格 | スマホ相当390pxでA/B保存まで完走。主要画面の外部要求0、app側通信制限、再起動後保存を別試験で確認 | browser-tests.json、browser-network.json、container-verification.json | A/B全操作とOS全通信遮断を一つの実機試験で同時に測定したものではない。実スマホでの利用、既存アプリとの結合は未実施 |

## まだ満たしていない条件

- 参照CSSと正式な名称・提出条件は未提示。AC-10、T06を完了にしない。所在・未提供を整理するT01の完了と、参照へ一致させる作業の完了を区別する。
- スマホ実機、Safari、支援技術による読み上げ、対象年代の異なる実利用者による成功率・操作時間・誤操作数・理解度の測定は未実施。自動操作の所要秒数を人の使いやすさの測定値へ転用しない。
- Core Web Vitalsの実利用75パーセンタイル、実際の継続来訪、地域消費・満足度の向上は未測定。現地コードの入力・候補保存・再アクセスを実再訪として数えない。
- 収集機能の「面白さ」「以前より集めたくなる」「再訪意欲が増える」は利用者調査をまだ行っていない。公式事例を採用したこと、実装が動いたことと、効果を実証したことは区別する。
- 既存アプリのソース・API・DB接続仕様は未提供。今回の追加体験は単独で動くローカル実装であり、既存サービスへの接続・移行・本番運用を完了したとは扱わない。
- 大会調査は候補50行を照合し、期間内資料49件（主対象28・関連21）、受賞作品確認40件、募集・開催等まで9件、本文未取得1件を確認した。主対象約50大会には22件不足し、達成を偽らずRSH-001で追加調査を追跡する。T13は公式出典・期間・分類・受賞と推論・件数不足・先行10件の設計適用を記録する調査工程として完了する。
- 全ASVS/WCAG/CIS適合・認証、未知脆弱性不存在を主張しない。モデル都市の実在情報検証や公開インターネット運用の評価は範囲外。
- 初期ブラウザー試験の失敗、コントラスト不合格と修正後成功を保存している。過去の失敗記録を消して最初から成功したように記録しない。

## チケットとの関係

個別不具合はBUG-001〜006で追跡する。正本は [チケットJSON](../project/tickets.json)、履歴は [追記イベント](../project/events.jsonl)、閲覧は [作業ボード](../outputs/project-board.html)。全受入条件と証拠が揃った項目だけ完了へ移す。

T06（参照CSSとの照合）、T16（実利用者・実機・未実測条件）、T18（指定時間での発表通し確認）は残条件を記録する。RSH-001でAI開発中心の大会数の不足を別途追跡する。T15/T17の完了は検証結果と未達を整理・追跡できることを意味し、残る条件を満たしたという意味ではない。本書の「合格」数を大会の公式点や実来訪効果に換算しない。
