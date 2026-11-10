# EV02 UI 改善レビュー

更新日: 2026-11-10。対象は現行 `frontend/src`。評価前の識別は `artifacts/community/frontend-quality/ev02-before-manifest.json`。構成移動 `d1bd8f9` 後に改善し、共有ファイルの同時編集は避けた。最終currentソースの統合imageによるブラウザ測定 `ev02-ui-after-005` は全9シナリオ合格、axe 5状態で検出0、実行時エラー0、外部リクエスト0。大会の得点、利用者満足度、実際の再訪効果はこのレビューから算出しない。

## 基準とレビュー範囲

固定版 Web Interface Guidelines とローカル適用規則、Vercel React Best Practices、Emil Design Engineering の操作・状態・アクセシビリティ・アニメーション基準を使用した。標準 select を使わない製品要件を維持し、独自 Choice のラベル、キー操作、フォーカスを改善する。Next.js/SSR/クラウドや実行時の外部配信は導入しない。

優先したのは、入力の消失、選択肢のキーボード操作、異なる事業者の情報混在、アカウントの安全な管理である。全面的な意匠変更や指摘除外による点数操作は行っていない。

## Before / After / Why

| 対象 | Before | After | Why |
| --- | --- | --- | --- |
| Choice の Tab | 選択肢内で閉じるだけで、非表示になる要素がフォーカスの出発点だった | トリガーへ戻して標準の Tab / Shift+Tab に委ね、外へ移動したら閉じる | 選択肢を閉じた後もフォームを順番に操作できるようにする |
| Choice の文字入力 | 矢印と Home/End が中心 | 700ms の先頭文字検索を追加。Ctrl/Alt/Meta と IME変換中は除外 | 選択肢が増えてもキーボードで目的の値に到達しやすくする |
| 入れ子の確認画面 | Escape の cancel が React の外側 Modal にも伝わり得た | 最上位 Modal で cancel の伝播を停止 | 内側の確認だけを閉じて入力に戻り、送信中の閉じる禁止を外側から迂回させない |
| 独自選択のラベル | 親 label 内のテキストを推定する箇所があり明示的な関連付けが不足 | 日程・日数・料金等に useId による htmlFor / id を設定 | 操作名を機械的に関連付け、名前のある入力として扱う |
| 事業者プラン編集 | 編集して閉じると未保存入力を破棄した | 変更があるときだけ専用確認。継続なら保持、破棄なら閉じる。保存成功時は通常終了 | 誤操作による入力消失を抑え、すべての閉じる操作に過剰な確認を増やさない |
| 事業者プランの再読込 | 未保存でもブラウザ離脱への通知なし | dirty 状態だけ beforeunload の標準警告を要求 | 再読込で長い行程入力を失うリスクを下げる。ブラウザごとの表示条件は残る |
| 公開参考情報 | providerId が変わる時点で前の取得値が残り得た | 結果に providerId を持ち一致する情報だけ表示。古いリクエストを中断し、中断済み結果を無視 | 別事業者の評価を現在の事業者の情報として表示しない |
| 読込・保存通知 | p に role=status を追加した表現 | 単純な通知21箇所と参考情報にネイティブ output。save-bar の表示も追従 | 同じ通知の意味をHTMLで表現し、読み上げと見た目を維持する |
| 講作成時の入力 | autoFocus で特定の入力へ強制移動 | 既存 dialog の初期フォーカス制御を使用 | モバイルで不要なキーボード表示と画面の移動を避ける |
| 重複したCSS | 後の同一セレクターで全プロパティが上書きされる8ブロック | 上書き済みの先行宣言を削除 | 見た目を担う最終宣言を保ち、修正箇所の見通しをよくする |
| 事業者の補助文字色 | nav・グラフ軸・詳細tabの5要素がaxeでcontrast 4.11〜4.26、必要4.5に未達 | 対応する既存CSS3宣言を#59634fへ変更、最終Stage axeで0 | 小さな補助文字を読みやすくし、集計の意味と操作先を判別できるようにする |
| パスワード変更 | 本人がパスワードを変更する入口がなかった | アカウントから現在/新規/確認を入力。12〜128文字、確認照合、表示切替、送信中の再入防止。成功で認証破棄と再ログイン案内 | 初期・既存の資格情報を本人が更新できる。現在値の検証と同一ユーザー全session失効はサーバーが担当 |
| パスワード入力の扱い | 変更用の入力なし | current-password/new-password、貼付可、trimなし、エラー関連付けと焦点移動。値は部品内だけで保持し成功/終了で破棄 | パスワード管理ツールと支援技術を妨げず、保存領域や証拠へ秘密を残さない |
| パスワードの文字数 | JavaScript/HTMLのUTF-16単位とPythonの文字数が不一致。絵文字を含む長いパスワードが入力途中で制限された | 登録/変更/ログインをUnicode code point単位で検証。HTMLの容量は256単位とし、論理上限128字を明示検証 | 正当な既存パスワードを変更せず入力可能にし、6絵文字を12文字と誤判定しない。正規化・trimは行わない |

