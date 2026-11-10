# 通う旅 API / schema 12

2026-11-10。陶芸（成形→絵付け→受取）と植物（植付け→手入れ→振返り）の 2 本。各段階は別々の保存済み公開プランに対応する。通常の来訪回数や写真枚数で段階を進めない。

## API

すべて本人認証必須。変更 API は既存の Origin / CSRF / 書込 rate 制限を受け、未知フィールドを拒否する。

| メソッド / パス（`/api` の後） | 入力 / 応答 |
|---|---|
| GET `/daytrip/programs` | `{items:[Program],notice}` |
| POST `/daytrip/programs/{id}/enroll` | `{client_request_id}` → Enrollment |
| POST `/daytrip/programs/{id}/cancel` | `{version,client_request_id}` → Enrollment |
| PUT `/daytrip/programs/{id}/steps/{step_id}` | `{version,outing_id:ID|null}` → Enrollment |
| GET `/daytrip/programs/{id}/outings` | `{items:[{id,title,starts_at,ends_at,plan_id,status}]}`、本人が承諾した対応プランの開催だけ |

Program は `id,title,goal,area,provider:{id,name},recommended_interval,price_basis:'per_person',price_scope:'plan_only',total_price_yen,price_note,steps,enrollment,available,unavailable_reason`。steps は `{id,order,title,purpose,plan_id,plan_title,price_yen,route_id}`。料金は現在の公開プランを読み、各回一人料金の合計・割引前・交通費別である。登録自体は予約・購入・決済ではない。

Enrollment は `version,status:'active'|'completed'|'cancelled',completed_count,total_steps,steps`。進捗 steps は `{step_id,status:'unplanned'|'planned'|'awaiting_confirmation'|'completed'|'invalid',outing_id:null|ID,has_link:boolean,reason:null|string}`。未登録の enrollment は null。`has_link` は本人が保存した紐付けの有無であり、開催の詳細閲覧権を示さない。閲覧権失効時は `outing_id=null` のまま、本人の解除入口だけ `has_link=true` で維持する。

## 達成・取消・権限

完了は本人の全行程参加、本人以外の有効な参加者の確認、事業者の利用確認、開催終了を毎回照合する。前工程が確認待ち・取消なら後工程も完了としない。同じ開催は本人の別段階に再利用できず、同じプログラム内は JST の別日で工程順に実施する。未来の予定や自己申告だけでは完了にならない。表示は「全段階の利用確認済み」とし、作品品質等を推測しない。

本人以外の enrollment ID を入力する API はない。事業者の参加確認は既存の事業者権限付き日帰り API が行い、この API はその事実を参照する。共有失効・所属離脱等で読めない開催の ID は進捗応答でも出さない。開催取消・個人取消・証人失効を次回取得で再評価する。

登録・取消は送信キーで再送に対応。取消は登録を cancelled にして紐付けを解除し、元の開催・参加実績・ポイント・割引は変更しない。新しい送信キーで再登録できる。紐付け変更は version 競合で 409。GET で最新状態を取得する。公開プランが閉じた場合、未登録者の一覧から外れる。既存登録者には登録時公開スナップショットを `available=false` で返し、料金を登録時参考値と明示する。非公開後の編集内容は返さず、取消と紐付け解除を継続できる。

schema 12 は本人登録、段階紐付け、変更履歴の 3 テーブルのみを追加し、旧行を変更しない。

## 初期素材の投入

明示 CLI `python -m app.programs.seed --apply`。schema 12 および `app.operational_seed` の適用後に実施する。startup は seed を呼ばない。新規 6 プランと 2 プログラムを用意する。利用者の指示に基づく架空履歴として、あおいの陶芸第 1 工程だけ利用確認済み、他 2 工程は未計画、植物は未登録とする。事業者・仲間を含む確認履歴は新しい開催として追加し、過去の一般プランの開催を目的達成へ読み替えない。

manifest `program-content-20261110-v1` と `program26-` / `program-n-nishi-` の ID で一度だけ追記する。N西市・参加・プランは架空で、実際の来訪や作品完成の証拠ではない。実 DB への適用は主担当が行う。

## 実試験と修正履歴

最終専用 5 試験が 2026-11-10 に全成功（15.78 秒、`artifacts/programs/pytest-final.xml`）。本人認可・CSRF・余分な入力拒否、二重送信、取消後再登録、同 JST 日拒否、工程プラン照合、予定と実施の分離、前工程訂正時の再計算、証人失効、非公開後の管理と私的編集非露出、seed の全既存行保全・再適用・FK、schema11→12失敗 rollback を含む。

初回結合 8 試験では 7 成功 / 1 失敗（`artifacts/programs/pytest.xml`）。共通 `require()` が None だけ拒否するため、承諾・plan・provider の boolean 判定に使うと不一致を拒否できない問題を検出した。明示的な 404 判定へ修正し、当該 1 試験成功（`sequence-final.xml`）、その後上記全 5 試験成功を確認。他の `require()` 全箇所は DB 行または `next(...,None)` で同じ誤用がないことを確認した。

独立読取で非公開化後の本人取消不可を検出し、上記 snapshot 方式へ修正して実試験を追加。source / test の Ruff 0、source C901 0、Bandit 0。実 DB 適用・Docker・実画面は主担当が別途検証する。

追加読取で、事業者停止時に開催 ID を秘匿すると画面の個別解除入口も消える不整合を検出。本人専用 `has_link` を追加した。事業者停止→ID秘匿と解除可否→個別解除→登録取消→元参加記録保持の境界 1 試験が成功（3.16秒、`artifacts/programs/inactive-unlink.xml`）。対象 Ruff 0。詳細 ID の秘匿は継続する。
