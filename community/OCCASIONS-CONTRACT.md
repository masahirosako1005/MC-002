# 誕生日・記念日の提案 API 契約（CP40 / schema7）

日付は本人登録のみ。本人の誕生日は月日だけ、任意の記念日は名前/月日/毎年または一度を保存する。写真・会話・年齢から推定しない。初期は共有先なし、提案利用OFF。バックエンドと隔離API試験を実装済み。Docker配信・実画面・実保存データ移行の確認は別途記録する。

## 本人の登録

- `GET /api/me/occasions` → `{items:Occasion[],circles:[{id,title,community_id}]}`。本人が参加済みで現在openの講だけを共有先として返す。
- `POST /api/me/occasions` → Occasion。body `{kind:'birthday'|'anniversary',name,month,day,repeats_annually,year:null|number,client_request_id}`。birthdayはname='誕生日'固定/毎年/年null、1人1件。anniversaryはname1〜60文字、年は一度だけの場合必須。上限20件。
- `PUT /api/me/occasions/{id}` 同じ内容＋`version`（client_request_idなし）。本人のみ、古い版409。
- `DELETE /api/me/occasions/{id}` `{version}` → `{ok:true}`。本人のみ。起因する共有・提案・専用起因候補は即失効。
- `PUT /api/me/occasions/{id}/sharing` `{version,sharing:[{circle_id,share_date:boolean,suggest:boolean}]}` → Occasion。日付共有と提案利用は別チェック。suggest=trueはshare_date=true必須。配列にない講は撤回。所属/承諾/open状態をtransaction内で確認する。
- Occasion = `{id,kind,name,month,day,repeats_annually,year,version,sharing:[{circle_id,circle_title,share_date,suggest}],next_occurrence:null|Occurrence}`。
- Occurrence = `{occurrence_date:'YYYY-MM-DD',occurrence_year,days_until,leap_adjusted}`。JST今日から30日後まで両端含む。2/29は非うるう2/28、元月日は変更しない。

本人の編集は既存の共有対象に適用するが、過去の提案から保存した記念日起因カードの許可版は引き継がない。共有取消・提案OFF・所属解除では許可版を進め、再許可/再加入だけで過去の記念日起因カードを復活させない。

## 提案と本人の状態

- `GET /api/circles/{pid}/occasions` → `{items:[{id,owner:User,kind,name,month,day,repeats_annually,year,next_occurrence,suggestions_enabled}]}`。参加済み本人のみ。share_date=trueの項目だけを返す。日付共有は登録者名・記念日名・月日（一度だけの場合は年）を含むと設定画面に明示する。提案OFFでも日付共有を選んだ項目はこの一覧で見られる。
- `GET /api/occasion-suggestions?circle_id={pid}` → `{items:OccasionSuggestion[]}`。参加済み本人のみ。選択講へ共有し提案利用を許可した近接記念日を返す。事業者の共有相談経由では読めない。最大100件。
- `GET /api/me/occasions/{id}/preview?circle_id={pid}` → OccasionSuggestion。本人は非共有/OFFでも自分だけの候補を確認できる。共有設定にかかわらずpreviewは常にshared=false。講の参加権限は必須。共有保存は後述の通常候補追加を本人が選ぶ。
- Suggestion = `{id,occasion_id,owner:User,name,kind,occurrence:Occurrence|null,circle_id,occasion_version,state:'new'|'later'|'dismissed',version,shared:boolean,candidates:DiscoveryItem[],notice}`。previewの窓外だけoccurrence=null。idは記念日×講×発生年の安定識別子。同年の再読で重複しない。日付変更でも同年stateは保持し、現在の公開条件を毎回確認する。
- `PUT /api/occasion-suggestions/{id}/state` `{state:'new'|'later'|'dismissed',version}` → Suggestion。状態は操作本人ごと。あとで/見送りを他会員へ強制しない。初期version=0、以降古い版409。
- shared=falseのpreviewはstate操作不可。日付が30日窓外なら候補なし・noticeを返す。通常一覧は窓外を返さない。外部通知/自動送信は行わない。

公開プランのみ。本人の関心は記念日の登録者が当該コミュニティへ現在use_matchingを許可した場合だけ利用する。他者向け理由へ本人の個別関心タグは複製せず、講タグ・条件の理由を表示する。希望関連度主順位/CP39の匿名参考は同点補助を維持。確定した人数/泊数/予算/日付を厳格照合し、記念日の発生日も開催期間内であることを確認。確定日が別日なら候補なしで条件確認を促す。未登録日時は「日程は相談」、特典/空席は生成しない。

## 講の候補へ保存

- `POST /api/occasion-suggestions/{id}/candidate-cards` `{plan_id,plan_version,occasion_version,client_request_id}` → 既存CandidateCard。現在の提案共有許可/所属/公開プラン版/開催日時/条件を同じtransactionで再検証。カードは公開プランのsnapshotだけで、日付/名前/登録者/個人理由を追加しない。参加招待・予約・実利用にはしない。
- 非共有previewからの追加は、本人が通常の`POST /api/circles/{pid}/candidate-cards`を明示実行する。記念日の共有ではなく、通常プランを独立して持ち寄る操作として画面に示す。
- 既存UNIQUE(party,plan)とsnapshotを維持。旧カード表の値は移行で変えず、追加のsource表で記念日起因を管理する。source行なしの既存カードは独立保存として扱う。記念日だけで初作成されたカードはindependent=false。後から通常追加を行った場合だけtrue。別記念日から同じplanを保存した場合はsourceを追加する。
- 一覧は独立保存、または有効な記念日起因sourceが1つ以上あるカードを返す。削除/共有撤回/提案OFF/日付編集/登録者の所属解除でsourceが失効すると、専用起因カードは即非表示。独立保存もあるカードを消さない。
- 保存後に単に30日窓を外れる・当日を過ぎるだけではsourceを失効しない。保存した候補は許可が有効なら残し、開催終了は既存カードcurrent_state='ended'で示す。近接提案の一覧は期間外になると消える。
- originを公開snapshot・provider invitation・共有相談へ渡さない。事業者への参加依頼は既存の明示共有確認を通す。記念日側の撤回はすでに明示して送った通常プランの事業者招待を自動取消ししない。

全APIは既存認証/CSRFを適用。本人CRUD、講閲覧、版、冪等、所属をtransactionで検証。所属解除の共有失効はラッチとして保存し再加入で復活させない。schema7は追加表/triggerのみ、旧表の行内容を移行で変更しない。