## 静的確認

- TypeScript: `node frontend/node_modules/typescript/bin/tsc --project frontend/tsconfig.json --noEmit --pretty false` はパスワード変更UI追加後に終了コード0。並行実装中に検出した `Omikuji.tsx` の未使用import 3件は担当へ報告し、親担当の `ev02-after` 統合測定で型エラー0を確認。
- 専用ブラウザ試験の構文: `node --check test/browser/verify-evaluation-ui.mjs` は終了コード0。これはブラウザ試験の合格を意味しない。
- CSS 中間確認: `artifacts/browser/ev02-frontend-stylelint.json` は115件（no-descending-specificity 102、no-duplicate-selectors 13、構文エラー0）。直前固定基準の126件（105/21）から11件減少。設定・除外は変更していない。最終統合値は親担当の after 測定を正とする。
- 親担当の固定基準再測定は Oxlint 115→82（中間）→81（最終current）、Stylelint 126→115、TypeScript 0。既存警告を全面解決したとは主張しない。

## 固定UIガイド17節の適用と証拠

全17節を「合格」にまとめない。以下の「部分確認」は記載の対象に限る。ソース行は再編集で移動するためファイル名と具体的な機能で追跡する。

| 節 | 適用・確認結果 | 証拠と残る確認 |
| --- | --- | --- |
| Accessibility | 対象5状態を実証 | after-004 の axe はStage・旅行者390/320/文字200%・パスワード変更で0。Stageの事業者5要素のcontrast未達を修正して再検証。全画面の読み上げは未測定 |
| Focus States | 対象操作を実証 | after-002 ChoiceのTab/Shift+Tab/Escapeと可視outline、プラン確認Escape/継続/破棄が合格。全sticky要素と全経路は未測定 |
| Forms | 対象操作を実証 | プラン保存/破棄、S02新規UI登録/ログイン/Unicode文字数/照合/誤り422/変更成功/新PW再ログインをafter-004で確認。PasswordChangeは貼付禁止なし、入力名/autocomplete/エラー焦点。登録の入力未完了時disabledは既存仕様で、ガイドの送信時検証方式と完全一致しない |
| Animation | 動きを減らす設定を部分確認 | after-002 reduced-motion時に#mainがidle、useNavigationMotion.ts/Stage.tsxに設定対応。全animationのcompositor測定や実端末での中断挙動は未測定 |
| Typography | ソースと画像を部分確認 | 和文の句読点/省略記号、wa-theme.cssのローカル書体、集計CSSのtabular-nums。Stageと200%画像で操作文の欠落なし。全文章や全数字配置の監査ではない |
| Content Handling | 部分確認 | 320pxと文字200%で横溢れなし、初期データのカードと候補の空状態をコード確認。極端に長い全ユーザー入力の視覚試験は未測定 |
| Images | 部分確認・残件あり | ui.tsx LocalPhotoにlazy/eagerとalt、失敗代替。Stageで写真を確認。共通imgのwidth/height属性はなく、全画像のCLSは今回未測定 |
| Performance | 限定レビュー | 参考情報の中断/旧結果遮断を実証、パスワード画面はlazy。全操作のINP、巨大リスト、CPU/メモリはこのUI試験では測定していない。CDN preconnectはローカル要件で非適用 |
| Navigation & State | ローカル規則を適用、対象を実証 | Choice選択とプランの未保存保護を実証。認証/個人状態をURLへ展開せず、既存本人専用再開状態を維持。全てのuseStateをURLへ同期する汎用規則は非適用 |
| Touch & Interaction | ソースを部分確認 | styles.cssのtouch-action、Modalのoverscroll、講作成autoFocus除去。実端末の粗いポインター/複合端末は未測定。新おみくじ操作は別担当評価 |
| Safe Areas & Layout | 対象サイズを実証 | Stage1440×900、旅行者390/320、文字200%で横溢れなし。320/390の「旅を計画」を実クリックして画面が開閉することもafter-004で確認。styles.css/marketplace.cssにsafe-area。実ノッチ端末は未測定 |
| Dark Mode & Theming | 明色の製品仕様を確認 | index.html theme-color、生成りのUI。ダークモード提供の要件はなく未実装。標準selectの指針は製品の独自Choice指定により非適用 |
| Locale & i18n | 日本語仕様を部分確認 | ui.tsxはIntl.DateTimeFormat(ja-JP)。Passwordの文字数をPythonと整合。多言語切替/全ての日時・数値表記は未測定 |
| Hydration Safety | SSR項目は非適用 | Viteのクライアント描画。変更したcontrolled inputにはonChangeを設定。SSRを新設して評価しない |
| Hover & Interactive States | 対象を部分確認 | styles.cssのfocus-visible、Choiceの選択状態、入力/送信disabled。ホバー全組合せと強制カラーモードは未測定 |
| Content & Copy | 対象を部分確認 | 保存/破棄/変更の具体的動詞、エラーからの再入力案内。和文に英語Title Case規則は非適用。説明理解・魅力度の人による評価は未測定 |
| Anti-patterns | ソース検索と対象操作で部分確認 | frontendにtransition: all、ズーム無効指定、変更フォームのpaste阻害なし。不要autoFocusを除去。画像寸法などの残件があるため全面解消ではない |

