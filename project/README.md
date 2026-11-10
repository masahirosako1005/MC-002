# ローカルのチケット管理

[作業ボード](../outputs/project-board.html)をブラウザーで開く。サーバーや外部サービスは不要。検索、状態・優先度の絞り込み、チケット詳細を使える。ボードは閲覧用で、変更は下記CLIで記録する。更新後はブラウザーを再読込する。

正本は `project/tickets.json`、変更履歴は `project/events.jsonl`。`TASKS.md` は作業範囲と完了条件の元資料。既存作業は起票した時点で整理しており、記録前の着手日・完了日を捏造しない。連絡された進捗は確認済みの証拠と区別し、受入条件が残るものは検証中に置く。

## 操作

PJルートで実行する。Python標準ライブラリーだけを使用。

```powershell
.\.venv\Scripts\python.exe scripts/tickets.py list
.\.venv\Scripts\python.exe scripts/tickets.py show BUG-001
.\.venv\Scripts\python.exe scripts/tickets.py create BUG-007 --type bug --priority P1 --title "具体的な不具合" --description "再現手順と影響" --accept "修正後の期待結果" --doc docs/API.md
.\.venv\Scripts\python.exe scripts/tickets.py status BUG-007 in_progress --note "原因を調べる"
.\.venv\Scripts\python.exe scripts/tickets.py comment BUG-007 --text "調査で分かったこと"
.\.venv\Scripts\python.exe scripts/tickets.py status BUG-007 review --note "修正済み。動作確認を行う"
.\.venv\Scripts\python.exe scripts/tickets.py evidence BUG-007 --text "確認した条件・操作・結果を記載" --file backend/tests/test_api.py
.\.venv\Scripts\python.exe scripts/tickets.py check BUG-007 1 --note "受入条件1を確認"
.\.venv\Scripts\python.exe scripts/tickets.py status BUG-007 done --note "条件と証拠を確認して解消"
.\.venv\Scripts\python.exe scripts/tickets.py revision BUG-007 abcdef1
.\.venv\Scripts\python.exe scripts/tickets.py document BUG-007 docs/API.md
.\.venv\Scripts\python.exe scripts/tickets.py validate
.\.venv\Scripts\python.exe scripts/tickets.py build
```

上のBUG-007とcommitは使い方の例。実際のID・確認内容・存在するcommitに置き換える。`evidence --file` は実在するPJ内ファイルのみ指定できる。テストのソースファイルをリンクしただけで、実行済みとは扱わない。結果の説明には実行条件・成功/失敗・未確認事項を記す。

- 状態: `todo` 未着手 → `in_progress` 作業中 → `review` 検証中 → `done` 完了。
- 優先度: P0 緊急、P1 高、P2 標準、P3 低。
- `--accept`・`--depends`・`--doc` は複数指定できる。
- `check ID N` は1から始まる受入条件番号。`--undo` で未確認へ戻す。完了を再開する場合は先に `status ID in_progress --note "再開理由"`。
- 完了には全受入条件のチェックと少なくとも1件の証拠が必要。CLIは証拠の真偽を自動認定しないため、担当者は実際に確認した内容だけを登録する。
- `revision ID HASH` はローカルGitでcommitを確認し、件名とhashをPJ内の閲覧ファイルへ保存する。外部Gitサービスやネットへ接続しない。未コミットの検証はcommitへ無理に結び付けない。
- `init` はTASKS.mdのT01〜T18を起票する。既存IDはスキップし、状態や証拠を上書きしない。
- コマンドで変更を保存するとボードも自動再生成する。ブラウザー上のフィルターは正本を変更しない。

## 保存と復旧

更新時はOSのファイルロックで競合を避ける。新しいイベントを末尾へ追記してfsyncし、その後JSONを同じフォルダの一時ファイルから原子的に置換する。HTMLも原子的に置換する。過去のイベントを書き換えたり削除したりする操作はCLIにない。

JSONとJSONLという2ファイルをOSが同時に原子的更新するわけではない。イベント保存後・JSON置換前に停止した場合は、次のCLI実行で追記済みのイベントから正本を回復する。イベント自体が不完全・改変された場合、または正本が履歴と矛盾する場合は自動上書きせず停止する。まず `project/` 全体をPJ内の退避先へ保全し、内容を確認する。壊れた履歴を手で削って成功扱いにしない。

イベントには連番・前イベントhash・内容hashがあり、順序や偶発的な改変を検出する。これは同じPCの管理者による全履歴改ざんを防ぐ署名・外部監査ではない。`tickets.json` や `events.jsonl` を通常の編集作業で直接更新しない。証拠の訂正は新しいコメント/証拠イベントとして残す。

保存先はこのPJ内に限定。文書リンクに外部URL・絶対パス・親フォルダ参照を受け付けない。個人情報、秘密、復旧コード、CSVの個票はチケットへ記録しない。ボードはJSONをscript内へ安全にエスケープし、画面の値はtextContentで挿入する。単独HTMLとして動かす固定スクリプト・CSSのみインライン許可し、CSPで外部通信を禁止する。観光アプリ本体のCSP設定とは別。

## テスト

```powershell
.\.venv\Scripts\python.exe -m pytest test/tooling/test_tickets.py -q
```

受入条件が揃わない完了の拒否、追記履歴の維持、イベント保存後の障害回復、同時コメントの欠落防止、HTML埋め込みの安全性、PJ外パス拒否、履歴破損時の停止、TASKS取込の重複防止を検証する。一時データは `project/.test-work/` 内に作り、試験後に片付ける。
