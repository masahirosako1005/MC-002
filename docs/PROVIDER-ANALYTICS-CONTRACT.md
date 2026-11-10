# 事業者分析 API 契約

2026-11-10。現在のSQLite保存記録から作る集計。公開統計・アンケートCSVや個人の写真・内部会話を事業者実績へ混入しない。初期追加データの来歴は別の投入記録を参照する。これは予約・売上・現地訪問の外部証明ではない。

## 認可と期間

`GET /api/providers/{provider_id}/analytics?days=30`。`days` は30/90/365のみ（省略30）。未知のqueryを拒否。ログイン必須、対象の有効な事業者staffだけ。未認証401、他社/個人/停止したstaff・事業者404。不特定のSQLやグループ条件・自由な日付を受け取らない。更新・migrationは行わない。

JSTの今日を含むN暦日が当期。直前の同じN暦日が比較期。今日の値は取得時刻までなので `today_partial=true`。任意の過去時刻はquery指定不可。ISO日時のtimezoneを解釈して比較し、naive/不正日付を採用しない。予定の未来時刻を利用実績にしない。

## 応答

```text
{
  provider_id, generated_at,
  period: {days, timezone:'Asia/Tokyo', start_date, end_date,
           previous_start_date, previous_end_date, today_partial:true},
  summary: {
    consultations: Metric, confirmed_users: Metric,
    confirmed_visits: Metric, completed_outings: Metric
  },
  daily: [{date, consultations, confirmed_users, confirmed_visits, completed_outings}],
  plans: [{id, title, status:'published', consultations, confirmed_users,
           confirmed_visits, completed_outings}],
  conditions: {
    population_unit:'相談者（各人の期間内最新共有条件）',
    consultation_count, sample_count, unique_sharers,
    people: Distribution, nights: Distribution, budget_per_person: Distribution
  },
  demographics: {age: Uncollected, gender: Uncollected, interests: Uncollected},
  origins: Origins, // RESIDENCE-CONTRACT.md参照
  privacy_threshold:5, notes:[string]
}
Metric = {count, previous_count, change_count, change_percent:number|null, unit, definition}
Distribution = {label, status:'available'|'insufficient_sample'|'no_data',
                known_count, missing_count, bins:[{key,label,count:number|null}], reason:string|null}
Uncollected = {status:'not_collected',reason,known_count:0,missing_count}
```

`change_percent` は前期0ならnull、その他は前期に対する増減率（小数1位）。`daily` は期間内全日を昇順で返し0件日を含む。人・回は別指標。期間内の実人数は日別値の合算では求めない。サーバーの同一read transactionで集計する。

## 数える対象

- 相談件数：`consultations` と `plan_selections` を結び、対象事業者に共有されて開始した相談IDを1件とする。作成日時で所属期間を決める。過去の終了済み相談も件数に含む。事業者への未承諾依頼だけでは相談成立としない。依頼と相談を二重加算しない。
- 利用実人数：事業者が一致する終了済み・非取消の `daytrip_outings` に、承諾・実参加申告・他の参加者による確認・事業者確認が揃い、取消されていない参加記録がある人の distinct user_id。確認者も有効な参加申告を持つことを確認する。期間は開催の終了時刻。外部の来店検知や第三者証明とは異なる。
- 延べ利用人数：上記の `(outing_id,user_id)` を1人回とする。同じ人の別開催は別に数える。ポイント台帳の行数や予定人数を使わない。
- 実施開催数：上記確認済み利用が1件以上ある distinct outing_id。予定だけ/未確認だけの開催は含めない。
- プラン別：現在公開中の自社プランのみ。全体指標は公開終了プランの過去実績を含むため、公開中プランの和と一致しない場合がある。実人数も複数プラン利用の重複があるので合算不可。

## 共有条件と小集団

`snapshot.shared_conditions` だけを使う。現在も開いている相談・有効な選択・開いている講が対象で、事業者参加依頼がある場合はaccepted、共有代表者もログイン有効である必要がある。共有終了後の条件は集計対象から外す。内部の `travel_requirements` や `preferences` を読むことはない。

