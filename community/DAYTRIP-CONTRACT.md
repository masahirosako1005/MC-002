# 日帰り・開催・先達・ランク特典 API（D1）

2026-11-10。追加 API。既存 Cookie / 左右独立認証 / CSRF を共用。外部通信・決済なし。JSON のキーは snake_case。更新競合は409、範囲外の対象は404。実装と専用試験の対象契約。画面・Dockerの結合確認は別記録。

## 読み取り

- `GET /api/daytrip/catalog` → `{routes:[Route],rules:{version,base_points:100,distance_cap_km:200,leader_points:50,rank_thresholds:[0,300,800,1500]},plans:[{plan_id,provider_id,route_id}]}`。Route は `id,origin,destination,mode,one_way_km,one_way_minutes,distance_note,source_url,checked_on,zone`。zone は `target/nearby/outside/unknown`。参考経路距離で実測GPSではない。
- `GET /api/circles/{circle_id}/outings` → `{items:[Outing]}`。受諾済み本人だけ。
- `GET /api/daytrip/outings/{id}` → Outing。旅行者の所属、または対象事業者の有効な担当者・参加承諾・講の共有継続を検証する。事業者の競合後再取得にも使用し、内部会話・写真は含めない。
- `GET /api/daytrip/me` → `{points,eligible_points,rank,eligible_rank,next_rank_points,completed_count,leader_count,ledger:[{id,outing_id,kind,points,eligible_points,reason,created_at}],benefits:[Benefit],redemptions:[Redemption]}`。ランクは1〜4。金銭特典資格は `eligible_rank` のみ。
- `GET /api/daytrip/provider` → `{plans:[既存の自社Plan],links:[{plan_id,route_id}],outings:[Outing],benefits:[Benefit],redemptions:[Redemption]}`。

`next_rank_points` は次の閾値の総点（最上位はnull）。金銭特典は `eligible_points>0` かつ `eligible_rank>=min_rank` が必要で、0点の一段や自己申告点だけでは使えない。台帳kindは `award/verify/reverse`。targetは最新指定の片道20〜40km（両端含む）、20km未満nearby、40km超outside。参考時間は別表示で、往復参考時間より短い開催を拒否する。旧120分を距離分類の条件にしない。

## 開催

- `POST /api/circles/{circle_id}/outings` body `{title,route_id,starts_at,ends_at,participant_ids,leader_id,plan_id:null|string,client_request_id}` → Outing。日時はoffset付きISO、同日(JST)、未来の開始、2人以上。代表者のみ。plan_id:nullでは事業者なしの開催。plan_id指定時は0泊公開プラン、経路の事業者設定、対象人数/開催日、当該プランについて事業者が参加承諾した共有相談が必要。共有したプラン版と現在版が異なる場合は409とし、最新版での共有・参加承諾を案内する。古い表示料金を新しい保存料金へ黙って変更しない。
- `POST /api/daytrip/outings/{id}/leader` body `{leader_id,version}` → Outing。開始前、代表者のみ。本人承諾をリセットし履歴を残す。
- `POST /api/daytrip/outings/{id}/accept` body `{version,accept_leader:false|true}` → Outing。開始前、対象本人の参加承諾。先達本人は `accept_leader:true`。
- `POST /api/daytrip/outings/{id}/claim` body `{version,full_route:true|false}` → Outing。終了後、事前承諾した本人の実参加申告。
- `POST /api/daytrip/outings/{id}/confirm` body `{version,participant_id}` → Outing。終了後、自分も実参加申告した別の参加者が確認。各人一日一開催のみ加点。先達加点は別の参加者による確認が必要。
- `POST /api/daytrip/outings/{id}/provider-confirm` body `{version,participant_ids:[...]}` → Outing。終了後、当該事業者のスタッフが利用確認。自己の分を承認不可。相互確認済みの人のみ。新規加点せず、当該実績の金銭特典対象ポイントを有効にする。
- `POST /api/daytrip/outings/{id}/cancel` body `{version,reason}` → Outing。代表者。加点は相殺台帳、未使用特典は取消、利用済み特典は調整確認フラグ。元実績は削除しない。
- `POST /api/daytrip/outings/{id}/participants/{user_id}/cancel` body `{version,reason}` → Outing。本人または代表者が誤参加/欠席を訂正する。本人の参加を失効し点を相殺する。この人が確認した別の参加者は「確認待ち」へ戻して点と資格点を相殺するが、その別人の自己申告と証言は取り消さない。別の有効な実参加者が再確認でき、事業者利用も改めて確認する。対象者の不参加と確認根拠の失効を分け、無関係な参加者を不参加にしない。

