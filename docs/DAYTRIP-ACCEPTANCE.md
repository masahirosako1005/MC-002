# 日帰り・先達・和の画面の検証記録

2026-11-10。後続の投稿改訂はCP68、階層整理はCP66として再検証する。

| 範囲 | 確認結果 | 証拠 |
|---|---|---|
| 日帰り・権限・計算 | 専用27件成功。価格版の同意後変更と事業者側の再読込の不具合を再現後修正 | `outputs/daytrip-boundary-before.xml` / `daytrip-boundary-after.xml` |
| モデル不要の写真処理 | 関連38件成功。旧モデル必須のskip撤去、写真処理維持 | `outputs/model-source-cleanup-tests.xml` |
| snapshotモデル情報任意化 | 4件成功、旧manifest互換 | `outputs/snapshot-metadata-tests.xml` |
| schema8→9 | 旧50表の行ハッシュ・画像8件一致 | `community/artifacts/daytrip-browser/migration-8-to-9.json` |
| schema9→10 | 旧58表の行ハッシュ・画像8件一致 | `community/artifacts/daytrip-browser/migration-9-to-10.json` |
| 開催操作 | 本人参加、翌日開催作成、先達の承諾、開催取消。未実施でポイント0を維持 | `community/artifacts/daytrip-browser/outing-consent.jpg` |
| 同じ講の再選択 | 読込状態で止まる不具合を修正。題名・参加者・保存操作保持 | `test/browser/DAYTRIP-CIRCLE-RESELECT.md` |
| 巻紙ログイン | ID/PW・表示切替・送信を統一。誤入力案内、Enter送信、320px横はみ出しなし | `community/artifacts/daytrip-browser/wa-login-v3.jpg` / `login-320.jpg` |
| 左右認証 | 左の利用者切替でも右の事業者ログイン維持 | 実操作。過去試験件数は合算しない |
| 費用・負担 | 15条件の計算例。効果・採算の実測ではない | [計算例](DAYTRIP-POLICY-SCENARIOS.md) |
| 解析 | React124、CSS126、型0、Ruff0、複雑度14、Bandit Medium19・High0 | `community/artifacts/frontend-quality/daytrip-wa-verified-manifest.json` / `community/artifacts/quality/daytrip-final/summary.json` |

対象が重なるため試験件数は足して総成功数にしない。残るSQL構築19件は[個別精査](DAYTRIP-SECURITY-TRIAGE.md)に残し、raw出力を抑制していない。

ゾーン20〜40kmは利用者の設定で片道経路距離。アクセス・待ち時間は別。開催、承諾、実参加、参加者確認、事業者確認を分離し、100点＋往復距離の10km単位（200km上限）＋先達50点、1人1日1回で計上する。ランク用と割引条件用のポイントを分ける。

開始後の先達交代、部分訂正、事業者確認のみの撤回、決済・返金は未実装。GPSで現地到着を保証しない。通常Edgeの停止、実利用者評価・再訪率、全画面200%拡大とアクセシビリティ全面適合は未確認。日帰り・和の全画面・新投稿を収録した新版動画は未作成。

旧ソース整理はGit管理下80ファイルを撤去。未追跡の旧ZIP・配布bundle・依存キャッシュは削除操作が自動承認審査に拒否され残存。詳細理由はなく `blocked by policy` のみ。[監査](CLEANUP-AUDIT.md)参照。DB・写真・バックアップ・Git履歴は保持。
