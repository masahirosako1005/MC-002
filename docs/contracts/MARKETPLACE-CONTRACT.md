# 旅行者・事業者・ローカル支援ハブの実装契約

2026-11-10の現行差分：通常実行はモデル推論なしのMOCであり、画像は既知素材の事前候補と本人の手入力を使う。[画像処理契約](IMAGE-PROCESSING-CONTRACT.md)と[MOC境界](AI-MOC-CONTRACT.md)を優先する。以下の0.2導入時点の試験件数、モデル実測、移行・結合待ち記述は履歴として保持し、現行の配信状態や全体受入へ流用しない。現行Stageは左旅行者スマホ・右事業者PCで独立認証。本人PW変更は[基本API契約](API-CONTRACT.md)を参照。

2026-11-09 / 実装契約 0.2。代表者決定・1 計画 1 active 選択・予算単位と範囲・既存講の明示メンバー/代表者単独を採用。以下の wire 契約でバックエンド実装済み、UI/Docker 結合は別途検証。稼働コンテナは親担当の統合まで更新しない。

## 結合用の確定 wire 型

全 POST/PATCH は extra 項目を拒否。PATCH plan は全編集項目＋現在 version を送る（部分差分ではない）。GET は一覧のみ `{items:...[]}`。以下は既存の `User` 等から独立した追加型。

```ts
type Provider = {id:string,name:string,area:string,description?:string};
type Requirements = {planned_people:number,nights:number,budget_yen:number|null,budget_basis:'per_person'|'party_total'|null,budget_scope:'plan_only'|'whole_trip'|null,date_start:string|null,interests:string[],departure_label:string,version:number};
type Party = {id:string,community_id:string,title:string,representative_id:string,can_manage:boolean,active_account_count:number,status:'open'|'closed',requirements:Requirements|null,consultation_id:string|null};
type Place = {day:number,period:'morning'|'afternoon'|'evening',place:string,description:string,travel_minutes:number|null};
type ProviderPlan = {id:string,provider:Provider,title:string,summary:string,area:string,min_people:number,max_people:number,nights:number,price_yen:number,price_basis:'per_person'|'party_total',price_scope:'plan_only'|'whole_trip',price_note:string,tags:string[],itinerary:Place[],status:'draft'|'published'|'archived',version:number,source_note:string};
type Message = {id:string,author_name:string,body:string,created_at:string};
type Match = {eligible:boolean,match_status:'excluded'|'needs_confirmation',reasons:string[],excluded_reasons:string[],unknowns:string[],common_tags:string[],estimated_total_yen:number};
type Recommendation = {id:string,requirements_version:number,method:'deterministic-constraints-v1',items:(Match & {plan:ProviderPlan})[]};
type Preview = {plan:ProviderPlan,shared_conditions:Pick<Requirements,'planned_people'|'nights'|'budget_yen'|'budget_basis'|'budget_scope'|'date_start'>,match:Match,notice:string};
type Consultation = {id:string,status:'open'|'closed',version:number,selection:{plan:ProviderPlan,shared_conditions:Preview['shared_conditions'],share_note:string,requirements_version:number,unknowns:string[]},can_close:boolean,created_at:string};
```