after-002/004 は `artifacts/browser/ev02-ui-after-002/results.json` / `artifacts/browser/ev02-ui-after-004/results.json` を指す。検出した色は nav #6e7667 / 背景#f2f4ef（4.26）、軸#75806b / 背景#fffefb（4.11）、tab#6b7861 / 背景#f2f4ef（4.22）。通常文字の4.5を満たすため既存セレクター内の色だけを変更し、after-004で検出0を確認。Stage、320px、文字200%の画像を目視確認し、表示欠落は見られなかった。

## ブラウザ確認の結果と限界

`test/browser/verify-evaluation-ui.mjs` を追加。既定は隔離環境 `127.0.0.1:8082`。8080/8081 への書込み試験は禁止し、外部リクエストを遮断・記録する。出力は `artifacts/browser/<PHASE>/results.json` と画面画像。PHASE の既存出力を上書きしない。

実施シナリオは Stage 左右独立認証とPC比率、Choice の矢印/Home/End/Escape/Tab/Shift+Tab/先頭文字と焦点、プラン変更の継続・破棄・保存、遅延した旧事業者情報の遮断、390px/320px/文字200%/reduced-motion、axe、実行時エラーと外部通信、パスワード変更の照合エラー/422/成功/旧session失効/他ユーザー維持/新PW再ログイン/ブラウザ保存領域へのPW非保存。非BMP文字を80字含む124 code pointの秘密値で新規UI登録・再ログイン・変更を完走し、6絵文字と129 ASCII字の入力は拒否した。入れ子のパスワード画面をEscapeで閉じてもアカウント画面は維持し、入口へ焦点が戻ることを確認した。

試験は架空 aoi/forest の再開状態を退避・復元し、専用下書きプランを作成して終了時にアーカイブする。パスワード試験では新規アカウントとその場で生成した値を使い、aoi/forest のパスワードは変更しない。新規アカウントは廃棄可能な隔離DB内にだけ残す。認証情報・入力値をスクリーンショットや結果へ書かない。

`ev02-ui-after-001/002` でStageコントラストを検出しCSSを修正。002の登録ラベル、003の旅行者アカウント入口は試験selectorの誤りだったためソース上の実要素へ訂正。004で全9シナリオ合格し、確認条件を除外せず完走した。出力は画面4枚と結果JSON。DBは隔離volume `kou-eval-ev02_community-data`、対象imageは `kou-community-app:ev02`。通常8081へは書き込んでいない。

root font-size 200% は文字拡大試験で、実ブラウザのズーム同等性を保証しない。日本語の先頭文字は合成キーイベントであり、実IMEの操作は別途人による確認が必要。axeで検出されない読み上げ順序、説明の理解、指操作、本人の再訪意向、全経路のWCAG適合は未確認。

### 最終統合の再確認

別担当の現地おみくじUI最終差分を含むcurrentソースとimageを一致させた後、同じ9シナリオを条件変更なしで `ev02-ui-after-005` として再実行した。全9合格、axe 5状態で0、実行時エラー0、外部通信0、fixture後始末成功。根拠は `artifacts/browser/ev02-ui-after-005/results.json` と同ディレクトリーの4画面。最終Stage画像も目視確認した。004の各節の実証は005でも再確認済みだが、新おみくじ自体の詳細操作はこの9シナリオの対象外であり、別担当の試験を参照する。再確認中にUIソースは変更していない。

## 残る技術的課題と変更所有

CSSの特異性・重複、effect内state更新、依存配列等の既存警告は残る。Choice の listbox / option、スクロール可能領域の tabindex、Stage の同一origin iframe 等は製品要件と操作上の意図があるため、警告を消すだけの削除や抑制は行わない。残件の妥当性と実害は個別に継続評価する。

UI担当の変更: `App.tsx`、`PasswordChange.tsx`（新規）、`Choice.tsx`、`Circles.tsx`、`ExperienceReference.tsx`、`Journal.tsx`、`KoPage.tsx`、`Login.tsx`、`Registration.tsx`、`Marketplace.tsx`、`Occasions.tsx`、`PlanDiscovery.tsx`、`Preferences.tsx`、`ProviderWorkspace.tsx`、`ReflectionWorkspace.tsx`、`ui.tsx`、`validation.ts`、`marketplace.css`、`provider-dashboard.css`、`styles.css`、専用ブラウザ試験と本書。

`ProviderWorkspace.tsx` は並行機能担当へ引渡し済み。引渡し時 SHA256 は `B1374AE3BDB5146891D3AC8557EF35B043878A2FAEF2FD1594C8742DFE0B22EC`。以後の追加機能差分はこのUI修正と区別し、統合後に検証する。
