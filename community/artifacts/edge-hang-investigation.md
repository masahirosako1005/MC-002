# Edge応答停止の切り分け（CP27）

2026年11月9日。利用者は「開いた直後・複数画面を切り替えた」と回答し、完全終了後も再発すると報告した。**未解決。停止位置はEdgeのブラウザー本体側を示唆するが、根本原因は未確定。**

## 観測したこと

| 対象 | 観測 | 解釈の範囲 |
|---|---|---|
| Windows | 15:03と15:05にEdgeのApplication Hang（1002）、AppHangB1（1001） | 実ブラウザーの停止を確認。アプリの表示だけの待機ではない |
| 通常Edge | ブラウザー親プロセスがResponding=false。5秒観測でCPU約1.01コア分。renderer/GPUは同期間CPUほぼ0 | 本体側の処理停滞を示唆。関数・原因モジュールは特定できていない |
| 再起動後 | 15:06作成の新プロセスでもResponding=false | 一度の終了だけでは回復していない |
| API | health 5回すべて200、147/13/6/7/6ms | 観測時のサーバー停止・高遅延を認めない。全APIの性能保証ではない |
| コンテナー | app約110MiB/768MiB、CPU0.53%、OOMKilled=false、healthy | サーバーのメモリ上限到達は観測されない |
| PC | 物理メモリ約15.6GiB、空き1.4〜2.6GiB、コミット86%、ページ読込あり | 余裕は少ないが、これだけで原因をメモリ不足と断定できない |
| 分離したEdge | 同じEdge157.0.4341.42、headless新規プロファイルで40回切替成功。開始735ms、中央値96ms、p95 150ms、最大208ms | 既存プロファイル・拡張・表示ウィンドウ/GPU経路との比較は未完了。実環境の修復を意味しない |
| ページ負荷 | 計測3フレームで50ms超longtaskの記録0、未処理JS例外0、外部要求0 | 今回の限定シナリオでの観測 |
| ブラウザー連携 | 停止プロセスにHP Sure ClickとSentinel Agentのモジュールを確認 | 存在だけで障害原因とはしない。無効化・削除・除外は行っていない |

実測の再現手順と値は [navigation-performance.json](navigation-performance.json) / `community/qa/verify-navigation-performance.mjs`。プロファイル内の閲覧履歴・Cookie・パスワードやメモリダンプは収集していない。ユーザーのEdgeは強制終了していない。

## 次の切り分け

1. ユーザー側で、既存プロファイルを保持したまま新しい一時プロファイルで同じlocalhostを開く。表示ありの同条件で比較する必要がある。
   - `community/scripts/open-edge-isolated.cmd` を用意した。手動起動用で、エージェントは実行していない。普段のプロファイルを変更せず、PJ内のGit対象外フォルダを利用する。保護機能やGPU設定を無効化する引数は付けていない。
2. 新プロファイルでも再発する場合は描画環境とブラウザー連携の互換性を確認する。組織管理の保護機能は、原因未確認で停止しない。
3. 画面操作ツールは現在URLの判定に失敗して停止済み。ツールを迂回して通常Edgeを操作しない。ユーザーによる比較結果が得られた時点で調査を続ける。

Microsoft公式は、完全終了、描画アクセラレーション、一時プロファイル、修復の順で切り分ける手順を公開している。本件では完全終了後の再発まで確認済み。[Microsoftの応答停止診断](https://learn.microsoft.com/en-us/troubleshoot/microsoft-edge/performance/edge-crashes-fails-to-launch)。HPの連携機能の概要は [HP公式説明](https://www.hp.com/gb-en/tech-takes/security/explainer/what-is-hp-sure-click.html)。両資料は、この端末で原因を特定した根拠ではない。
