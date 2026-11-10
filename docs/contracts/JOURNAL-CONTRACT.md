# 旅の記録・位置・実績 API（CP29以降）

2026-11-09。すべて `/api` 配下、既存Cookieまたはstage BearerとCSRF。全APIは認証必須。位置情報は個別の訪問共有、県別実績は独立したプロフィール共有を使う。初期値は非公開。

## カタログと所有者の記録

- `GET /journal/catalog` → `{prefectures:[{id,name,latitude,longitude}],badges:[{id,title,prefecture_ids,description}],evidence_note}`。idはJIS都道府県2桁（愛知23、岐阜21、三重24、静岡22）。座標は概略表示用代表点で境界・測量値ではない。
- `GET /journal/journeys` → `{items:[Journey]}`
- `POST /journal/journeys` `{title,request_key}` → Journey
- `PUT /journal/journeys/{id}` `{title,version}` → Journey
- `DELETE /journal/journeys/{id}` `{version}` → `{ok:true}`（所属訪問も削除し実績を再計算）
- `GET /journal/journeys/{id}` → `{journey:Journey,visits:Visit[]}`。本人限定。
- Journey = `{id,title,version,created_at,visit_count}`
- `POST /journal/visits` VisitInput + `{request_key}` → Visit
- `PUT /journal/visits/{id}` VisitInput + `{version}` → Visit
- `DELETE /journal/visits/{id}` `{version}` → `{ok:true}`
- VisitInput = `{journey_id,prefecture_id,visited_on,place_label,latitude:null|number,longitude:null|number,media_id:null|string,source:'manual'|'exif',visibility:'private'|'community',community_id:null|string,confirmed:true}`。日付はYYYY-MM-DD、当日（日本時間）以前。県と日付・場所・訪問意思の本人確認必須。県代表点は座標なしの場合のみ表示に使い、実地点とは呼ばない。
- Visit = VisitInput + `{id,version,created_at,updated_at,prefecture_name,media_url:null|string,evidence_label}`。confirmed=trueのみ保存。request_keyは出力しない。source=exifは自身の写真からopt-in取得した候補座標と一致する場合のみ。訂正はsource=manualへ。

同じrequest_keyかつ同じ本文の再送は同じ記録を返す。不一致は409。削除後の古いキー再送は復活させない。更新・削除のversion不一致は409。訪問の追加・変更・削除時は所属する旅のversionも増やし、古い旅削除確認で新しい訪問を消さない。旅100件、訪問1000件、旅1件の返却訪問はその範囲で上限1000。写真削除時は写真に紐付く訪問も同じトランザクションで削除し、実績を再計算する。

## 写真と位置候補

- 既存 `POST /media` は位置を取得しない。`POST /media?read_location=true` は、本人が写真選択前に位置取得へ同意した場合のみ使う。戻り値は従来Media + `{location_candidate:null|{latitude,longitude}}`。位置なし/不正EXIFでも手動入力へ進める。
- `GET /journal/media` → `{items:[{id,url,width,height,location_candidate:null|{latitude,longitude}}]}`。本人の未削除写真のみ。候補は他者feed/APIへ追加しない。
- `GET /journal/media/{id}/location-candidate` → `{location_candidate:null|{latitude,longitude}}`。本人限定。
- `DELETE /journal/media/{id}/location-candidate` `{}` → `{ok:true}`。未確定候補を破棄。確定した訪問は別管理で、候補破棄だけでは消えない。
- 写真配信は従来通りEXIF除去後JPEG。GPS以外のEXIF情報を位置候補へ保存しない。写真を訪問に関連付けても写真の既存閲覧権限は広げない。共有訪問の写真は、同じ共有先へ公開された投稿の写真だけ他者へ返す。

## プロフィールと閲覧

- `GET /journal/people?community_id=peers` → `{items:[User]}`。同じactiveコミュニティのログイン可能会員（本人含む）。
- `GET /journal/profile/{user_id}` → Profile。他者は同一activeコミュニティ所属必須。共有なしでもuserと非公開状態のみ返す。
- `PUT /journal/profile` `{share_achievements:boolean,version:number}` → 本人Profile。初期version=1、更新時+1。
- Profile = `{user:User,is_owner:boolean,share_achievements:boolean,version:number,visited_prefectures:Prefecture[],badges:BadgeProgress[],shared_visits:Visit[],evidence_note:string}`
- BadgeProgress = `{id,title,description,prefecture_ids:string[],visited_prefecture_ids:string[],remaining_prefecture_ids:string[],achieved_count:number,total_count:number,earned:boolean}`。他者へ実績非公開ならvisited_prefectures/badgesは空。本人は非公開でも全進捗を確認可能。
- `shared_visits` は本人には全訪問、他者にはvisibility=communityかつ双方が現在activeの指定先だけ。他者へはlatitude/longitudeは常にnull（県代表点で表示）、media_idとjourney_idもnullとし、場所名・訪問日・閲覧権限のある写真のみ共有する。場所名と日付は訪問保存時に共有確認する。訪問共有はバッジ公開から独立し、非共有の座標・場所・日付・旅名・根拠写真は実績公開からは返さない。

バッジ初版は「東海をめぐる」=愛知・岐阜・三重・静岡の4県。本人が確認した訪問県の集合から毎回算出し、重複写真や同県の繰返しで加算しない。取消・訂正で条件を失えば未達へ戻る。EXIFおよび自己申告は物理訪問の第三者認証ではない。候補保存、投稿だけ、写真閲覧を訪問には数えない。

schema3は追加表・索引のみのatomic migration。既存テーブル内容を初期化しない。旧schema2バックアップを保持して配信し、schema3から旧コードへの直接巻戻しは禁止する。