- capabilities → `{providers:Provider[],traveler:true,hub:{image_model,condition_method,recommendation_method}}`。
- party 作成 → `{title,ko_group_id?:string|null,member_ids?:string[]}`、返却 Party。既定は本人1名。member_ids は既存講の明示選択のみ。
- requirements PUT → Requirements（初回 version=0）、返却 **Party**。
- messages POST → `{body,client_request_id}`、返却 Message。GET は `{items:Message[]}`。ID はランダム英数字/ハイフン可。
- condition-drafts POST `{message_ids:string[]}` → `{id,method:'numeric-rules-v1',candidates:{message_id,candidates:{planned_people?:number[],nights?:number[],budget_yen?:number[]},needs_confirmation:true}[],warning,status:'needs_confirmation'}`。値を直接条件へ上書きしない。
- recommendations POST → **`{version:現在requirements.version}`**、返却 Recommendation。不適合も eligible=false と理由付き。既定の選択可能表示は eligible=true のみ。
- selection-preview POST → `{plan_id,plan_version,requirements_version}`、返却 Preview。
- selections POST → 同3項目＋`{share_note:string,sharing_confirmed:true,client_request_id:string}`、返却 Consultation。明示共有確認を必須とする。
- close POST → `{version:consultation.version}`、返却 Consultation。
- 計画全体の POST `/travel-parties/{id}/close` `{}` → Party。代表者だけ。関連する open 相談と active 選択も閉じ、以後の条件更新/選択/内部投稿を停止する。未終了の代表計画があるコミュニティからの退出は409、計画閉鎖後は既存の退出条件を適用する。
- provider-plans GET query `provider_id?:string,mine?:boolean`。mine=true は自社スタッフのみ、下書きも返す。plan POST/PATCH は ProviderPlan から id/provider/source_note を除く全項目、初回 version=0。
- 公開候補を価格や人数で絞る UI は Recommendation の判定を用いる。現一覧 API は provider_id/mine のみ対応し100件上限。

追加合成ログイン：`forest`（森の旅案内、provider_id=`forest-house`）、`shore`（海辺の学び舎、provider_id=`shore-school`）。初期試作用パスワードは `<username>-local-2026`、初回環境 `KO_PASSWORD_FOREST/SHORE` で置換可。事業者は旅行コミュニティへ自動加入しない。bootstrap の accounts に追加する。

公開初期プラン：`forest-six`（4〜8人/2泊/1人28000円/plan_only）、`shore-school`（30〜60人/2泊/1人24000円/plan_only）、`forest-day`（1〜12人/0泊/1人6000円/plan_only）。全て架空の行程、交通費・営業・空席は未確認。6人/1人30000円/2泊なら forest-six、35人/1人30000円/2泊なら shore-school が人数・泊数・概算条件に合う。実人数は代表者1人のまま。

## Stageの左右独立セッション

POST `/api/stage/login` `{username,password}` → `{user,csrf_token,access_token,expires_at}`。通常と同じパスワード検証を行い、30 分の乱数 opaque token を返す。DB `stage_sessions` には hash のみ。通常 Cookie は作成・変更・削除しない。

現行の再認証では、有効な既存Bearerが指定されている場合にCSRFを確認し、その呼出し元tokenだけを新tokenへ置き換えて旧tokenを失効させる。他方の画面や別ユーザーの認証は変更しない。PW変更成功時の本人全セッション失効とは別の処理である。

各 iframe は token と csrf をその API モジュールのメモリだけに保持し、API fetch を `credentials:'omit'`、`Authorization: Bearer ...` 付きで呼ぶ。書込みは CSRF と Origin も必須。URL、ブラウザー保存領域、ログ、中央パネルへのメッセージに token/password を入れない。誤った/期限切れ Authorization があれば Cookie へ戻らず401。stage token を Cookie として渡しても認証しない。通常 `/me` `/logout` はどちらの認証にも対応し、Bearer logout では通常 Cookie を変更しない。

private 画像は Authorization 付き fetch で取得して blob URL として表示し、終了時に破棄する。公開 covers だけは通常 URL でよい。同じ origin の iframe は相互に信頼された自アプリであり、悪意ある同一 origin script に対する隔離境界とは主張しない。CSP と自己配信を維持する。

HTML の `/stage/visitor` と `/stage/provider` の2パスだけ `frame-ancestors 'self'` / `X-Frame-Options:SAMEORIGIN`。他の画面/API は従来の `frame-ancestors 'none'` / DENY。中央パネルは実 API 操作の成功・待機を反映し、推論未実行を成功と表示しない。

