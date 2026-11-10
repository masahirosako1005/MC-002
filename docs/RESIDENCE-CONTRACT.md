# 居住地域・登録と事業者の地域集計

2026-11-10。市区町村単位の本人登録を追加する。番地、建物、郵便番号、自由文住所、GPS、個別の緯度経度は入力・保存しない。推測・CSV・写真EXIFから居住地域を補わない。N西市は大阪府内を想定した架空の目的地（34.83, 135.50）である。

## 公開カタログ

`GET /api/residence/areas`（未ログイン可）:

```text
{items:[Area], destination:Destination, precision:'municipality_representative'}
Area = {id,prefecture,city,label,latitude,longitude}
Destination = {id:'n-nishi',name:'N西市',prefecture:'大阪府',latitude:34.83,longitude:135.50,fictional:true}
```

47都道府県の県庁所在市区と近隣22市の計69市区。全国の全市区町村を網羅するものではない。東京は新宿区。未掲載の市区町村に住む人は地域を未登録として登録を完了できる。府県を選んだだけでその県庁所在市に居住していると扱わない。

主要ID：大阪市27100、堺市27140、京都市26100、神戸市28100、奈良市29201、吹田市27205。IDは変更しない。座標は小数第2位までの**表示用の概略代表点**であり、市区町村境界・居住者の実際の所在地・測量値・道路距離を表さない。全国点は既存journalカタログを再利用し、近隣点は地域の目安としてローカルに定義した。実行時の外部ジオコーディング/地図素材配信はない。

