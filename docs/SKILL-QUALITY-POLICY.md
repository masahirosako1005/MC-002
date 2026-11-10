# React・Pythonの開発指針と継続評価

2026-11-10 / CP67。スキルはレビュー時の指針であり、測定ツールや認証そのものではない。「世界で最も信頼できる」という順位を主張せず、実装フレームワークへの適合、提供元の責任、公開ソースと固定版の再現性を採用理由とした。

| 対象 | 採用元 | 保存先・固定版 | 適用 |
|---|---|---|---|
| React 19 / Vite / TypeScript | [Vercel Engineering](https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices) | `.agents/skills/vercel-react-best-practices` / `1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62` | 独立取得の並列化、不要な再描画抑制、イベントでの送信、遅延読込、古い応答の扱い |
| Python / FastAPI | [FastAPI公式リポジトリ](https://github.com/fastapi/fastapi/tree/master/fastapi/.agents/skills/fastapi) | `.agents/skills/fastapi` / `ba5d72bae32807f0af203c45cff695f80fd0f26c` | 入出力の型・検証、認証依存、公開レスポンスの限定、同期I/Oの適切な実行 |
| Python / Reactの安全性 | 既導入のOpenAI `security-best-practices` | 利用環境のスキルを継続適用 | 所属権限、投稿者権限、画像再符号化、入力制限、外部共有防止 |
| 操作と細部の品質 | 既導入の `emil-design-eng` | 利用環境のスキルを継続適用 | フォーカス、押下反応、動きを減らす設定、読字と処理中の表示 |

スキル導入には既存installerを使用。作業一時領域もプロジェクト内に限定。スキル本体に実行するPython/JS/shellファイルがないことを確認した。導入元の各ファイルSHA-256は `.agents/skills.lock.json` に保存。新版への自動更新はしない。スキルの自動検出は次のターンから利用でき、今回も保存した指針を読み実装レビューへ適用した。

Next.jsのRSC、SSR、`next/dynamic`、FastAPI Cloud、外部OpenTelemetryをこのアプリへ導入しない。現行はVite SPA・ローカルDocker・SQLiteで、既存の安全な仕組みを別のライブラリに置き換える理由にはしない。AI/MOC境界も変更しない。

## 変更ごとの評価ループ

1. チケットと受入条件を更新し、変更前の測定版を保持する。
2. 関係するスキルの指針で実装とレビューを行う。投稿では送信をイベント処理に置き、遅延読込、通信中断、本人・共有先の検証を確認する。
3. `./.venv/Scripts/python.exe scripts/quality_check.py posts-wa-001` のように新しい名前で実行する。API/ツール試験と静的解析はメモリを抑えるため順番に実行する。
4. `artifacts/quality/<測定名>/REPORT.md` と `summary.json` の新規指摘、解消、既存残件、実行失敗を読む。故障した検査や型エラーは成功にしない。
5. 原因を直して別の測定名で再測定し、Git版・チケット・動作証拠を結びつける。基準を緩めたり未達を除外して改善値を作らない。

通常の実行はRuff、複雑度C901、Bandit、Oxlint、Stylelint、TypeScript、pytestを含む。画面操作・画像投稿・アクセシビリティ・バックアップ復元は別の実操作検証が必要。`--skip-tests` や `--reports-only` は試験未実行と明示する。永続的な常駐監視やクラウドへのコード送信は行わない。

## 固定した比較元と解釈

比較元はフロント `daytrip-wa-verified`、バック `daytrip-final`。React指摘124、CSS指摘126、Ruff 0、複雑度14、Bandit 19（Medium 19 / High 0）を残件込みで保持する。型検査は0。ソース・設定のハッシュを保存し、新規ファイルも解析対象に含む。Banditの既存SQL構築指摘は [個別の安全性判定](DAYTRIP-SECURITY-TRIAGE.md) を参照し、raw結果から抑制しない。

現行集計はメッセージ内の参照行番号の変化をraw新規として数えることがある。[EV02独立レビュー](evaluation-frameworks/EV02-STATIC-REVIEW.md)で既存指摘との対応を説明し、生結果を保持する。同じファイルの同じ種類の問題が別の位置へ置き換わる場合は件数だけで判別できないため、ファイルのハッシュが変わり既存指摘が残る場合は `review-required` で止める。差分レビューと動作試験を併用する。設定変更・CSS構文/設定エラー・検査不能は `incomplete` とする。過去の集計は再集計でも上書きしない。

`no-new-findings-existing-debt` は「固定基準に対する新規指摘なし・既存課題あり」。全面合格ではない。指摘の数は大会の点数、実際の再訪率、利用者満足度、セキュリティ認証を表さない。

## Workでの独立調査

公開情報による提供元と指針の比較をChatGPT Workへ依頼。プロジェクトのソース・CSV・写真・秘密情報は送っていない。受信した助言も一次資料と適用バージョンで確認し、未受信を完了扱いにしない。

同日「外部Skill比較調査」の回答を受信。Vercel/FastAPIの選別適用、Next.js限定項目の除外、固定commit、実行コードの審査を推奨し、今回の選定と一致した。Trail of Bitsのmodern-python/differential-review等も候補に挙がったが、既存のRuff/pytest/安全性指針と重なるため追加導入は行わない。保守元だけで全scriptの安全性が保証されるとは扱わない。調査結果は製品コードを検査した結果ではない。


## EV01・EV02の追加基準

固定版web-design-guidelines（17節）とOWASP ASVS 5.0.0（345要求台帳）を導入し、既存4指針と併用した。[由来・固定版](evaluation-frameworks/README.md) / [最新の評価入口](QUALITY-CURRENT.md)。スキル適用、測定成功、規格全面適合を区別する。