実装モジュールは `backend/app/marketplace/`、追加 HTTP 試験は `backend/tests/test_marketplace.py` と `test_stage.py`。既存仕様は API-CONTRACT.md。既存を含む通常 API は 26 passed / 実モデル1件 deselected（18.74秒）。その後追加した移行失敗・計画閉鎖・埋込制限を含む marketplace/stage 対象13件は 13 passed（7.75秒）。Linux モデル・Docker・ブラウザーは別途検証。

## 目的と役割

旅行者は家族、サークル、部活動、修学旅行等の旅を講で相談する。ローカル支援ハブは確認された人数・泊数・予算・関心から、旅行先、行程、店や場所を含む候補を示す。旅行者は候補または事業者一覧からプランを選び、その事業者への共有内容を確認して初めてアプリ内相談を開く。事業者は自分のおすすめプランを作成・公開し、選ばれた案件だけ相談できる。

三役は機能上の役割である。ハブは人間のアカウントや意思決定主体ではなく、ローカルで動く処理。利用者が承諾したように発言・選択・予約しない。事業者権限はローカル管理済み所属から判定し、リクエストの role や user_id で取得できない。1 アカウントが複数役割を持っても、画面切替だけで権限を増やさない。

## 既存の講と人数の区別

既存 `ko_groups` と 3〜6 人の相互承諾は維持する。新しい `travel_parties` を旅行計画の器とする。成立済み講から作成する方法と、家族等の代表者が所属コミュニティ内で作成する方法を用意する。後者は代表者 1 アカウントで計画を開始できるが、全員がアプリ参加・承諾した講とは表示しない。

- `planned_people`：代表者が入力する旅行の予定人数。例：6 人、35 人。
- `active_account_count`：現在この計画へ参加している実ログイン可能アカウント数。予定人数から生成しない。
- `planning_role`：代表者または計画メンバー。代表者が候補選択・外部共有を決定する方式をこの版の明示ルールとする。「全員合意」とは表現しない。
- 既存講由来でも作成時のメンバーが退出したら、以後の権限を再判定する。代表者の退出は後任指定まで拒否、または計画を閉じる。コミュニティ所属だけでは全計画を閲覧できない。

## 旅行条件と会話の流れ

1. 代表者が計画を作成。現在メンバーだけの会話を投稿する。
2. 利用者の操作で会話から条件候補を整理する。候補は未確認であり、確定条件を上書きしない。
3. 代表者が人数、泊数、予算、関心等を訂正・確定する。
4. 条件照合または事業者一覧でプランを比較し、行程・価格の範囲・不足情報を確認する。
5. 代表者がプランを選び、事業者へ渡す内容を確認する。
6. 選択・共有スナップショット・相談室を同一トランザクションで作成する。選択前は事業者の相談一覧に現れない。
7. 双方が相談室に投稿する。予約・契約・支払い・外部連絡は発生しない。

確定した条件型：

```ts
type Requirements = {
  planned_people: number; // 1..500、実参加数とは別
  nights: number; // 0..30。2泊は3日の行程
  budget_yen: number | null; // 正の整数、上限100000000
  budget_basis: 'per_person' | 'party_total' | null;
  budget_scope: 'plan_only' | 'whole_trip' | null;
  date_start: string | null;
  interests: string[]; // 既存固定タグ、本人/計画メンバーが共有を許可したもの
  departure_label: string;
  version: number;
};
```

予算が「全体」か「1 人」か不明なら確認待ち。交通費等の含有範囲が異なる価格を合算して適合とは判定しない。旅行日、出発地、予算が欠けても一覧閲覧はできるが、該当条件は未確認と表示する。未入力を 0 円や条件適合に置換しない。旅行者の家族属性・健康状態を写真や会話から補完しない。

## AI 支援として説明する範囲（0.2導入時点の履歴と現行差分）

