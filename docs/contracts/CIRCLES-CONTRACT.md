# 講・対話・事業者参加 API（schema4 / CP32–35）

2026-11-09。全APIは `/api` 配下、既存認証/CSRF。新講は `travel_parties` を再利用する。pending招待は会員ではない。新機能の事業者招待はpending中にconsultationを作らず、受諾後だけ共有相談を作る。画面を一つにしても、内輪会話・AI対話と事業者共有区間の権限は分ける。

## 1. 旅仲間の候補と招待

- `POST /circles/candidates` `{community_id,tags:string[],desired_count:number}` → `{items:[{user:User,common_tags:string[]}],desired_count,available_count,shortage_count,method}`。desired_countは本人を含む2〜20人。候補は同じactive所属・ログイン可能・本人許可(use_matching/display_matching/participate)・確認タグ一致の人だけ。本人をitemsから除き、available_countは本人込み。候補表示は参加承諾ではない。
- `POST /circles` `{community_id,title,mode:'recommended'|'manual',tags:string[],desired_count,invitee_ids:string[],client_request_id}` → CircleDetail。推薦modeは選んだ人を保存直前にも再評価。手動modeはactive会員への明示招待。未操作の人をacceptedにしない。招待上限19人、重複拒否。
- `GET /circles` → `{items:CircleSummary[],invitations:MemberInvitation[],groups:GroupOption[]}`。itemsは本人参加済みの新講と既存travel_party、invitationsは本人宛pending、groupsは本人の既存成立講（未連携も含む）。
- `POST /circles/from-group` `{group_id,client_request_id}` → CircleDetail。既存成立講の現在activeメンバーのみを計画へ接続。新たな参加承諾の代行ではなく、その講の既存承諾を再利用。
- `GET /circles/{id}` → CircleDetail（accepted会員のみ、事業者は利用不可）。
- `POST /circles/{id}/invitations` `{invitee_ids,version,client_request_id}` → CircleDetail。代表限定。追加の招待は明示的な手動招待として扱う。
- `POST /circle-invitations/{id}/respond` `{decision:'accepted'|'declined',version,client_request_id}` → MemberInvitation。本人のみ。現active所属と現在のpending状態をtransaction内で確認。
- `POST /circle-invitations/{id}/cancel` `{version,client_request_id}` → MemberInvitation。代表限定、pendingのみ取消。
- `POST /circles/{id}/leave` `{version}` → `{ok:true}`。代表以外の本人のみ。退出後の内輪/共有区間閲覧拒否。コミュニティ退出でも招待取消・参加削除し、再加入で自動復活しない。
- `POST /circles/{id}/close` `{version}` → CircleDetail。代表限定、招待と共有区間を閉じる。

CircleSummary = `{id,community_id,title,representative_id,can_manage,status,version,mode,desired_count,accepted_count,pending_count,shortage_count,requirements:null|Requirements,active_provider_invitation:null|ProviderInvitation}`。
CircleDetail = CircleSummary + `{members:User[],invitations:MemberInvitation[]}`。
MemberInvitation = `{id,circle_id,circle_title,invitee:User,inviter:User,status,version,created_at}`。
GroupOption = `{id,purpose,community_id,member_count,circle_id:null|string}`。

推薦許可は候補表示・招待作成時に再確認する。送信済み招待への本人の参加意思は別であり、その後関心利用を取り消しても本人が明示承諾することはできる。退会の場合は招待自体を取り消す。既存成立講が一部会員だけの計画へ接続済みの場合、本人が参加する既存計画だけ再利用し、未接続の本人は同じ成立講の別計画へ接続できる。

## 2. 内輪会話・ローカル案内対話

内輪会話は既存 `GET/POST /travel-parties/{id}/messages`（POST `{body,client_request_id}`）を再利用。条件確認も既存 `PUT /travel-parties/{id}/requirements` を再利用。代表のみ確認保存。planned_peopleは実参加人数とは別。

- `GET /circles/help` → `{method:'local-catalog-rules-v1',external_ai_enabled:false,description,limitations:string[]}`。
- `GET /circles/{id}/assistant-turns` → `{items:AssistantTurn[]}`。
- `POST /circles/{id}/assistant-turns` `{body,client_request_id}` → AssistantTurn。
- AssistantTurn = `{id,user_body,author_name,reply,proposed_conditions:Partial<Requirements>,missing_fields:string[],ambiguities:string[],candidates:[{plan:ProviderPlan,reasons,unknowns,estimated_total_yen}],requirements_version:number,method,needs_confirmation:true,created_at}`。