参考：国土地理院の[位置情報の確認方法](https://web2.gsi.go.jp/KOKUJYOHO/center-faq.html)、地震調査研究推進本部の[大阪府内観測点の位置表](https://www.jishin.go.jp/main/chousakenkyuu/uemachi_juten/h23/23Report_Chap3_4_1.pdf)、伊丹市の[市の位置](https://www.city.itami.lg.jp/mirai/sinosyoukai/21179.html)を位置表現の参考として確認した。69点すべてを現時点の庁舎測量値として検証したものではない。

## 新規登録

`POST /api/register`（未ログイン可、JSON、正常201）:

```text
request = {username,password,name,residence_area_id:string|null,
           share_area_analytics:boolean=false}
response = {user:{id,username,name,initials,color},residence:Residence,login_required:true}
```

- username：英小文字・数字・`_`・`-`、3〜40文字。既存名の重複409。既存資格情報は書き換えない。
- password：12〜128文字。既存と同じsalt付きscrypt。SecretStrで扱い、応答へ返さない。
- name：前後空白を除き1〜80文字。改行等の制御文字は禁止。
- residence_area_id：カタログID又はnull。省略もnull。未掲載・未登録はnullで完了できる。未知IDは422。
- share_area_analytics：初期false。nullとtrueの組合せは422。本人の選択でのみtrue。
- 番地/座標/user_id/権限/未知項目はextra禁止により422。

users・preferences・residence_profilesを一つのwrite transactionで作成する。コミュニティ・講・事業者の所属は自動付与しない。登録ではcookieやtokenを発行しない。フロントは成功後、通常画面なら既存 `/api/login`、発表左右画面なら `/api/stage/login` を使う。登録とログインは別処理なので、ログインが失敗した場合は登録済みアカウントで再ログインする。

既存SecurityMiddlewareのHost/Origin/JSONサイズを適用。registerをloginと同じ20回/分の制限に含める。既存ログインsessionがある登録操作はCSRFも検査する。初回匿名登録はsessionなしのためOrigin等を境界とする。本人住所更新は通常のauthenticated/CSRF必須。

## 本人設定

`GET /api/residence/me`、`PUT /api/residence/me` は本人だけ。

```text
Residence = {area:Area|null, share_area_analytics:boolean, version:int, updated_at:string|null}
PUT = {residence_area_id:string|null, share_area_analytics:boolean, version:int}
```

未設定GETはarea=null、share=false、version=0、updated_at=null。PUTはversion照合、競合409、成功時version+1。nullで地域を削除できる（share=false必須）。他人IDを指定する住所APIは設けない。他者プロフィールには住所を追加しない。集計は現在の設定を毎回読み、同意撤回は次回GETから反映する。撤回しても利用した事実の全体件数を消すものではない。

## schema11

`residence_profiles(user_id PRIMARY KEY REFERENCES users, area_id nullable,
share_analytics CHECK 0/1 DEFAULT 0, version>=1, updated_at)` を追加する。

`area_id IS NULL`ならshare_analytics=0をDBでも強制。migrationは10→11の一つのtransaction、失敗rollback、11は再実行しても何もしない。既存ユーザーの地域/同意を自動推定しない。既存migrationの11許容とmain登録は主担当が統合する。

## 事業者の地域集計

既存 `/api/providers/{id}/analytics?days=30|90|365` の事業者staff認可を継続し、次を追加する。

```text
origins = {
  status:'available'|'insufficient_sample'|'no_data', destination:Destination,
  total_visitors, consented_visitors, missing_visitors, withheld_visitors,
  suppressed_visitors, privacy_threshold:5,
  areas:[{...Area, visitors, returning_visitors:number|null, visits:number|null,
          returning_status:'available'|'insufficient_sample'}],
  definitions:[string]
}
```

対象は**自社の確認済み利用者**。通常analyticsと同じ終了済み開催・承諾・参加申告・他参加者確認・事業者確認・取消除外の条件を使う。自己申告のみ/候補/予定/他事業者の利用は含めない。N西市だけへの実来訪を断定する集計ではない。既存開催の目的地は勝手に変更しない。

- total_visitors：当期確認済み利用のdistinct user_id。
- missing_visitors：現在の居住地域が未登録又はカタログ対象外。
- withheld_visitors：地域登録はあるが現在本人が集計を許可していない。
- consented_visitors：有効な地域登録と現在の本人許可がある人。total=missing+withheld+consented。
- visitors：市区町村ごとの当期実人数。現在の本人登録地域で集計する。訪問当時の住所や実際の出発地とは異なる。
- returning_visitors：当期の確認済み開催より前に、同じ自社の別開催で確認済み利用がある人。過去全期間を確認し、当期内の2回目も含む。同時刻の開催や同一開催の台帳追記は再訪を作らない。
- visits：当期のdistinct(開催,利用者)。人数と延べ回数を混同しない。

## 少人数の表示制限

市の来訪者が5人未満の場合、その市の**名前と位置を含めarea全体を返さない**。市の来訪者が5人以上でも、再訪者又は初回者が1〜4人なら同様に市全体を省略する。内訳だけnullにして全体件数から差し引ける構造を避けるため。suppressed_visitorsは、このため市を省略した本人許可済みの実人数。公開areaのvisitorsの合計+suppressed=consented。現版の公開areaは数値がすべて公開可能な場合だけ返すが、UI契約ではnullを0として扱わない。

これは**少人数セルの非表示**であり匿名化を保証しない。30/90/365日の重なる期間、同意や参加記録が変わる前後、事業者が別に知る参加者情報との比較による推測まで防ぐ数学的保証はない。氏名、利用者ID、個別の訪問日、住所個票を地域応答へ含めない。自由な地域/日付/利用者によるフィルターを受け付けない。強い差分プライバシーや公開用の匿名統計には追加設計が必要。

## 検証

隔離DBでresidence＋analyticsの29試験成功（20.47秒）。`artifacts/residence/pytest.xml`。その後追加した架空データ6市×6人の結合assertを限定1件で確認（2.45秒、`artifacts/residence/enrichment.xml`）。Ruff/C901/Banditは新residenceとanalyticsで0件。同じ意味の試験を繰り返した数を機能数として加算しない。

69市区の公開カタログ、scrypt・秘密非応答・セッション非発行、通常/独立stageログイン、既存資格保持、NULL登録、未知項目/番地拒否、Origin/CSRF/登録rate、登録と本人更新の同時競合、schema10→11の既存保持/失敗rollback/再実行、他社や未確認/未来/取消の除外、400日前の確認済み再訪、初回/再訪の少人数の補完抑制、同意撤回を含む。過去400日の利用は当期来訪者数には加えず、再訪判定のみに使う。

6市の許可プロフィールは利用者から追加を求められた架空コンテンツのfixture。既存u-aoi/ren/mioの住所を推測して補っていない。隔離試験では90日自社の36人が各6人の6市へ分かれ、全員が過去の確認済み利用を持つことを確認した。現実の来訪・同意実績を示す数字ではない。

独立読取レビューは [RESIDENCE-SECURITY-REVIEW.md](RESIDENCE-SECURITY-REVIEW.md)。全体回帰・Docker移行・画面操作検証は主担当の統合記録で別に確認する。
