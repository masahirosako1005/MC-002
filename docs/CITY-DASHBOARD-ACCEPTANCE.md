# N西市全体ダッシュボードの実装・確認記録

2026-11-10 / CP78〜86の統合確認。自社の業務集計を残し、市全体集計・数か月分の記録・通う旅・クーポンを接続した。API、保存、静的解析、主担当による実画面の受入を以下に分けて記録する。狭幅の最終受入でCP79を完了とし、文字200%が未確認のCP83はreviewを維持する。今回の追加と過去の試験数を混ぜない。

## 登録と集計範囲

市の所属は表示用の住所文字列から推測せず、settings の `city-provider:n-nishi:<provider_id>` が `1` の有効な事業者で決める。初期の森の旅案内・海辺の学び舎の2事業者を起動時に一度登録する。既に `0` の設定を上書きしない。照会にはログインと参照元事業者の有効なスタッフ権限、市への登録が必要。

その後、明示的に投入した追加データで4事業者を加え、実配信の読取時点では6事業者を集計する。N西市と運用履歴は架空のシナリオであり、実在地域の観光成果ではない。由来と再適用条件は [OPERATIONAL-DATA-PACK.md](OPERATIONAL-DATA-PACK.md) に記録する。

市の来訪実人数は事業者間で同じ人を重複計上しない。同じ日に複数の店を利用した場合は回遊として扱い、市への別日の再訪とは分ける。期間外の過去利用も再訪の判定に用いる。元データはアプリ上の確認済み開催であり、全市民・全観光客の統計ではない。

個人識別子、氏名、他社の相談・内部会話、写真、個別の希望条件は市APIへ含めない。地域は本人が共有を許可した現在の登録市区町村。少人数の表示制御は匿名性の数学的な保証ではない。

## 画面の変更

| Before | After | Why |
|---|---|---|
| 自社の実績だけ | 自社 / N西市全体の明確な切替 | 市場全体と自社を混同せず確認する |
| 高いヘッダーと大きなカードが最初の画面を占有 | コンパクトな業務ナビと主要数値、その下の推移・地域図 | PC画面で傾向を早く把握する |
| パネルを縦に並べる構成 | 広幅では比較しやすい複数列、狭幅では一列 | 画面幅に合わせて読字を保つ |
| 利用者向け装飾が業務操作にも残る | 落ち着いた墨色・緑と細い罫線の業務画面 | 利用者の和の画面と、事業者の実務を両立する |
| 日帰り候補とクーポンの場所が分かれている | 具体的な体験カードから、その経路のクーポンへ移動 | 事業者・場所・階級・期間・費用を同じ候補の判断に使う |
| 単発の開催だけを管理 | 通う旅に目的・全回料金・工程・開催との紐付け・利用確認の進捗 | 登録や予約希望と、各回の確認済み利用を区別する |
| フィードは最大100件で途切れる | 初期24件と「続きを読み込む」、切替時は旧要求を破棄 | 古い写真へ到達でき、別コミュニティの結果を混ぜない |

## 検証記録

| 範囲 | 確認済みの事実 | 証拠 |
|---|---|---|
| 市所属 | 1試験成功。繰り返し、無効設定の保持、名称・地域の不変 | [registry-tests.xml](../artifacts/city/registry-tests.xml) |
| 市集計 | 専用18試験成功。認可、同日別店と別日再訪、JST境界、取消、同意撤回、少人数・補完集団の非表示、0件、読取によるDB不変 | [verification.json](../artifacts/city-analytics/verification.json)、[独立レビュー](CITY-ANALYTICS-REVIEW.md) |
| 追加運用データ | 分離DBの3試験成功。再適用不変、既存行・写真保全、途中失敗の巻戻し、会話・写真・位置の公開範囲、次回開催のクーポン確保 | [pytest.xml](../artifacts/operational-seed/pytest.xml) |
| 候補・投稿ページング | 関連回帰29試験、ページングと追加データ4試験がそれぞれ成功。別実行を一括件数に合算しない | [discovery-suite.xml](../artifacts/city/discovery-suite.xml)、[paging-operational.xml](../artifacts/city/paging-operational.xml) |
| 通う旅 | 最終専用5試験成功。工程順の追加1試験、閲覧権失効後の個別解除1試験も成功。初回混合実行は7成功・1失敗で、その失敗記録を保持 | [verification.json](../artifacts/programs/verification.json)、[sequence-final.xml](../artifacts/programs/sequence-final.xml)、[inactive-unlink-verification.json](../artifacts/programs/inactive-unlink-verification.json) |
| 追加割引・予算 | 専用9試験、API接続1試験、初回予算設定時の既存確保額1試験が別実行で成功 | [pytest.xml](../artifacts/zone-benefits/pytest.xml)、[router-check.xml](../artifacts/zone-benefits/router-check.xml)、[initial-budget-display.xml](../artifacts/zone-benefits/initial-budget-display.xml) |
| 実DB保全 | 比較対象62表で旧行を保持。既存画像36件のバイト保持、integrity=ok、外部キー違反0 | [seed-preservation.json](../artifacts/city/seed-preservation.json) |
| 実配信のAPI読取 | 12 GET成功。対象利用者で候補8、クーポン17、実施21、訪問記録20・写真20、仲間内/共有会話各5件。市は30/90/365日の各期間で6事業者・33公開プラン・42人・6地域 | [live-experience.json](../artifacts/city/live-experience.json) |
| 統合回帰 | 322試験＋12 subtests成功。JUnitは計334件、失敗・エラー・skip各0、244.248秒。追加修正の対象試験は前記の別記録 | [tests.xml](../artifacts/quality/revisit-integrated/tests.xml) |

