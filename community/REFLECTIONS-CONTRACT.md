# 旅行後の振り返りから参考情報をまとめる（CP39 / schema6）

2026-11-09。通常の仲間内会話・事業者との共有会話・AI対話・写真を解析対象にしない。選んで実際に利用した事業者について、全対象旅行者が実利用を申告し、用途へ同意した専用振り返り区間だけを使う。外部AI送信なし。自己申告を第三者の利用認証とは称さない。

## 旅行終了・対象者・同意

- `GET /api/circles/{pid}/reflection-options` → `{items:[{invitation_id,provider:{id,name,area},plan_title,earliest_end_on}],reflections:ReflectionSummary[]}`。参加済旅行者のみ。事業者の受諾履歴がある依頼だけを選べる。
- `POST /api/circles/{pid}/reflections` `{invitation_id,ended_on,trip_finished:true,client_request_id}` → Reflection。代表旅行者が終了を申告。ended_onは日本時間の今日以前、共有した出発日と参加依頼受諾日より前へはできない。参加承諾や見積の確認から利用済みを自動認定しない。
- `GET /api/circles/{pid}/reflections` → `{items:ReflectionSummary[]}`。
- `GET /api/reflections/{rid}` → Reflection。
- 1講×事業者につき1区間。旅行者の現在のactive講メンバー全員を対象に固定する。対象事業者のstaffは対象外で、原文の閲覧・投稿・同意・申告も不可。代表が反対者だけを除外する指定は設けない。
- `PUT /api/reflections/{rid}/participation` `{used_service:boolean,version}` → Reflection。本人のみ。versionはmy_state.version。falseに戻すと本人のconsentもfalseへ。
- `PUT /api/reflections/{rid}/consent` `{allowed:boolean,version}` → Reflection。本人のみ。初期OFF。trueには本人のused_service=trueが必要。用途表示は「この振り返りから明確に読み取れる事業者の体験を自動で参考集計へ反映し、おすすめの補助に使います。公開するのは件数と定型の匿名要点だけです」。撤回可能。
- `POST /api/reflections/{rid}/participants-refresh` `{version}` → Reflection。対象者集合が変わった場合、代表が現在の全旅行者へ更新。対象者のepochが変わり、全員の利用申告・同意を初期OFFへ戻す。前epochの明示操作は監査用に保持し現同意として使わない。
- `PUT /api/reflections/{rid}/completion` `{trip_finished:boolean,version}` → Reflection。代表のみ。終了申告の取消で直ちに全集計を無効化。再度trueへする場合はepochを更新し、全員確認をやり直す。

全員の現利用申告・同意、現参加者集合の一致、現active所属、終了申告がそろった場合だけ解析・集計する。退出・参加者追加・利用取消・同意撤回で即時保留。公開値は読取transaction内で現在の権限・状態から再計算し、古いキャッシュを残さない。

ReflectionSummary = `{id,circle_id,provider,ended_on,trip_finished,version,epoch,participant_set_current,ready_for_analysis,target_count,usage_confirmed_count,consented_count}`。
Reflection = ReflectionSummary + `{participants:[{user:User,used_service,consented}],my_state:{used_service,consented,version},messages:ReflectionMessage[],method,usage_notice,consent_purpose,can_manage}`。

対象者更新・終了取消後の再開は新しいepochに切り替える。旧epochの会話を新対象者へ表示・解析・集計せず、新区間では全員の実利用申告・同意を初期OFFから確認する。対象者の一時退出と再参加でも旧同意は復活しない。

## 専用会話と本人の訂正

- `POST /api/reflections/{rid}/messages` `{body,client_request_id}` → ReflectionMessage。全員同意前も専用区間へ投稿できるが、解析しない。
- `PUT /api/reflection-messages/{mid}` `{body,version}` → ReflectionMessage。投稿した本人のみ。
- `DELETE /api/reflection-messages/{mid}` `{version}` → `{ok:true}`。投稿した本人のみ。原文を空にし、自動抽出・訂正値も消す。
- `PUT /api/reflection-messages/{mid}/review` `{version,source_version,values:[{aspect_id,sentiment}]}` → ReflectionMessage。本人のみ。対象事業者の実体験として解析可能な発言だけ。valuesは4観点を重複なく含め、使わない観点はexcluded。全観点excludedで集計除外。新しい発言版への古い訂正は409。
- aspect_id = `guidance`（案内の分かりやすさ）、`response`（対応）、`experience`（体験内容）、`price`（価格への納得）。sentiment = `positive | negative | mixed | excluded`。
- ReflectionMessage = `{id,author:User,is_mine,body,version,source_version,created_at,extraction:{status:'waiting'|'auto_included'|'author_corrected'|'excluded',reason,proposed:[{aspect_id,sentiment}],effective:[{aspect_id,sentiment}],can_correct:boolean,source_version}}`。

全員の利用・同意が揃ったら、明確な自動抽出は追加の発言ごとの承認なしで参考集計へ反映する。本人は後から訂正・除外できる。内部ではautoと本人overrideを分離し、同じ原文版だけへ訂正を対応させる。編集・削除では旧結果を無効化し再解析する。本人訂正も原文版が変われば引き継がない。

対象名を明示した過去の体験表現と限定した評価語だけを扱う。主語不明、他者/他社、未利用、予定・期待、否定/例示の曖昧さ、皮肉の手掛かり、写真・位置・健康・家族・連絡先等の私的記述を含む場合は不使用。一般的な日本語や皮肉を完全に理解する保証はなく、対象範囲が狭いローカル規則である。除外発言をreviewで強制的に評価へ変えることはできず、本人が対象事業者の体験として書き直す。

## 匿名公開と順位

- `GET /api/providers/{provider_id}/experience-summary` → PublicExperienceSummary（認証済み利用者向け、講への所属不要）。
- PublicExperienceSummary = `{status:'available'|'insufficient',trip_count:null|number,minimum_trip_count:3,facets:[{aspect_id,label,status:'positive'|'negative'|'mixed'|'insufficient',trip_count:null|number,summary:string}],method:'local-reflection-rules-v1',note,ranking_signal:number}`。
- 1講×事業者×観点を1単位。同じ講で同観点を連投しても件数を増やさない。複数人/発言に肯否があればmixed。未評価やexcludedは0点の否定へ変換しない。
- 公開は各観点で最低3講、かつ異なる3投稿者以上。少数の肯否内訳を露出しないため、非ゼロの傾向カテゴリが3講未満ならその観点を保留する。全員肯定3講、全員否定3講、混在3講などが表示対象。公開しない観点の件数はnull。
- 公開情報に個人名、原文、講名、日時、位置、内部の出典IDは含めない。要点は固定の匿名文のみ。表示可能な観点がなければstatus=insufficient/trip_count=nullで、未評価を低評価と扱わない。
- `plan-discovery.items[].experience_reference`に同じ公開情報を追加。希望との関連度scoreは変更しない。同点だけ、公開可能な観点のpositive=1/negative=-1/mixed=0の平均ranking_signalを補助に使用する。保留/未評価は中立0。人数・予算・日程の不適合は依然除外する。

上限は1区間100発言/本文1000文字。writeは既存認証/CSRF、transaction内の本人・対象・版確認、送信キーで冪等。schema6は追加表のみで既存会話を取り込まない。