Outing: `{id,circle_id,title,route,starts_at,ends_at,status,version,leader_id,leader_accepted,plan_id,provider_id,participants:[{user_id,name,accepted,claimed,full_route,confirmed_by,provider_verified,points,revoked}],can_manage,is_provider,created_at}`。フラグ値はJSON boolean。
status: `scheduled/reporting/confirmed/cancelled`。全員相互確認でconfirmed、一部申告でreporting。見積合意や閉鎖からの自動実施認定はしない。予定・参加・実施確認を別に保存。

## 事業者が設定する経路と特典

- `PUT /api/daytrip/plan-routes/{plan_id}` body `{route_id}` → `{plan_id,route_id}`。自社の0泊プランのみ。
- `POST /api/daytrip/benefits` body `{plan_id,title,min_rank,discount_type:'amount'|'percent',discount_value,max_discount_yen,max_redemptions,starts_on,ends_on}` → Benefit。自社公開0泊・一人料金のみ。事業者負担・併用不可。勝手な初期特典なし。
- `POST /api/daytrip/benefits/{id}/close` body `{version}` → Benefit。未使用の確保も取り消す。
- `POST /api/daytrip/benefits/{id}/reserve` body `{outing_id,client_request_id}` → Redemption。本人の特典資格・参加承諾・開催日・対象プランを確認。1人1開催1件、金額は公開プランの一人料金から計算し保存。
- `POST /api/daytrip/redemptions/{id}/redeem` body `{version}` → Redemption。当該事業者のみ。終了後、本人の実参加相互確認と事業者利用確認、特典資格・条件を再確認。二重利用しない。
- `POST /api/daytrip/redemptions/{id}/cancel` body `{version}` → Redemption。未利用は本人または事業者が取消可。使用済みを戻して再利用させない。

Benefit: `{id,provider_id,plan_id,title,min_rank,discount_type,discount_value,max_discount_yen,max_redemptions,starts_on,ends_on,status,version,funding:'provider',combinable:false}`。statusはpublished/closed。
Redemption: `{id,benefit_id,outing_id,user_id,provider_id,status,version,original_yen,discount_yen,total_yen,adjustment_required,created_at}`。statusはreserved/redeemed/cancelled。入金/予約確定ではなく、アプリ内の割引適用記録。

## 保存と境界

開催・先達・利用確認・ポイント取消は本人/当該講/当該事業者だけ。事業者には開催参加者の利用確認に必要な情報のみ渡し、内部会話や非公開の写真/位置を含めない。本人の総ポイントは事業者へ開示しない。旧訪問や振り返りは換算しない。計算規則D1、取消前後の台帳を保持。取消後もその本人の日別付与枠を保持し再作成による水増しを防ぐ。

参加100 + floor(min(参考往復km,200)/10) + 先達50。部分参加は参加100点のみ、距離不明は距離0点。先達は事前本人承諾と全行程参加、別人の確認が必要。ランク閾値0/300/800/1500、役割とランクは別。先達の開催後付替は初版不可。加点・取消・再確認を追記し、同じ開催の再確認では実効残高を一開催分へ戻す。別開催への同日枠の再利用は不可。所属を失って再加入しても旧参加承諾は復活しない。

割引は開催作成時の公開プラン版と一人表示料金に限定。確保時にプラン版・料金対象/注記・特典条件・通常額/割引額/適用後額を保存する。事業者が公開した単一の表示額を対象とするが、外部の確定見積/決済ではない。現プランが改訂された場合は利用を409で止め、過去の額を変えない。割合の端数は円未満切捨て、通常額と事業者の上限額を超える値引きはしない。確保と利用時に資格を再判定し、今回の実績で今回の割引資格を作らない。取消で資格不足となった未使用分を取り消し、既利用分は金額を保持して調整要確認とする。事業者の総枠は確保と利用の合計で検査する。

schema10追加：講退出・コミュニティ退出・アカウント無効等で参加が失効すると、その本人・その開催の未利用特典だけ自動取消して枠を戻す。講全体の閉鎖や事業者参加の失効では、該当開催の未利用分を取り消す。利用済みの状態・金額・調整フラグ、別本人や別開催の有効な確保、ポイント台帳は変更しない。schema9へ既に保存された利用不能な未利用分も、起動時の追加移行で同じ範囲だけ整理する。移行の再実行は無変更、失敗は全体を戻す。schema8からは従来のデータ保全移行と連続してschema10まで進む。

未実装：開催後の先達付替、既利用額の精算/返金、現地訪問の外部認証、4時間滞在の自動評価、経路の自動生成、外部予約。実参加・利用の確認は人の申告であり、物理的訪問の保証ではない。初版の日時/経路変更は旧開催の取消と出発前の新規作成を使う。
