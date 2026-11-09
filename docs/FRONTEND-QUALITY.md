# フロントエンドのローカル品質計測

## 最新の区切り：CP47追加後の第2巡

2026-11-09。CP45の手動写真タグとCP47の本人再開状態を追加した後、全39ファイル（TS系29＋CSS10）を再計測し、小修正だけを実施して凍結した。前節以降の初回改善値と混同しない。

| 同じCP47ソース範囲・同じ設定 | 第2巡前 | 第2巡後 |
|---|---:|---:|
| Oxlint error | 96 | 96 |
| Oxlint warning | 56 | 29 |
| Oxlint合計 | 152 | 125 |
| Promise handler のreturn指摘 | 11 | 0 |
| cleanup callback のconsistent-return指摘 | 9 | 0 |
| array index key指摘 | 11 | 4 |
| Stylelint error | 127 | 127 |
| tsc error | 0 | 0 |

根拠は `community/artifacts/frontend-quality/cp47-before-*` / `cp47-after-*`。両manifestの設定hashは一致。errorが減ったとは報告しない。OxlintとStylelintは残件により引き続き非ゼロ終了で、全適合ではない。

第2巡は Promise の副作用ハンドラとeffectの非適用時に `undefined` を明示した。行動は変えていない。確認事項・制限・曖昧さの文字列リスト7箇所は同じ文の重複を取り除き、文字列をkeyにした。編集可能な行程のkey構造は変更していない。

未選択コミュニティは、モバイルChoiceに空値の「コミュニティを選ぶ」を追加し、作成・投稿には選択が必要という読み上げ説明を紐付けた。PC側のコミュニティボタン一覧にも未選択の説明を表示。保存済みnullを自動的に所属先へ戻す処理は追加していない。

### 個別に確認した指摘と残課題

以下は一括免除の設定ではなく、次の修正判断に使う根拠。該当診断自体はJSONに残している。

| 場所・規則 | 個別の判断 |
|---|---|
| `Journal.tsx` JourneyMap / `jsx-a11y/prefer-tag-over-role` | inline SVG全体の `role=img` は地図の代替説明を与える。imgへの機械置換では内部の地図点とtitleの構造を維持できないため保留。 |
| `Choice.tsx` / `jsx-a11y/prefer-tag-over-role` | listbox/optionは利用者指定の独自選択部品。標準selectへの置換は要件に反する。矢印/Home/End/Escape/Tabの動作は維持し、親listboxにtabIndex=-1を明示済み。 |
| `marketplace-ui.tsx`, `ReflectionWorkspace.tsx` 会話履歴 / `jsx-a11y/no-noninteractive-tabindex` | 履歴だけをスクロールする構造で、キーボード利用者が履歴へ移動するためtabIndex=0を維持。単純削除は操作性を損なう。 |
| `Stage.tsx` / `react/iframe-missing-sandbox` | 同じローカルアプリの左右端末であり、信頼しない外部文書の埋込ではない。origin/source認証と独立Bearerを維持。sandbox追加の必要性は実権限と回帰を伴って別途評価。 |
| `Composer.tsx` / `eslint/no-await-in-loop` | 最大5枚のアップロードを直列化し負荷を制限する。単純なPromise.all化は今回行わない。 |
| `api.ts` / `typescript/no-unsafe-type-assertion` | generic JSON応答は型だけで保証できない。全APIのruntime schema検証が残る。既存の認証世代ガードは別途追加済みで、この型断言を安全化したとは扱わない。 |

その他の未解決125件の内訳は、native要素推奨44、effect同期更新22、Compiler依存20、Hooks依存13、label11、index key4、refs3、履歴tabIndex2、iframe2、直列await1、autofocus1、map spread1、API型断言1。CSS127件はspecificity順106＋重複selector21。すべての指摘を誤検知とは扱わず、API・セッション・画面比較を伴う次の改善対象として残す。

主担当の配信済みCP47実測では再開5検証（旧リクエスト401、CAS、本人分離等）、discovery5、occasions6、reflections6、motion5が成功と報告されている。これらは第2巡の最終小修正より前の配信結果であり、最終小修正のブラウザー検証済みとは主張しない。最終統合build/smokeは主担当へ引き渡す。

---

2026-11-09、CP43 `02ed9d9` の全 `community/frontend/src` を対象に、同じ設定で計測・安全な修正・再計測を実施。静的解析への適合を達成したという報告ではない。残る指摘を非表示にせず、コマンドは非ゼロ終了を維持する。コンテスト評価、実利用効果、セキュリティ認証の代用にはしない。

## ツール・互換性

