# ローカルAPI契約 v1

ReactとPython FastAPI、SQLiteを採用。単一オリジン。API prefix `/api`。JSON。認証はサーバー発行のHttpOnly SameSite=StrictセッションCookie。書込はOrigin検証とJSON Content-Type必須。ユーザーIDをクライアントが指定して権限を切替えない。初回のPOST /sessionで匿名の旅の手帳を発行、以降同じブラウザーで保持する。

## エンドポイント

- GET `/health` → `{status:"ok"}`
- POST `/session` body `{}` → `{nickname:"旅人",csrf_token:string}`。既存セッションは再利用。以降のPOST/DELETEは`X-CSRF-Token`必須（新規sessionのみ例外）。GET `/session` → 同じ形または401。
- GET `/catalog` → `{city:string,season:string,spots:Spot[],experiences:Experience[],games:Game[]}`（公開）
- GET `/journal` → `{visits:Visit[],attempts:Attempt[],achievements:Achievement[],plans:Plan[]}`（要セッション）
- POST `/visits` body `{spot_id:string,code:string}` → Visit。登録済み同一日スポットは再利用。訪問コードは印刷用現地しおりに配置。公開カタログAPIに正解コードを出さない。
- POST `/attempts` body `{game_id:string}` → `{id,game_id,status,hints_used,puzzle:Puzzle}`。同一の未完了挑戦を再利用。ゲームには同日同スポット訪問が必要、未訪問なら409。
- POST `/attempts/{id}/hint` body `{}` → `{hint:string,hints_used:number}`。ヒントは一度だけ適用。
- POST `/attempts/{id}/answer` body `{values:number[]}` → `{correct:boolean,score:number|null,achievement:Achievement|null,message:string}`。完了再送は元結果。正答・得点はサーバー判定。
- GET `/leaderboard?game_id=...` → `{entries:[{rank,nickname,score}],game_id}`。同一ゲーム版で比較、ユーザー識別子を露出しない。
- GET `/recommendations?minutes=90&season=autumn&interest=all` → `{items:Recommendation[],reason:string}`。minutes整数15..240、season spring/summer/autumn/winter、interest all/shrine/coast。往復・滞在・余裕時間と季節/営業条件検証。
- POST `/plans` body `{experience_id:string,reason:string}` → Plan。利用者と体験で重複保存を防ぐ。
- DELETE `/plans/{id}` → `{ok:true}`。自分の記録のみ。

## 表示用データ型

Spot = `{id,name,area,kind,description,walk_minutes,dwell_minutes}`。kind gate/shrine/coast/conference。
Experience = `{id,spot_id,title,season,description,month_label,duration_minutes,kind}`。kind puzzle/event/activity。
Game = `{id,spot_id,title,season,difficulty,description,version}`。difficulty beginner/advanced。
Puzzle = `{title,instruction,labels:string[],max_value:number,clue:string}`。valuesの正解を返さない。水路の条件を手掛かりに3つの水門の値を選ぶ。
Visit = `{id,spot_id,spot_name,visited_at}`。
Attempt = `{id,game_id,title,status,score,hints_used,created_at,completed_at}`。
Achievement = `{id,title,description,earned_at,season}`。
Plan = `{id,experience_id,title,spot_name,season,month_label,reason,created_at}`。
Recommendation = `{experience:Experience,spot:Spot,total_minutes,travel_minutes,buffer_minutes,reason}`。

## エラー・履歴

通常エラーは `{detail:string}`。詳細は日本語。HTTP 400/401/403/404/409/422/429/503を用途に応じ使用。例外・SQL・秘密を返さない。更新はSQLiteトランザクション、一意制約、外部キー。データはDocker volumeへ保存。季節と年度・問題版はサーバー時刻から固定し履歴を上書きしない。試験用時刻はPythonの依存差替えに限定。

## 仮の表示名

製品は正式表記確認前のため `tang you chi`。架空都市は `平城京市` を暫定使用。画面に制作事情を散在させず、設計書とREADMEに仮設定を明記する。
