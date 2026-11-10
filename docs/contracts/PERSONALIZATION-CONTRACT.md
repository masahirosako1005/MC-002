# CP47 本人専用の再開状態 API 契約

2026-11-09にschema 8で導入。2026-11-10に現行コードとの契約差分を確認した。現行アプリはschema 12で、`daytrip`の再開と未保存旅行者の初期画面に対応する。本書の履歴・導入番号を現行DB版や全体受入完了の宣言に読み替えない。

## 保存とレスポンス

`GET /api/me/resume-state`、`PUT /api/me/resume-state`。既存認証を使用、PUTは既存Origin/CSRF必須。user_id指定不可、公開/他者profileへの出力なし。1ユーザー1行をSQLiteの `user_resume_state` に保存する。関心/許可は既存 `/me/preferences` を使用し、再開状態へ複製しない。

GET/PUT成功のJSON（PUTも同じ全フィールドを入力）:

```json
{"version":0,"page":"market","community_id":null,"circle_id":null,"filters":{"query":"","category":"","duration":"all","schedule":"all","area":""}}
```

- `version`: 非負整数、PUT必須。未保存0、保存成功で+1。同内容・同版のPUTは既存保存版を維持し、古い版は409。競合はGETで最新を取得し、古い別タブ状態を自動上書きしない。
- `page`: `feed|market|circles|journal|provider|daytrip`。frontendの `ko` は `circles` と対応。preferences等の一時画面は直前の対象画面を保持。
- `community_id`: null または現在active所属のID。
- `circle_id`: null または現在参加済み/open/同communityの講ID。招待pendingは不可。legacy講の元group所属も必要。
- `filters.query`: 0〜120文字、前後空白除去。本人専用。
- `filters.category`: 空文字か現TAGSキー。
- `filters.duration`: `all|day|overnight`。
- `filters.schedule`: `all|dated|on_request`。
- `filters.area`: 空文字か現在active事業者の公開・期限内プランにあるエリア、最大100文字。非公開/他人の下書きからエリアの存在を推測させない。
- 未知キー、bool版、未知enum/タグ、長すぎる値は422。参照不正（所属外/未承諾/別community/閉じた講/未許可provider画面）は共通404。存在しない公開エリアは内容を含めない共通422。

未保存GETは書込せず、provider権限があればpage=provider、それ以外はdaytrip、他は初期値を返す。保存済み状態の失効時にmarketへ戻す既存処理とは区別する。既存の選択講なし検索も有効なのでcircle_id=nullを許容する。community_id=nullのときcircle_idは指定できない。

## 現権限・失効・復元

- コミュニティ所属失効/削除: community/circle/filtersを消し、pageをmarketへ、version更新。
- 講メンバー削除/元groupメンバー削除/講close・削除: circleとfiltersを消し、circles画面ならmarketへ、version更新。
- provider職員権限/事業者active失効: provider画面をmarketへ戻しversion更新（別の有効provider権限が残る場合は維持）。
- アカウント無効化: 再開参照/filtersを初期化しversion更新。
- 上記はDB triggerで失効時に反映し、GET前に退出→再加入しても復活しない。GET/PUTでも現権限を再検査し、残存する無効状態・公開終了エリアは正規化して保存する。正規化でversionが変わった場合、古いPUTは409。本人の関心・講本体・会話・写真は削除しない。
- 単なる候補0件ではfiltersを消さない。元エリアが公開カタログ自体からなくなった時だけareaを空にする。
- ページ読み込み後、本人とデータ取得完了を待って復元。ログアウト/アカウント切替でdebounceと保留結果を破棄。左右の別認証を維持し、同一ユーザーだけが同じ本人状態を共有する。

## 移行

schema 7→8の追加1表と失効triggerのみ。再適用可能、失敗はrollback。旧表の行・初期関心/許可・mediaファイルを変更しない。親担当が既存migrationの8受入、mainへのmigrate/router接続を行う。

## 最小受入

本人/別人分離、明示した異なる関心による順位差、許可OFF、私的情報の公開不在、保存後のDB再接続、新app lifecycle、CAS競合、失効→再参加の非復活、pending拒否、非公開area拒否、nonempty移行/rollback、画面の再読/切替を確認する。DB/ブラウザー実検証結果は別の証拠を参照する。
