# 大会8項目と評価ツール — Q1（2026-11-09）

2026-11-10追補（EV01）：既存の評価ツールに、固定版Vercel Web Interface GuidelinesとOWASP ASVS 5.0.0の345要求台帳を追加した。[導入内容・8項目対応・評価手順](evaluation-frameworks/README.md)を参照。導入確認とアプリの評価結果を区別し、今回の新基準に対するアプリ評価は未実施。以下の数値は過去の測定記録である。

8項目の名称は旧設計書8.1の利用者提示条件を引き継ぐ。旧アプリの得点・試験結果は引き継がない。大会の公式配点や採点用ツールは提示されていないため、以下は現行アプリを改善する独自の測定計画。固定C1の20項目と別に管理する。数値はツールの対象範囲に限り、公式点や全面適合に換算しない。

## 対応表

| 大会の項目 | 今回使う評価ツール・方法 | 測れる部分 | 自動では決められない部分 |
|---|---|---|---|
| サービス性：要求仕様・目的の達成度 | 要件台帳＋Playwrightの利用シナリオ | 実装済み操作と要件の対応、保存成功 | 利用者の価値、再訪効果、目的の妥当性 |
| サービス性：ユーザビリティ | Playwright、axe-core、ブラウザーPerformance API | キーボード/焦点、画面幅、文字拡大、既知のアクセシビリティ違反、操作時間 | 初見で迷わないか、気持ちよさ、満足度 |
| サービス性：革新性 | 公式先行事例の比較表・設計差分（補助分析） | 既知の類似機能と差分の整理 | 新しさ・有用性の評価。静的解析/LLM点数だけでは判定不可 |
| サービス性：多様性 | axe-core、Playwrightの320/390px・200%・キーボード・reduced motion試験 | 代替操作/拡大/動きの制約、限定したアクセシビリティ | 年代/性別/障害等を含む利用者の公平な体験。合成人物やaxe0だけでは達成扱いにしない |
| テクニカル：正確性 | pytest、Playwright、TypeScript、coverage.py | 正常/異常/境界/競合、契約と画面動作、行/分岐の通過率 | 試験していない条件、要件そのものの誤り |
| テクニカル：セキュリティ性 | Bandit、pip-audit、npm audit、認証/CSRF/Origin/越権/回数制限のpytest | コードの危険パターン、既知依存脆弱性、権限境界 | 未知の攻撃、構成全体の安全保証。検出は独立にトリアージ |
| テクニカル：データ完全性 | SQLite integrity_check/foreign_key_check、pytest競合/rollback、DB+mediaのhash比較・隔離復元 | 原子性/参照整合/冪等性、再起動保存、バックアップ一致、削除反映 | 実運用の全障害。古いバックアップ自体の削除情報は後から改変しない |
| テクニカル：保守性 | Ruff、Oxlint type-aware、Stylelint、tsc、coverage.py、Git/チケット追跡 | 未使用/型安全/React規則/CSS問題、複雑度、試験範囲、再現性 | 設計責務の適切さ、将来拡張の容易さ。独立レビューも行う |

## ツール選定と限界