- **過去の実モデル推論記録**：導入当時はローカル MobileNetV2 による写真の被写体タグ候補を検証した。利用者の訂正と利用許可を経た情報だけ使い、分類精度・趣味適合・施設の特定を保証しない設計だった。現行はこのモデルをロード・推論せず、当時の測定を現在の認識性能として扱わない。
- **実装済みの決定的処理**：会話中の「6 人」「2 泊 3 日」「1 人 3 万円」等を規則で抽出する。値・出典メッセージ・曖昧な箇所を返す。否定、引用、複数案、人数変更の解釈が不確実なら候補を並べ、本人の確認を求める。一般的な会話理解モデルを実装したとは称しない。
- **実装済みの条件照合**：公開プランの人数範囲、泊数、概算費用の範囲、タグを照合。適合理由、不適合理由、未確認項目と計算版を保存する。価格の金銭計算は整数円。人数・泊数等の必須条件を満たさないプランを高い関心点で救済しない。
- **行程**：事業者が登録した日別の店・場所候補を使う。存在しない店を自動生成しない。移動時間や営業情報が未登録なら未確認と示す。ローカルカタログにない施設検索、空席照会はしない。
- 事業者一覧からの選択も同じ確認・共有処理を通す。条件不一致は理由を示し、条件を訂正するか別プランを選ぶ。外部 LLM、外部 API、DB、メール、SNS 送信は使わない。

## 追加データと不変条件

既存表を破壊しない schema 1→2 の追加移行を実装した。新表と事業者 seed は一回の BEGIN IMMEDIATE 内で作成する。既存初期化は schema 2 を 1 に戻さない。未知 schema は起動拒否する。単体試験で移行失敗時のロールバック、再初期化、SQLite バックアップ復元を確認。稼働 DB+media の保全と隔離復元は環境担当の証拠で別途確認する。

| 表 | 最小データと制約 |
| --- | --- |
| `stage_sessions` | token_hash、user_id、csrf_token、expires_at。通常 Cookie セッションとは別表、30分有効 |
| `providers` | id、名称、説明、地域、active。架空の事業者台帳 |
| `provider_staff` | provider_id/user_id 複合一意、active。通常 API から権限昇格不可 |
| `provider_plans` | provider_id、title、summary、draft/published/archived、version、人数 min/max、泊数、概算の単価/全体価格と含有範囲、タグ、日別行程 JSON。価格条件の整合を検証 |
| `travel_parties` | community_id、任意の ko_group_id、代表者、title、open/closed、created_at |
| `travel_party_members` | party_id/user_id 一意。現在所属は memberships と照合、代表者は travel_parties に保存。ログイン可能なアカウントのみ |
| `travel_requirements` | party_id 一意、上記条件、version、confirmed_by、confirmed_at |
| `party_messages` | party_id、author_id、本文、created_at。内部会話専用。発言削除は未実装 |
| `condition_drafts` | party_id、候補 JSON、created_at。候補内に参照 message_id・規則版・確認待ち状態を保存。requester と作成時条件 version の独立列は設けていない。候補は確定条件を自動更新しない |
| `recommendation_runs` | party_id、結果 JSON、created_at。JSON 内に条件 version、各 plan version、方法版、候補と理由のスナップショットを保存 |
| `plan_selections` | party_id、plan_id、provider_id、snapshot JSON、selected_by、active/closed、created_at。各 version は snapshot に保存。既存行を別プランへ上書きしない |
| `consultations` | selection_id UNIQUE、open/closed、version。provider_id は selection と結合。選択と原子的に作成 |
| `consultation_messages` | consultation_id、author_id、本文、created_at。内部会話とは別表。発言削除は未実装 |
| `operation_keys` | actor_id/operation/key 一意、payload hash、結果 ID。選択・メッセージ再送の重複を防止 |

同一計画の active 選択は一意インデックスで 1 件に制限する。別プランを選び直すと旧相談を closed とし、新たな共有確認を要求する。複数の事業者へ同時に相見積もりする機能はこの版に暗黙追加しない。プランの編集は version を増やす。既存選択の行程・条件・概算は選択時スナップショットのまま保持する。

