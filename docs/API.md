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

## 実装時の互換補足

- `Experience.season` と `Plan.season` は四季に加え `all`（通年）を取り得る。安産祈願・お宮参りを季節に固定しない。`month_label` は `希望する時期に`。カタログの現在季節、ゲーム、実績とrecommendationsのseason入力は四季のまま。
- recommendationsは指定季節と通年体験を対象にする。現在季節は日本時間の現在時刻・営業日・体験終了時刻を検証する。将来季節は次の旅の候補として返し、開催日・営業時間の再確認を理由に含める。
- 営業時間や移動時間は架空都市の設定。会議館を固定の発着地とし、徒歩往復＋体験＋10分の余裕。利用者の実際の移動速度、天候、臨時休業は未確認。
- `POST /session` は有効セッションがある場合CSRFを要求する。初回はOrigin検証のうえCookie発行。初期表示は `GET /session`、401時に `POST /session` の順で利用する。DELETEにもJSON Content-Typeが必要。
- 通常エラーに加えて408（送信時間超過）、413（本文16KiB超過）、415（JSON以外）を返す。API応答はno-store。すべてのエラーは `{detail:string}`。
- 問題ID例 `gate-autumn-beginner-2026-v1`。季節年・難易度・版が異なる得点を混ぜない。ゲーム開始には当日同スポット訪問、回答・ヒント時にも当日訪問が必要。完了再送だけは時期が変わっても元結果を返す。
- セッションは匿名のブラウザー保存で180日有効。別端末・Cookie消去・期限後は下記の復旧コードで同じ手帳へ戻る。DBバックアップと、利用者の認証の復旧は別の問題として扱う。

## 手帳の復旧

- POST `/recovery` body `{}` → `{recovery_code:string}`。要セッション・CSRF・Origin。256bitのコードを発行/更新し、この応答で一度だけ表示する。DBはSHA-256のみを保存し、生コードの再取得APIはない。再発行で古いコードは失効する。
- POST `/session/recover` body `{recovery_code:string}` → `{nickname,csrf_token}` と新しいセッションCookie。未認証で利用でき、必ずOrigin・JSONを検証する。有効な既存Cookieがある場合はそのセッションのCSRFも要求する。復旧成功は以前の全セッションを無効にする。
- 復旧コードはセッション寿命に依存せず、次の再発行まで有効。コードを知る人は手帳へアクセスできるため、端末内の安全な場所へ保存し、URL・ログ・ランキング等へ出さない。応答はno-store。
- 無効コードは一般的な401を返し、コードの内容や所有者を出さない。復旧要求はIPあたり5回/分、超過は429。コードを失った場合の本人確認による救済は未実装。
