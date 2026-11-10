# 大会8項目の評価基盤 — EV01

2026-11-10。利用者の「評価するスキル/frameworkがなければ外部から導入する」という指定に対応。既存の検査は維持し、不足するUIレビュー基準とセキュリティ要求台帳を追加した。これは導入記録であり、アプリの再評価や大会の採点結果ではない。

## 追加したもの

- **Vercel web-design-guidelines**：`.agents/skills/web-design-guidelines/SKILL.md`。元スキルと参照規則を別々のcommitで固定。毎回mainへ接続する手順を、同梱した規則を読む手順へ変更した。原文も保持。入力、フォーカス、代替操作、状態表示など17節をレビューする。日本語、ローカル配信、独立認証、標準select不使用を優先し、Next.js/SSR、外部CDN、私的な状態のURL公開を導入しない。
- **OWASP ASVS 5.0.0**：公式英語CSVの全345要求とCC BY-SA 4.0ライセンスを保存。`ASVS-assessment.csv`へ全IDを対応させ、適用判定・理由・検査方法・結果・証拠・担当・確認日を記入できる。初期状態は全件 `not-assessed` / `not-tested`。345項目の合格やASVS全面適合を示すものではない。
- **由来と固定版**：[lockファイル](../../.agents/evaluation-frameworks.lock.json)にcommit/ref、変更点、SHA-256を記録。参照規則のMITライセンスも同梱。アプリの実行時に新たなサービス、外部AI、外部DBは追加しない。

公式の提供元：[Vercelスキル](https://github.com/vercel-labs/agent-skills/tree/1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62/skills/web-design-guidelines)、[Vercel参照規則](https://github.com/vercel-labs/web-interface-guidelines/blob/434b7f91364665f2f733b310ec54809bf8f37937/command.md)、[OWASP ASVS 5.0.0](https://asvs.owasp.org/downloads/)。外部資料の取得のみで、ソース・CSV個票・秘密情報は送信していない。

## 8項目への対応

| 項目 | 導入済みの指針・測定方法 | 残る評価 |
|---|---|---|
| 要求仕様・目的の達成度 | DESIGN/受入条件/チケット、pytest・Playwrightのシナリオ | 実利用者の価値、実際の別日再訪。保存や初期履歴を効果に換算しない |
| ユーザビリティ | emil-design-eng、新Vercel UI規則、Playwright・axe-core | 初見利用者の完遂率・所要時間・迷い・満足度を観察する |
| 革新性 | 先行事例との機能・体験の比較表、独立レビュー | 新規性と有用性を分け、人が判断。専用自動採点スキルは導入しない |
| 多様性 | Vercel UI規則、axe-core、キーボード/画面幅/拡大/reduced motion試験 | 実際の多様な利用者・支援技術で確認。自動違反0を全面適合としない |
| 正確性 | pytest、Playwright、TypeScript、coverage.py、FastAPI指針 | 要件の誤り、未試験の条件。カバレッジは正しさの点数ではない |
| セキュリティ性 | security-best-practices、Bandit、依存監査、権限/CSRF試験、新ASVS台帳 | 対象要求をレビューし、試験と証拠を対応付ける。台帳導入だけでは未検証 |
| データ完全性 | SQLite整合性/外部キー検査、競合・取消・再起動・隔離復元、ハッシュ比較 | 障害想定と復旧手順の確認。ASVSは一部補助であり復元試験の代替ではない |
| 保守性 | Vercel React/FastAPI指針、Ruff/Oxlint/Stylelint/型/複雑度、Git・台帳 | 責務分割や変更容易性の独立レビュー |

## 評価の使い方

1. 対象のGit版、作業ツリー変更、画面、役割、環境と受入条件を固定する。大会の公式配点・合格点は未提供のため独自点を公式点へ換算しない。
2. UIレビューでは固定規則に対し、問題箇所・再現条件・重要度・証拠・修正案を残す。静的な疑いと実操作で確認した問題を分ける。`UI-REVIEW-TEMPLATE.md`を新しい記録へコピーして用いる。
3. ASVSはまず適用範囲を判断する。`applicable` / `not-applicable` / `not-assessed`、結果は `pass` / `fail` / `not-tested`。対象外には理由、passには対象版と証拠を必須とする。今回L1/L2等の達成レベルは宣言しない。
4. サービス性では、実利用者の対象・人数・課題・成功条件を事前に決める。革新性は比較先/比較日/既存との差/価値仮説/判断者を記録する。AIの点数や架空の利用者回答を実証の代わりにしない。
5. 修正後は同じ条件で該当検査を再実行。未達・未確認・対象外を分け、過去の証拠を上書きしない。

## 確認した既存基盤と制限

既存のReact/FastAPIスキル、環境側のsecurity-best-practices/emil-design-eng、ブラウザー試験のPlaywright/axe依存定義、pytest/coverage、品質用環境のRuff/Bandit、pip-audit、フロントのOxlint/Stylelint/TypeScriptと過去の評価記録を確認した。

確認時には別作業でcommunity配下からroot frontend/backendへ構成移動中だった。既存 `scripts/quality_check.py` には旧パス参照が残っていたため、この導入作業では現在の一括検査が実行可能・合格とは断定しない。構成変更担当の更新と分け、実アプリ、DB、Dockerは変更していない。過去の最新参照 `artifacts/quality/revisit-release/REPORT.md` はreview-required、当該実行の動作試験はnot-runだった。過去結果を今回の評価結果へ流用しない。

導入検証は `installation-verification.json` に記録する。新スキルの自動検出は次のターンから利用可能。今回は導入内容と適用範囲の確認までで、8項目の全再評価は未実施。