## 実装した追加 API

既存 `/api`、Cookie、CSRF、Origin、Host、サイズ制限、CSP、no-store を継承。全て認証必須。下表のパスは `/api` を省略。レスポンスは必要情報の DTO とし、生の DB 行を返さない。本文はプレーンテキスト、任意 HTML / URL fetch は許可しない。

| API | 入力 / 返却 / 権限 |
| --- | --- |
| GET `/marketplace/capabilities` | 自分の provider 所属と操作可能範囲。自称 role は受け取らない |
| GET `/providers` / `/providers/{id}` | active 事業者の公開情報。非公開連絡先なし |
| GET `/provider-plans` | provider_id で絞り込み、mine は自社 staff のみ。100件上限。人数/泊数は推薦 API で判定、cursor/limit 指定は未実装 |
| GET `/provider-plans/{id}` | 公開プラン詳細。自社 staff は自社下書きも可 |
| POST `/providers/{id}/plans` | 自社 staff のみ作成。UI は draft 保存から開始。API は検証済み published 作成も許可 |
| PATCH `/provider-plans/{id}` | 自社 staff、version 必須。整合する行程・価格を確認して公開可 |
| POST `/communities/{id}/travel-parties` | 現在所属者が代表者として作成。任意 ko_group_id は自分が現在参加する講のみ |
| GET `/travel-parties` / `/{id}` | 自分が現在計画メンバーのものだけ。予定人数と実参加数を分離返却 |
| GET/POST `/travel-parties/{id}/messages` | 計画メンバーのみ。投稿 body 2000 文字、client_request_id 必須 |
| POST `/travel-parties/{id}/condition-drafts` | 明示指定した自計画の message_ids（最大50）から候補抽出。規則版と不足事項を返す |
| PUT `/travel-parties/{id}/requirements` | 代表者が確定。version 必須。未確認 draft は自動反映しない |
| POST `/travel-parties/{id}/recommendations` | 確定条件 version 必須。マッチ候補、根拠、不足事項。private preference の生データを返さない |
| POST `/travel-parties/{id}/selection-preview` | plan_id、plan_version、requirements_version。共有する内容をそのまま返す。事業者への可視化なし |
| POST `/travel-parties/{id}/selections` | 同じ3指定＋share_note＋sharing_confirmed=true＋client_request_id。代表者のみ。入力と version を再検証して選択/相談を原子的作成 |
| GET `/consultations` / `/{id}` | 当該計画の現在メンバー、または当該事業者の現在 staff のみ |
| GET/POST `/consultations/{id}/messages` | 同じ認可。open のみ送信、client_request_id 必須。過去の内部会話は一切含めない |
| POST `/consultations/{id}/close` | 計画代表者または当該事業者 staff。version 必須、閉鎖後は送信不可 |

初版の計画作成時メンバー追加は既存講の現在メンバーからの明示選択に限る。代表者だけの家族計画も可能。追加されたことは参加承諾や旅行契約と扱わない。独立した招待・加入・退出 API が必要なら実装前にこの契約へ追加する。既存コミュニティ退出でアクセスは失効する。

404 は対象不明と権限なしを共通化。競合・古い条件/プランは 409。不整合入力は日本語 detail を持つ 422、曖昧な会話は needs_confirmation の候補として返す。推薦不一致は eligible=false と理由配列で返す。同じ idempotency key と異なる本文は 409、同一本文は同じ結果。失敗時は選択だけ・相談だけが残らない。

## 共有と取り消しの境界

事業者が受け取れるのは、選ばれたプランのスナップショット、予定人数・泊数・確認済み予算/希望日、代表者が確認した相談文と相談室内の発言だけ。プレビューはサーバーの allowlist で組み立て、クライアントから既存写真 ID、内部会話 ID、会員全員の好みを埋め込めない。