実配信読取では利用者による市APIと他社の私的集計を拒否し、自社集計は取得できた。12要求の最大59.2msは一度のローカル読取結果であり、負荷試験やp95の性能保証ではない。42人の再訪表示は投入したシナリオの集計であり、施策による実再訪の改善率ではない。市の推移は公開可能な集約区分を使い、非表示を0へ置換しない。

## 統合品質の差分

比較は `nnishi-revision` → `revisit-integrated`。設定ハッシュとOxlint実行イメージは同一。フロントエンドの測定対象は54→67ファイル、バックエンドは69→84モジュールへ増えた。行番号の移動を除き、ファイル・規則・診断内容の多重集合で比較した。

| 検査 | 前回 | 統合計測 | 差分・範囲 |
|---|---:|---:|---|
| TypeScript | 0 | 0 | 型エラーなし |
| Oxlint | 119 | 115 | 新規0、Appの3件とJournalの1件解消。全体は未合格 |
| Stylelint | 126 | 126 | 新規0、解消0。既存指摘を除外していない |
| Ruff | 0 | 1 | main.pyのimport順I001。主担当修正後、対象ファイルの再検査は0 |
| 複雑度C901 | 14 | 14 | 同じ指摘が残存、新規0 |
| Bandit | 19 | 19 | 行番号以外は同じ指摘、新規0。検出0や全面安全性を主張しない |

証拠は [フロントエンドmanifest](../artifacts/community/frontend-quality/revisit-integrated-manifest.json)、[バックエンドsummary](../artifacts/community/quality/revisit-integrated/summary.json)、[診断差分](../artifacts/quality/revisit-integrated/finding-delta.json)。計測後の `has_link` 修正を含む4ファイルの厳格lint・全体型検査・main.pyのRuffは [補足再検査](../artifacts/quality/revisit-integrated/post-fix-checks.json) にハッシュ付きで分離した。計測後に変わったファイルを、元の全体計測で検証済みとは扱わない。

追加修正では、初めて割引予算を設定するときも既存の確保・利用総額を表示して下限に用いる。通う旅は開催詳細が閲覧できなくなっても本人の紐付けを解除できる。降格予定日は年を表示し、翌年の予定を過去日と誤読させない。階級と特典資格の点・維持条件が同一のときは説明の重複を短縮し、事業者確認済みの点だけが特典対象になる区別を保持した。

### 最終再計測 revisit-final

全体を再計測し、Ruff 0・型エラー0・Oxlint 115・Stylelint 126・C901 14・Bandit 19、新規指摘0。判定は既存指摘が残る `review-required`。前の計測で検出したI001は解消した。最終manifestの全ソースハッシュと現行ファイルの一致も確認した。証拠は [最終summary](../artifacts/quality/revisit-final/summary.json)、[フロントエンドmanifest](../artifacts/community/frontend-quality/revisit-final-manifest.json)、[バックエンドsummary](../artifacts/community/quality/revisit-final/summary.json)。

最終集約ツールの比較基準は `daytrip-wa-verified` / `daytrip-final` で、Oxlint124→115（9件減）。本節前半の直前基準 `nnishi-revision` からは119→115（4件減）であり、基準の異なる差分を同一の改善件数として扱わない。最終staticレポートの `tests: not-run` はその再計測で動作試験を再実行していない意味で、上記の統合回帰とは別である。

### 最終配信再計測 revisit-release

