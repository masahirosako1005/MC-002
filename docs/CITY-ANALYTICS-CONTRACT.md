# N西市の統合集計 API

2026-11-10。自社専用analyticsを変更せず、市に登録された複数事業者の確認済み利用を統合する。個人ID、氏名、会話、写真、私的な旅行条件、個別の価格・取引は返さない。実装はread-only、DB migrationや実DBの更新は行わない。

## 対象と認可

`GET /api/providers/{provider_id}/city-analytics?days=30|90|365`。省略30、未知query拒否。未認証401。本人が対象の有効staffであり、事業者も有効、かつサーバーの `settings['city-provider:n-nishi:'+provider_id]='1'` による明示登録が必要。その他は404。表示名やプランの自由文、area文字列から市の所属を推測しない。

市に明示登録された有効事業者だけを集計する。主担当のcity_registry初期設定はforest-house/shore-schoolの既知2事業者で、既存の無効設定0を上書きしない。登録のない他地域事業者は名称がN西市を含んでも対象外。

開催の保存済み `route_json.id` が以下の固定IDのいずれかであることも必須。

- osaka-nnishi-reference
- suita-nnishi-reference
- kyoto-nnishi-reference
- kobe-nnishi-reference
- sakai-nnishi-reference

旧新宿→町田等の履歴は、現在の事業者areaをN西市に変えただけでは市実績にならない。将来の市内別経路は管理するallowlistへ追加する設計作業が必要。自由文destinationからの自動推定はしない。N西市は架空の目的地で、これらの経路は計画用参考値である。

## 利用と再訪の定義

終了済み・非取消、参加承諾、実参加申告、他参加者による確認、事業者確認が揃った記録を使う。取消/無効になった参加者・確認者を除き、利用者と確認者の有効アカウントも確認する。候補保存、予定、自己申告のみは利用実績ではない。内部chat/相談/写真のテーブルを読まない。

期間は既存自社APIと同じJSTの今日を含む30/90/365暦日。今日の集計は取得時刻まで、比較は直前の同日数。日時のoffsetを解釈し、不正/naive/未来日時は採用しない。

- visitors：当期に市内利用があるdistinct利用者。複数事業者の利用を重複加算しない。
- returning_visitors：当期の利用日より前の**別のJST日**にも、市内利用が確認されている人。当期内の2日目も含み、期間前の全履歴を参照する。同日他店利用は回遊であり市への再訪にしない。
- visit_days：distinct(利用者,JST利用日)。同日複数店舗を回っても1人日。
- participations：distinct(利用者,開催)。同日の別開催は別の人回。
- 事業者比較のcompleted_outings：確認済み利用者がいるdistinct開催。

現在の本人登録地域とshare_area_analyticsの許可を地域集計に使う。同意撤回・地域削除・参加取消は次回読込へ反映する。住所個票は返さない。市への再訪と従来の自社再利用は単位が異なるため、自社APIの計算方法を変更しない。

## JSON契約

```text
CityAnalyticsResponse = {
 scope:'city', city:Destination, generated_at, period:Period,
 provider_count, published_plan_count,
 plan_categories:[{id,label,plan_count}],
 summary:{visitors:Metric,returning_visitors:Metric,visit_days:Metric,participations:Metric},
 daily:{status,reason,items:[{date,visitors,returning_visitors,visit_days,participations}]},
 trend:{status,reason,interval_days,items:[{date,end_date,visitors,returning_visitors,visit_days,participations}]},
 providers:{status,reason,items:[{id,name,area,published_plan_count,
                                visitors:number|null,participations:number|null,completed_outings:number|null}]},
 origins:{status,reason,destination:Destination,total_visitors:number|null,
          consented_visitors:number|null,missing_visitors:number|null,
          withheld_visitors:number|null,suppressed_visitors:number|null,
          areas:[OriginArea],privacy_threshold:5,definitions:[string]},
 privacy_threshold:5, notes:[string]
}
Metric = {count:number|null,previous_count:number|null,change_count:number|null,
          change_percent:number|null,unit,definition,
          status:'available'|'insufficient_sample',reason:string|null}
status = 'available'|'insufficient_sample'|'no_data'
```

Destination/Period/OriginAreaの基本形は既存analytics/residence契約と同じ。dailyの各値もnumber|null。非表示を0にしない。前期又は当期が非表示なら増減値もnull。0の前期に対する率もnull。

`trend` は7日→14日→30日→期間全体の順で、安全に公開可能な区分を選ぶ。期間先頭からの連続区分で最終区分は短くなる場合がある。UIは各点のdate〜end_dateとinterval_daysを示す。非表示の日だけを除外して架空の0として折線をつながない。原則として市画面の推移はtrendを使い、dailyは検査可能な補足とする。

事業者比較は公開事業者名・area・公開プラン本数を返す。非公開プラン/個別価格/商談は返さない。plan_categoriesは公開プランtagsの本数で、利用者属性ではない。複数分野のプランは各タグで数え、合計をプラン総数として扱わない。

## 少数と差引き推定の抑制

人数の0は公開可能。1〜4人は小集団とする。

1. 市の当期実人数、再訪者、初回者のいずれかに小集団があれば、当期の全KPI/事業者実績/日別/地域内訳を抑制する。前期は独立に同じ判定をする。
2. 市内の事業者を利用した集合の原子的区分（Aのみ/Bのみ/A+B等）にも1〜4人があれば、市の期間全体を抑制する。自社値と市総計の差し引きで少数を取り出せるケースを防ぐため。
3. dailyは1日でも安全条件に合わなければ、全日の数値をnullとする。どの非ゼロ日が少人数かも出さない。trendはより広い区分で再評価する。
4. 地域/未登録/未共有/再訪内訳に小集団がある場合は**地域breakdown全体**を抑制し、areas=[]、関連母数=null。一部地域を足して少数地域を逆算する表示を避ける。公開可能な総来訪者数だけはsummaryと一致させる。
5. 公開事業者情報・公開プラン本数は個人実績ではないため、実績抑制中も表示できる。

これは少人数セルと明白な補完集計の表示制限であり、数学的な匿名化保証ではない。重なる30/90/365日の比較、更新前後、事業者が別に知る参加者情報からの推測を完全に防ぐものではない。任意期間/事業者部分集合/地域/個人を絞るqueryは提供しない。

## 実装範囲

新規 `analytics/city_*.py` と既存routerへの追加だけ。自社APIのURL・計算・JSONを変更しない。テストは `test/backend/test_city_analytics.py`。registryの作成・main統合は主担当が別途行う。

## 検証結果

隔離SQLiteの専用18試験が成功（16.81秒）。証拠：`artifacts/city-analytics/pytest.xml`。Ruff/C901/Bandit指摘0。認証・staff・明示市登録・無効化、30/90/365と未知query拒否、空集計、JSTの同日/別日境界、400日前の市内履歴、旧経路/非市事業者の除外、未確認/取消/確認者失効、事業者集合差引き、日別小セルの粗い粒度への集約、地域同意撤回/削除、住所個票非露出を確認した。

自社analytics応答の前後完全一致と、city GETによるDB全行不変も確認。架空追加データとの90日結合では市の36人・再訪36人・144人日・144人回、公開プラン15本、同意した6地域、公開可能な粒度のtrendを確認した。これは架空コンテンツの計算整合確認で、実際の地域観光効果の数字ではない。

実DBへは書き込んでいない。Dockerでの統合・画面操作は主担当が別途確認する。