写真・顔・氏名一覧・個別の趣味・元コミュニティ名・内部会話・断った人や理由を自動共有しない。相談室では投稿者の表示名は共有されると事前表示する。自由文の入力者が書いた内容は相手に届くため、共有前プレビューを必須とする。AI が自由文を安全と保証するとは説明しない。

他社 staff、選択されていない事業者、計画外の同じコミュニティ会員は相談を閲覧できない。プラン検索や推薦 run も事業者へ行動履歴として渡さない。画像 URL の権限を相談開始に合わせて拡大しない。

閉鎖は新規送信を止めるが、現在権限を持つ双方は相談履歴を閲覧できる。所属退出・事業者/スタッフ無効化は該当権限による閲覧/送信を制限する。他の正当な旅行者権限がある場合はその範囲だけを認める。ただし、相手が既に見た内容を見なかったことにはできない。バックアップには選択・相談も含まれる。保持期限、削除・復元時の再削除手順は実データ運用前に確定する。プロトタイプは合成利用者・架空商品だけとする。

## 実装工程と検証状態

1. 完了：代表者権限、1 計画 1 選択、価格範囲、計画メンバー方式を親担当が採用。既存試験証拠を保存。
2. 完了：marketplace schema/service/router と接続を追加。schema 1→2 の移行・再実行・ロールバック、既存 API 回帰を検証。
3. 完了：架空事業者2社の実ログインと3プランを用意。6人2泊3日/30人以上の条件照合を確認。自動承諾・予約なし。
4. API 実装・試験完了：プラン作成/公開、代表者計画、内部会話、確認付き条件抽出、決定的候補照合。不明条件を適合と偽装しない。
5. API 実装・試験完了：両入口で共通の共有確認→選択→アプリ内相談を提供。UI の最新通し検証は親担当の結果を参照。
6. API 権限・整合性試験完了。親担当から初回実ブラウザー4段階成功の報告あり。最新 UI、schema2 の稼働復元、左右セッションのブラウザー専用試験は担当別に継続検証し、未確認を完了扱いしない。

必須試験：予定35人/実アカウント1人の区別、6人2泊の上限下限、全体/1人予算と除外交通費、未確認日程、複数数字/否定/訂正の確認停止、選択前相談なし、別社と別計画のID差替え拒否、CSRF/Origin/退出・staff解除、内部会話/元写真/個別嗜好の不漏洩、選択二重再送、古い版拒否、DB失敗時選択と相談の同時ロールバック、プラン編集後の既存選択保持、DBとメディア復元、既存3人承諾/投稿試験の維持。

## 現在版の証拠

`artifacts/backend-verification.json` は既存 API の 16 成功・1 Windows skip と、その後の希望日返却の対象試験 1 成功を記録する。`artifacts/model-verification.json` は Linux Docker の実画素推論を記録する。この結果を本追加機能の成功証拠には流用しない。

### 最終 API 検証追記

通常 API 全体は 30 passed / 実モデル 1 件 deselected（23.84 秒）。追加の同時作成/退出試験 1 件も passed（1.37 秒）。無効事業者と旅行者の兼任時の権限確認、代表者退出と計画作成の原子的判定を独立レビューにより修正した。記録は `artifacts/marketplace-backend-verification.json`。Linux 実モデルの試験は Windows の除外を成功と扱わず別途実施する。

### 左右セッションの実ブラウザー試験準備

`qa/verify-stage-security.mjs` を作成し、`node --check` による構文確認のみ実施。実ブラウザー実行は親担当のスケジュール待ち。予定出力は `artifacts/stage-security-browser.json` であり、未実行時点では成功証拠ではない。試験コードはトークンをメモリ内だけに保持し、結果に保存しない。自然な30分の期限経過はブラウザーで待たず、期限切れの API 試験とブラウザーでの明示失効試験を区別する。