- TypeScript **7.0.2** の既存 `strict` / `noUnusedLocals` / `noUnusedParameters` を維持。降格していない。
- 調査時の `typescript-eslint` と `@typescript-eslint/parser` **8.72.1** は npm peer と[公式対応範囲](https://typescript-eslint.io/users/dependency-versions/)の両方が `>=4.8.4 <6.1.0`。このプロジェクトで公式対応とは扱わず、導入していない。
- Oxlint **1.92.0** + oxlint-tsgolint **7.0.2006** を固定。[公式型依存解析](https://oxc.rs/docs/guide/usage/linter/type-aware.html)は TypeScript 7.0+ を対象とする。実際に型依存検査を全対象に実行し、型断言の指摘を得た。標準 tsc は独立して維持する。すべての typescript-eslint ルールを実装するわけではなく、解析ゼロでも完全性を保証しない。
- Stylelint **18.0.0** + stylelint-config-recommended **19.0.0**。Node **24.21.0** は各 engine 条件内。
- Windows Application Control が Oxlint のネイティブ binding を拒否した。OS の保護は変更せず、ローカル Docker の Node 24 Alpine に切り替えた。WASM 配布は npm 404 で利用できなかった。
- 解析コンテナはネットワーク無効、1 CPU、512 MB、ソースとツールは読み取り専用 bind。アプリの DB volume を接続しない。依存取得時だけ公開 npm へ接続し、ソースや利用者情報を送信していない。

## 固定した範囲と設定

初回は TS/TSX/宣言27ファイル＋CSS10ファイル。修正で `validation.ts` を追加し、再計測は28＋10ファイル。除外パターンなし、Oxlint `--no-ignore --type-aware --deny-warnings`。カテゴリは correctness / suspicious / perf、標準プラグインに React / JSX accessibility / import / promise を追加。実験的 React Compiler 由来の指摘も隠していない。

構成への適合設定は次の2点のみ。baseline と after の設定hashは一致する。

1. `react/react-in-jsx-scope` は `react-jsx` 自動変換方式に不適用なので無効。React namespace import を全ファイルに要求する旧方式の規則を、現行方式の不具合数に含めない。初回調査の生出力には1,928件があり、正式baselineでは除外した。
2. `import/no-unassigned-import` は `**/*.css` の副作用読み込みだけ許可。CSSを変数として読むことは実装方式に合わない。

ファイル単位の除外、全警告無効化、修正対象だけの測定、指摘数を減らすための個別抑止コメントは使用していない。

## 同条件での結果

| 計測 | 修正前 | 修正後 |
|---|---:|---:|
| tsc 型エラー | 0 | 0 |
| Oxlint error | 97 | 94 |
| Oxlint warning | 145 | 55 |
| Oxlint 合計 | 242 | 149 |
| うち unsafe-type-assertion | 84 | 1 |
| Stylelint error | 129 | 124 |
| CSS構文エラー | 0 | 0 |

`community/artifacts/frontend-quality/before-*` と `after-*` に JSON、生stderr、tsc結果、全対象・設定hashを保存。`baseline.json` は構成適合前の調査値であり、比較表には使わない。`after-first-*` は途中経過。再計測の所要時間は Oxlint 約7.2秒、CSS約1.5秒、tsc約1.2秒で、性能ベンチマークではない。

## 修正内容

- catch値を Error と決めつける処理を `errorMessage(unknown)` に置換。文字列やnull等がthrowされても例外表示自体が失敗しない。
- 選択肢の値を enum と断言せず、許可された値を確認。無効値なら現在値を維持する。
- DOMのtarget・フォーカス復元を `instanceof` で確認。Choiceの選択肢にフォーカス可能性を明示し、選択indexだけを依存値にして不要な再フォーカスを防ぐ。
- Stageの受信データをunknownとして検査。既存origin / source検証と成功イベント限定を維持。
- motion cancel / Stageの終了処理を安定callbackにし、イベント依存関係を明示。
- LocalPhotoをsrc単位で再mountし、旧画像状態を持ち越さない。中止処理とblob URL解放を維持。
- 配列の初期値を安定化。訪問地点の選択肢を型付き配列で構成。
- buttonと講見出しの重複CSSを小範囲で統合し、読み上げ専用要素の旧clipをclip-pathへ変更。

独立レビューでは Choice の再フォーカス、Stage のイベント検証、motion のref依存、Modal のフォーカス復元、写真のabort/blob解放に重大指摘なし。実ブラウザー回帰とDocker配信は主担当の統合検証へ渡す。

## 未解決・適用上の判断

- Oxlint残149件。native要素を勧める43件には現在妥当な `role=status` / SVG `role=img` / キーボード対応カスタムChoiceを含む。全件を誤検知とは扱わず、DOM/読み上げを変える修正は個別検証が必要。
- React effectの同期更新22件、Compiler依存19件、Hooks依存12件、refs3件は残存。再取得・利用者切替での状態消去が含まれ、単なる依存配列追加は再fetchループを招き得る。セッション境界と再取得回帰を伴う別整理が必要。
- ラベル11件にはChoiceを内包するlabelや深い子要素の文字が含まれる。既存axe0という実測は静的指摘の一括免除には使わない。
- index key11、Promise返却10、return形式10、iframe sandbox2、会話履歴のtabIndex2、autofocus1、直列await1、map内spread1も残存。写真の直列uploadは同時負荷を抑える意図があり、並列化だけで数を減らさない。stageのsame-origin iframeをsandbox化する場合は独立認証とpostMessageの回帰が必要。
- API generic応答の型断言1件は残存。型指定だけではサーバー応答のruntime validationにならない。全APIのschema検証は今回の小修正の範囲外。
- CSS残124件＝specificity順103＋重複selector21。段階追加した既存上書きが含まれ、大規模並替えは見た目の変更を招く。実画面比較を伴って整理する。ツールを黙らせるために無効化しない。

## 再実行

`community/frontend` で `npm run typecheck`、対応環境で `npm run lint`、`npm run lint:css`。このWindows環境ではネイティブ制約により `npm run quality:measure -- current` を使う。

Docker計測に使う依存は、プロジェクト内 `community/artifacts/frontend-quality/tool-runtime` に公式パッケージ `oxlint@1.92.0` と `oxlint-tsgolint@7.0.2006` をLinuxコンテナから `npm install --prefix /tools --save-exact --ignore-scripts --no-audit --no-fund` で準備する。runtimeキャッシュはGit対象外。スクリプト内のNodeイメージdigestを固定し、実解析時はネットワークを切る。