その範囲の各代表者の期間内最新相談1件を採用する（日時同値なら相談IDの降順）。`sample_count=unique_sharers` は別々の共有代表者数であり、予定人数の合計でも、参加者全員の人数でもない。`consultation_count` は当期の全相談件数。各軸 `known_count+missing_count=sample_count`。欠測はその代表者の該当条件が未入力/対象外/不正の件数。

- 人数帯：1〜2、3〜5、6〜10、11〜20、21人以上。これは共有された予定人数。
- 泊数：日帰り、1泊、2泊、3泊以上。
- 予算帯：1万円未満、1〜3万円未満、3〜5万円未満、5万円以上。**1人あたり・プラン部分**の予算だけ。グループ総額や旅全体の予算は変換・混合せず欠測扱いにし、表示名と理由に対象を明記する。実売上/実消費額ではない。

5人未満なら軸全体を抑制。5人以上でも1〜4人の非空binがあれば、その軸の**全bin**をnullとする（小さいbinだけ伏せて差引き推定できる表示を避ける）。抑制時はすべての固定binを返し、どのbinが非空かも返さない。0とnullを区別する。母数/欠測は表示する。自由なクロス集計を提供しない。これは小集団表示抑制であり差分プライバシーを保証するものではない。

年齢・性別は現行に本人同意つき収集がない。関心は現行の共有snapshotへ含まれず個人の好みを非共有と説明している。いずれも `not_collected`、known_count=0、missing_count=sample_count とする。出発地/交通/人流も推定しない。

schema11の本人登録・同意に基づく現在居住地域を `origins` として追加した。来訪/再訪と地域の少人数抑制の正本は [RESIDENCE-CONTRACT.md](RESIDENCE-CONTRACT.md)。同意した現在居住地域であり、実際の出発地や追跡された人流ではない。

## main.py 統合（主担当）

```python
from .analytics.router import create_router as analytics_router
# database 作成後、既存API routerと同じ場所へ追加
app.include_router(analytics_router(database))
```

追加先は `community/backend/app/analytics/`。テストは `test/backend/test_provider_analytics.py`。main.pyへ登録したAPIを隔離したテストapp経由で検証する。

参考：[奈良県「みるなら」](https://nara-tourism-data.pref.nara.jp/)（2026-11-10閲覧）は利用者特徴・目的・滞在期間等を情報単位として参照した。外部の人数・人流をこのサービスの実績として流用せず、外観も複製しない。

## 検証記録

2026-11-10、隔離SQLiteを使った専用15試験が成功（19.03秒）。`artifacts/analytics/pytest.xml`。未認証/個人/他社/失効したstaff、許可した期間、自由queryの拒否、JST期間境界・不正/naive/未来日時、同一人の再利用、相談・招待・台帳の重複、未確認/自己確認/取消、プラン公開終了、少数秘匿、代表者重複、予算の単位、共有失効を含む。新モジュールのRuff/C901/Bandit指摘は0（同ディレクトリのJSON）。全面的な安全性の認証を意味しない。

明示依頼された架空コンテンツパックとの結合も隔離DBで検証した。90日forestの保存値は35相談・36人・144人回・30開催、条件母数31人。人数帯21人以上の6人は**相談で共有された予定人数**の分布であり、実参加人数へ置換しない。年齢・性別・個人関心は未収集。これらの数字は架空コンテンツの整合確認で、現実の観光成果ではない。既存利用者3アカウントへの架空の実参加付与がないことも確認した。

コンテンツ投入実装を読み取りレビューし、固定ID/追加のみ・同一transactionのmanifest・再実行不増殖・既存資格情報不変・snapshot共有6項目・既存利用者への架空加点なしを確認した。投入は主担当が実行し、本APIの起動では実行しない。全体回帰・画面統合確認は主担当の記録を参照する。
