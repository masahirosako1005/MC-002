# 講コミュニティ API 契約 1

React/Python結合用。全て `/api`、同一オリジン。Cookie `ko_session` はHttpOnly/SameSite=Strict。JSON書込に `X-CSRF-Token` とOrigin必須。初回loginはOrigin必須、既存Cookieが有効なloginはCSRFも必要。画像だけmultipart/form-data。エラー `{detail:string}`、401/403/404/409/413/415/422/429/503。API・画像はno-store。CSRF失効403は `X-Session-Invalid:true`。

初期の操作用アカウントは架空の **aoi / 藤沢 葵、ren / 高橋 蓮、mio / 小野 美緒**。ローカル試作用パスワードは各々 `aoi-local-2026` / `ren-local-2026` / `mio-local-2026`（実データ運用は禁止、`KO_PASSWORD_AOI/REN/MIO`で初期作成時に上書き可能）。ログインはID書換えでなく必ずパスワードを照合する。3名とも「同期の旅じたく」、葵だけ「大学さんぽ部」に所属。同期は合成200人、追加197人はログイン不可・候補参加の初期許可false。操作3名だけ、共通の好みと許可を設定した合成初期状態。size3で実承諾を確認でき、size5は人数不足になる。合成メンバーも勝手に参加承諾させない。

## 型

```ts
type User={id:string,username:string,name:string,initials:string,color:string};
type Tag={id:string,label:string};
type Community={id:string,name:string,description:string,member_count:number,role:'owner'|'member',cover_key:string};
type Analysis={status:'queued'|'running'|'succeeded'|'failed',tags:{id:string,label:string,score:number}[],message:string,model_version:string|null};
type Media={id:string,url:string,width:number,height:number,analysis:Analysis};
type Post={id:string,community_id:string,author:User,body:string,tags:string[],media:Media[],status:'draft'|'published',created_at:string,place_label:string,taken_on:string|null,can_edit:boolean};
type Grant={community_id:string,use_for_matching:boolean,display_in_matches:boolean,participate:boolean};
type Preferences={tags:string[],learn_from_posts:boolean,grants:Grant[],evidence:{tag_id:string,post_id:string}[]};
type Trip={id:string,title:string,area:string,description:string,tags:string[],duration:'day'|'overnight',budget:number,season_label:string,cover_key:string,source_note:string};
type Participant={id:string,name:string,initials:string,color:string,common_tags:string[],response:'pending'|'accepted'|'unavailable'};
type Proposal={id:string,community_id:string,purpose:string,date:string|null,trip:Trip,participants:Participant[],my_response:'pending'|'accepted'|'declined',status:'pending'|'formed'|'invalidated',version:number,group_id:string|null,reason:string,created_at:string};
type Contribution={user_id:string,name:string,role:'none'|'research'|'schedule'|'food'|'photos',note:string};
type Group={id:string,community_id:string,purpose:string,trip:Trip,members:User[],contributions:Contribution[],plan:{date:string|null,meeting_point:string,notes:string,version:number},created_at:string};
```

## ログイン・所属

- GET `/bootstrap` 公開 → `{accounts:{username,name,initials,color}[],tags:Tag[],model:{status:'ready'|'unavailable',name:string}}`。パスワードは返さない。
- GET `/covers/{key}` 公開 → image/jpeg。keyは `woodland/coffee/coast/table` だけ。公開可能な生成カタログ素材から再エンコードした写真で、実uploadや任意pathを配信しない。cover_keyはこの4種のいずれか。
- POST `/login` `{username,password}` → `{user:User,csrf_token:string}`。新Cookie発行、切替前Cookieを失効。
- GET `/me` → `{user,csrf_token}`、未ログイン401。
- POST `/logout` `{}` → `{ok:true}`。
- GET `/communities` → `{items:Community[]}` 本人所属だけ。
- GET `/communities/{id}` → `{community:Community,invite_code:string|null}`。invite_codeはownerのみ。
- POST `/communities` `{name,description}` → Community。作成者owner。
- POST `/communities/join` `{invite_code}` → Community。
- POST `/communities/{id}/leave` `{}` → `{ok:true}`。ownerは他の所属者がいる間は409。退会で未確定提案を失効。
- GET `/communities/{id}/feed` → `{items:Post[]}`。公開投稿＋本人の下書き。所属必須。

## 写真と投稿