複数ターンで人数・泊数・金額・単位/範囲・日付・関心を整理。複数数値/否定などは曖昧として本人確認を求める。提案条件は保存済み条件とは別。候補は実際の公開planに既存の人数/泊数/予算照合を適用してeligibleだけを返す。必要条件が不足なら候補を捏造しない。招待・行き先確定・外部送信は発話から自動実行しない。外部AIは未設定/未接続。

## 3. 行き先決定と事業者の参加

- `POST /circles/{id}/provider-invitations` `{plan_id,plan_version,requirements_version,share_note,sharing_confirmed:true,version,client_request_id}` → ProviderInvitation。代表が確定条件/選択plan/共有文を確認して招待。versionはCircleSummary.version。同時に有効な招待は1件だけ。
- `GET /circle-provider-invitations` → `{items:ProviderInvitation[]}`。当該事業者のactive staffのみの受信一覧（pending/accepted、直近100件）。
- `POST /circle-provider-invitations/{id}/respond` `{decision:'accepted'|'declined',version,client_request_id}` → ProviderInvitation。当該staff本人操作。受諾時に条件/plan版が変わっていたら409で再確認。
- `POST /circle-provider-invitations/{id}/cancel` `{version,client_request_id}` → ProviderInvitation。代表のみ。承諾済みも閉鎖し共有区間を失効できる。
- ProviderInvitation = `{id,circle_id,provider:{id,name,area},inviter_name,status,version,snapshot:{plan,shared_conditions,share_note,requirements_version,unknowns},consultation_id:null|string,created_at,accepted_at:null|string}`。内輪のタイトル/会話/写真/個人関心/招待会員リストは含めない。
- `GET /circle-provider-invitations/{id}/room` → `{invitation:ProviderInvitation,messages:Message[],proposal:null|Proposal,can_propose:boolean,can_confirm:boolean,my_role:'traveler'|'provider',reservation_status:'not_booked'}`。当該accepted招待の現旅行者会員と当該staffだけ。
- `POST /circle-provider-invitations/{id}/messages` `{body,client_request_id}` → Message。共有先を明示した区間の投稿だけ。既存consultation_messagesを再利用するが、新招待は別consultation_idで開始する。

pendingではlegacy consultationのIDが存在しない。cancel/closed/declinedは新共有区間の閲覧書込みを拒否し、旧API側のguardにも適用。再招待は新ID/新履歴で、前の共有会話を継承しない。旧機能で作成済みのconsultationsは保持。新講のlegacy `/selections` は拒否し、事業者招待確認へ誘導する。

受諾後の条件編集は内輪の最新版にのみ反映する。共有snapshotは共有確認時の版のまま固定し、事業者へ無断更新しない。変更後条件を共有するには既存招待を閉じ、改めて共有確認・招待を行う。legacy側の相談/計画閉鎖もtriggerで新招待をclosedへ同期する。

## 4. 行程・概算見積と双方確認

- `POST /circle-provider-invitations/{id}/proposals` `{title,date_start:null|string,itinerary:[{day,period,place,description,travel_minutes}],estimated_price_yen,price_basis:'per_person'|'party_total',price_scope:'plan_only'|'whole_trip',price_note,unknowns:string[],version,client_request_id}` → Proposal。事業者staffのみ。versionは直前Proposal.version（初回0）。行程は選択snapshotの泊数+1日を過不足なく含む。
- `POST /circle-provider-invitations/{id}/confirmations` `{proposal_id,version,client_request_id}` → Proposal。旅行者代表か当該staffが各自操作。最新提案版のみ。
- Proposal = `{id,invitation_id,version,title,date_start,itinerary,estimated_price_yen,price_basis,price_scope,price_note,unknowns,created_at,created_by,confirmations:[{role:'traveler'|'provider',user:User,confirmed_at}],status:'awaiting_confirmation'|'both_confirmed',reservation_status:'not_booked'}`。

改訂は新proposal_id/versionとなり両方の確認を引き継がない。旧版の確認と根拠はDBで保持。両者確認後も外部予約・空席・決済は未確定。

## 保存・上限・競合

schema4は追加表/索引/triggerと既存partyへのメタデータ補完だけ。既存写真/旅記録/相談を上書きしない。writeはBEGIN IMMEDIATE、各権限/状態/版チェックと保存を同transactionで行う。client_request_idは同じ入力なら同じ結果、不一致409。取消後の再送で状態を復活させない。講は本人代表100件、対話は講200ターン、招待は講100件まで。GET会話は直近100件、対話は直近100ターン。新プロファイルやキー探索は行わない。