`revisit-final` 後の `Daytrip.tsx` と `provider-dashboard.css` の遅い修正を含め、再計測した。Ruff 0・型エラー0・Oxlint115・Stylelint126・C90114・Bandit19、実行エラー0、新規指摘0。全体判定は既存指摘による `review-required` のまま。[release summary](../artifacts/quality/revisit-release/summary.json)、[frontend manifest](../artifacts/community/frontend-quality/revisit-release-manifest.json)、[backend summary](../artifacts/community/quality/revisit-release/summary.json) の全測定対象ハッシュと、この記録時点の現行ファイルが一致することを確認した。前の計測へ修正後の成功を遡及させていない。

## 主担当の実画面受入

[観測記録と画像ハッシュ](../artifacts/city/browser-acceptance.json) は主担当のCUA操作報告を記録したもの。記録担当がブラウザー操作を再実行したという意味ではない。

- 自社 / N西市全体の90日切替、全国 / N西市周辺の地図切替を確認。
- 通う旅の1/3回の利用確認済み進捗、次回開催を選ぶダイアログを確認。
- 階級から17クーポンへの導線と、事業者の追加割引予算を同値で保存した成功表示を確認。
- 20件の記録から地図の9月2日を選び、17〜20件の一覧ページに連動することを確認。
- 共有相談の利用者送信→事業者受信・返信→利用者受信を確認。会話内容の観測を写真だけの推測で代替していない。

保存画像は [全体](../artifacts/video-revisit/screens/actual-full.jpg)、[通う旅](../artifacts/video-revisit/screens/program-stage.jpg)、[予算](../artifacts/video-revisit/screens/zone-stage.jpg)、[記録地図](../artifacts/video-revisit/screens/journal-stage.jpg)、[共有返信](../artifacts/video-revisit/screens/reply-stage.jpg)。スクリーンショットは各時点の表示証拠であり、全操作のアクセシビリティ試験ではない。

### 狭幅と最終二画面の追加受入

主担当が最新Docker配信をCUAで確認した。表の横スクロールと、文書全体のはみ出しを区別して測定する。

| 表示 | clientWidth / scrollWidth | 結果・証拠 |
|---|---|---|
| 自社・viewport320px | 修正前305 / 403 → 修正後305 / 305 | 暗黙の最小幅で期間・グラフが広がる問題を修正。[修正後](../artifacts/city/provider-320-after.png) |
| 市全体・viewport320px | 305 / 305 | 文書外の横はみ出しなし。比較表は内部スクロール。[市全体](../artifacts/city/provider-320-city.png) |
| 事業者・viewport854px | 839 / 839 | 文書外の横はみ出しなし。主担当CUA計測 |
| stage1440×900 | 外側1440 / 1440、右843 / 843、左410 / 410 | 左右の画面を維持し、横はみ出しなし。[最終stage](../artifacts/video-revisit/screens/final-stage.png) |

[番付の最終画面](../artifacts/video-revisit/screens/rank-v4-stage.jpg) で降格予定の「2027年」と、同一条件の説明が一度に短縮された表示を主担当が目視確認した。

同じアカウントを別windowでも使用中、scopeボタンの初回操作では切替せず、2回目に切り替わる事象を一度観測した。コード上は再開保存が409競合した場合に画面が再生成され、scopeが自社へ戻る経路がある。ただし当該操作の409や再生成は記録しておらず、原因・再現条件は未確定。切替ボタン自体に選択を戻すeffectはなく、競合が原因と断定しない。通常の切替と狭幅の受入結果とは別の未確定観測として残す。

## 受入状態と残る確認

CP78・79・80・81・82・84・85・86は受入条件をAPI試験・独立コードレビュー・保全記録・上記実画面観測で確認し、証拠を付けてdoneへ更新した。CP85の遅い旧応答破棄は取得処理のscope・abort・世代条件を読取確認した範囲で、ブラウザーの通信遅延注入試験とは分ける。

CP85は最初の83行では「100件超」の受入証拠が不足したためreviewに残した。その後、主担当が123行（本人から可視122行）へ増やし、24件ずつの取得・重複なし・途中の新規投稿・他者下書き非表示・退会後の拒否を確認する対象1試験に成功（1.159秒）。[feed-over-100.xml](../artifacts/city/feed-over-100.xml) を追加し完了にした。初回の不足を過去に遡って合格へ変更していない。

CP79は320px・854pxと左右端末の横幅を確認し完了。CP83は今回の文字200%をIABの対応操作で確認できなかったためreviewを維持する。未実行を成功扱いせず、過去版での成功も流用しない。CP87の約1分動画は主担当の制作・目視確認対象で、この文書のAPI成功で代替しない。固定C1は40/100据置である。

## 既存の制限

現在の実AI/APIは導入しない。外部地図やクラウドへ接続せず、ローカル素材とDBを用いる。通常Edgeプロファイルの既存停止、旧不要物の削除拒否、既存の品質指摘はこの機能の完成とは別の課題として残す。