[Ruff公式](https://docs.astral.sh/ruff/)はPython規則解析、[Bandit B608公式](https://bandit.readthedocs.io/en/latest/plugins/b608_hardcoded_sql_expressions.html)はSQL文字列構築等の疑いを検出する。疑いを実脆弱性と即断せず、入力値の経路とplaceholderを確認する。[pytest公式](https://docs.pytest.org/en/stable/)をAPI/保存/境界試験に使用する。

フロントはTypeScript 7に対応するOxlintのtype-aware解析を採用した。対応範囲外のtypescript-eslintを無理に使用したり、解析を通すためにTSを旧版に下げない。Windowsの組織ポリシーでnative解析ライブラリが拒否されたため、OS設定を緩めず固定digestのDocker内でネットワークなし・1CPU/512MBに制限して解析する。詳細は FRONTEND-QUALITY.md。

SonarQube Community Buildは総合管理の候補だが今回未導入。空きメモリ約2.3GBの端末でアプリ/ブラウザーと並行稼働させず、軽量な個別解析の生結果を保存する。Semgrep/ZAP/Lighthouseも今回未実施なら合格の根拠に含めない。Lighthouseの公開ページ点数だけで認証後の体験を評価しない。クラウドへコード/CSV/秘密情報をアップロードしない。

## Q1の固定した測定条件と改善ループ

1. 現行productionソース全体を対象に、規則・版・ファイルhashとbaselineを保存。依存キャッシュ/旧版/生成物は対象外と明記。無効化規則を増やして得点を上げない。
2. 誤検出は根拠を付けて区別し、生の件数を残す。型の決め打ち/未使用/実重複/失効処理など、具体的な原因を修正する。
3. 同じ設定で再測定し、新機能で母集団が変わった場合はソースhashとともに明示する。coverageは実行した行数/分岐数を分母にせず、対象全体を分母にする。
4. 型と本番ビルド0エラー、選んだ正常/異常/権限/復元試験は全成功を必須とする。既知の未解決重大脆弱性/データ破壊/起動不能があれば提出可とはしない。
5. Lint/CSSの残りは0を目指して改善するが、警告の総数だけで100点や大会最高品質と称さない。新規追加コードの行/分岐と未通過箇所も確認する。

## 測定履歴（途中）

| 指標 | baseline | 安全修正後 | 状態 |
|---|---:|---:|---|
| Python Ruff 指摘 | 45 | 0 | 同config、全49module。baselineは追加機能の新規草稿を含むdirty treeでhashを保存 |
| Python 複雑度 C901 | 12 | 12 | 残存。routerのネストしたendpoint定義も数えるため設計レビューと併用 |
| Bandit | Medium 19 / High 0 | Medium 19 / High 0 | 全19件SQL構築。固定識別子/固定DDLと値placeholderを主/独立レビュー、規則抑制なし |
| Oxlint | error 97 + warning 145 | error 94 + warning 55 | CP45/47統合前の安全改善区切り。最終測定は後記 |
| 危険な型assertion | 84 | 1 | generic API応答境界が残存。例外unknownやDOM/eventをguard化 |
| Stylelint | 129 | 124 | 未達。実重複修正、無関係component間specificityも残数に含む |
| TypeScript | 0 | 0 | 型エラーなし |
| Python runtime依存監査 | 未測定 | 既知脆弱性0 | pip-audit、固定requirementsと解決された依存。日時とDB応答範囲に限る |

生結果は community/artifacts/quality/ と frontend-quality/。独立レビューは COMMUNITY-PERSONALIZATION-REVIEW.md、C1の未達監査は COMMUNITY-EVALUATION-AUDIT.md。最終結果・実行条件・残課題をここへ追記する。

## 追加受入の結果

本人再開は最終画面7項目（再読/講復元/前回画面/409調停/遅い旧401/2人分離/未選択から明示選択）、320px/390px/200%、axe0、外部0に成功。回帰で既存試験が「常に初期画面」を仮定していた箇所を、明示的なコミュニティ選択/講一覧へ戻る操作へ更新した。

Python全体145ケースは全体実行144成功＋schema期待値更新後1再成功、旧実モデル1skip。行91.85%、分岐80.94%、除外行0。新規personalization各moduleの総合coverage85.7〜100%。全49moduleに休止モデルも含めて分母を隠していない。

固定C1はCQ14/15の実証追加により30→40/100。残りを大会点へ換算しない。課題の詳細は評価正本を参照。

## 画面側の第2巡

CP47追加後の同一39ファイル・同設定比較: Oxlint152→125（error96→96、warning56→29）、Stylelint127→127、tsc0。Promise11件/cleanup return9件等を安全修正。最初の27 TS系ファイル＋CSSのbaseline242とは新hook等の母集団が異なるため、2巡を分ける。最終125件とCSS127件は未解決数として保持し、0や全面合格とはしない。npm auditはruntime/devを含む既知脆弱性0。

現在配信の40回画面遷移は中央値66ms/p95 172ms/最大175ms。前の測定は96/150/208msで、p95は増加している。画面版/アニメーションと状態が異なるので速度改善率として宣伝しない。通常Edge停止とは無関係な分離headless試験。
