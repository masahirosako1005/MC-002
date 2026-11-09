# 関連する旅行プラン・開催日時・講の候補カード（CP38 / schema5）

2026-11-09。実行時はローカル。表示するのは保存済みの公開事業者プランであり、架空の口コミ・人気指標・未保存イベントを生成しない。候補保存は参加招待・予約・訪問実績とは別操作。

## 公開プランの日程

ProviderPlanの入出力に次を追加する。既存の保存データは書き換えず、読み出し時にon_requestを補う。

- `schedule_type: 'on_request' | 'dated'`（初期値on_request）
- `starts_at: string | null`, `ends_at: string | null`（初期値null）
- datedはタイムゾーン付きISO8601の開始・終了日時を必須とし、終了>=開始。保存時はUTCへ正規化する。on_requestは両方null。
- 日時は事業者が登録した開催日時/期間であり空席確認ではない。未登録は「日程は相談」と表示。終了日時より現在が後なら終了扱い。希望開始日を指定した場合は、その日本時間の日が開催期間に含まれることを比較する。開催期間内の各日に同じプランが出発する保証ではなく、営業・空席・移動は別の未確認事項。
- 事業者自身は過去・下書き・公開停止も編集できる。一般の探索は終了済み/非公開を除外。条件比較・選択・参加承諾でも日程を再検査し、順位で不適合を相殺しない。

## 関連度順の探索

`GET /api/plan-discovery?community_id={cid}&circle_id={pid任意}`

応答:

`{items:[{plan:ProviderPlan,score:number,reasons:string[],unknowns:string[],match_status:string,schedule_status:'on_request'|'upcoming'|'ongoing'}],context:{community_id,circle_id:null|string,profile_used:boolean,requirements_version:null|number},method:'consented-relevance-v1'}`

- 同じactiveコミュニティに所属する本人だけ。circle_id指定時は、そのコミュニティの参加承諾済み講メンバーのみ。
- 本人のpreferences.tagsは、当該コミュニティへのuse_matching許可が現在有効な場合だけ使用。他者の非公開嗜好を使わない。プロフィール空/許可なしなら講のtagsと確定したrequirements.interestsだけで順位を付ける。
- 各一致タグに、本人の許可済み関心2点・講の希望3点・確認済み旅行条件の関心3点。表示理由は実際の一致を説明。人気・評価点ではない。
- 確定条件がある場合は既存の人数/泊数/予算/日程照合でeligibleなものだけ。条件未確認なら確認を促し、合致済みと主張しない。同点は開催開始日時、最後にplan IDで安定した順。
- プロフィールに由来する理由は本人だけの探索応答へ返す。講へ保存するカードに個人プロフィールのタグや理由を複製しない。

CircleSummaryに`tags:string[]`を追加。代表は`PUT /api/circles/{pid}/preferences` `{tags,version}`で講の希望タグを更新し、返り値はCircleDetail。現在の版・代表権限・open状態を検査し、版を増やす。変更後の探索は最新タグで再計算する。確定条件の関心は既存requirements更新を使う。

## 講に候補を保存する

- `GET /api/circles/{pid}/candidate-cards` → `{items:CandidateCard[]}`。
- `POST /api/circles/{pid}/candidate-cards` `{plan_id,plan_version,client_request_id}` → CandidateCard。
- acceptedメンバーが、現在公開中・期限内・確定条件に明確な不適合のないプランを保存できる。確認したplan版が変わっていたら409。
- 保存時に参加招待、selection、consultation、予約、訪問を作らない。代表でなくても候補を持ち寄れる。
- `UNIQUE(party_id,plan_id)`で重複保存しない。同じ送信キーと内容は再送可能、不一致409。別キーで同じプランを再度選んだ場合も既存カードを返し、snapshotを無断更新しない。
- 上限は講100カード。追加/読込の権限は各transaction内で再確認。保存後も同じ講の候補一覧で再読できる。

CandidateCard:

`{id,circle_id,plan_id,plan_version,snapshot:ProviderPlan,saved_by:User,created_at,version:1,current_state:'available'|'updated'|'unpublished'|'ended'|'conditions_changed',current_plan:ProviderPlan|null,reasons:string[],unknowns:string[]}`

- snapshotは保存した時点の公開内容。current_planは現在も公開中の場合のみ（下書きや公開停止後の新内容を漏らさない）。
- current_stateは現在の公開状態・開催終了・確定条件・版変更から算出。available以外は変更状態を示す。updatedでは最新詳細を本人が確認して選び直す。unpublished/ended/conditions_changedは事業者招待へ進めない。
- reasonsは講の希望/確定条件由来だけ。他人へ公開されていない本人の嗜好はカードに保存しない。
- 後続の事業者参加依頼は既存circles provider-invitationsでplan/version/requirements_versionと共有確認を再検査する。カード保存を共有同意として代用しない。

schema5はcircle_candidate_cards追加のみ。schema2→3→4→5は既存表の内容を初期化しない。開催日時はprovider_plans.bodyの許可された新フィールドとして保存するため既存行の再保存を強制しない。