- POST `/media` multipart `file`（1ファイル、JPEG/PNG/WebP、12MiB/20MPまで）→ Media。再エンコード/EXIF除去済み、分析を永続ジョブへ投入。filenameを分類に使わない。
- GET `/media/{id}/analysis` → Analysis。所有者のみ。UIはqueued/runningの間に1〜2秒程度で確認する。
- POST `/media/{id}/analyze` `{}` → Analysis。所有者のみ再試行。
- GET `/media/{id}` → image/jpeg。本人または公開投稿先の現在メンバーのみ。独立した公開画像ディレクトリは作らない。
- POST `/posts` `{community_id,body,media_ids:string[],tags:string[],place_label?:string,taken_on?:string|null}` → Post。1〜5枚、まず下書き。タグはbootstrap辞書に限定。
- PATCH `/posts/{id}` `{body?:string,tags?:string[],status?:'draft'|'published',place_label?:string,taken_on?:string|null}` → Post。本人のみ。公開は画像処理済みと所属を確認。分析失敗でも手入力タグで公開可。
- DELETE `/posts/{id}` JSON `{}` → `{ok:true}`。本人のみ。配信禁止と分析取消、派生画像を削除。

画像の推論は本物のローカルモデル。モデルなし/失敗時は `failed` と日本語messageで手入力を案内し、推論成功を偽装しない。モデルの対応分類にない活動は手入力になる。候補は被写体の候補であり本人の嗜好の断定ではない。

## 好みと旅行候補

- GET `/me/preferences` → Preferences。
- PUT `/me/preferences` `{tags:string[],learn_from_posts:boolean,grants:Grant[]}` → Preferences。tagsは本人が明示確定する好み。learn_from_posts=true時は本人の公開投稿の確認済みタグも根拠付きで候補として返す。利用先group/表示/今回候補参加の許可を分ける。権限取消・変更で未確定提案を失効。
- GET `/trips` → `{items:Trip[]}` ローカル台帳。固定概算の企画素材で営業/空席/予約を確認した商品ではない。

## 仲間提案・参加・講

- POST `/communities/{id}/proposals` `{purpose:string,tags:string[],size:number,trip_id:string,date?:string|null}` → Proposal。sizeは3〜6、**作成者を含む**。同じgroupかつ3許可を満たすメンバーから共通タグ順に提案。情報不足と人数不足は409で説明。希望しない人や追加合成メンバーを自動承諾しない。
- GET `/proposals` → `{items:Proposal[]}` 本人が参加候補の提案だけ。
- GET `/proposals/{id}` → Proposal。現在所属と本人が参加候補かを確認。
- POST `/proposals/{id}/respond` `{decision:'accepted'|'declined',version:number}` → Proposal。本人の意思だけ更新。同じ応答の再送は重複作成しない。全員acceptedでgroupを一度だけ作成。辞退者を他人へ個別表示せず、未成立の提案はinvalidatedにする。
- GET `/groups` → `{items:Group[]}` 本人が参加する講だけ。
- GET `/groups/{id}` → Group。現在所属＋講の参加者だけ。
- PUT `/groups/{id}/contribution` `{role:'none'|'research'|'schedule'|'food'|'photos',note:string}` → Group。自分の任意の役割のみ。noneで参加可。
- PUT `/groups/{id}/plan` `{date:string|null,meeting_point:string,notes:string,version:number}` → Group。参加者が編集。古い版409。

投稿タグ/好み/許可/所属は本人だけが更新する。元groupの写真や所属名、辞退理由を別groupの提案へ出さない。APIに任意の所有者IDやURLを指定して切り替える入口はない。

## 結合設定

Backend `app.main:app`。環境 `APP_DB_PATH`、`MEDIA_DIR`、`MODEL_DIR`、`SEED_ASSET_DIR`、`STATIC_DIR`、`APP_ALLOWED_ORIGINS`、`APP_COOKIE_SECURE`。既存旧版とCookie名/DB/portを分離。既定dev URLはlocalhost:8001。フロントは `/api` へ相対アクセス。安全ヘッダは自己配信CSP（inlineなし、画像self/blob/data）とnosniff。モデルは開発時だけ取得し、実行時に外へ接続しない。`SEED_ASSET_DIR`には生成4写真を置き、初期投稿と固定カタログカバーとして取り込む。初期投稿のタグは合成シナリオの投稿者注釈であり、モデル結果と別に扱う。
