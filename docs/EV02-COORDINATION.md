# EV02 同時作業の調整記録

## 最終記録

共有indexのタイミングが重なり、EV02の評価文書と証拠は別作業の96c79c0へ一緒に記録された。アプリの評価対象が21eb465であることは変更しない。証拠の原本byteを保つ.gitattributesは追加済みだが、最初にstageされたCRLF原本の一部はGitの既存変換結果が残ったため、後続で証拠だけを再正規化して原本SHAとの一致を確認する。公開ソースや実利用データの巻戻しは行わない。

EV02の優先改善と検証を21eb465で確定。全体433+細分32、最終UI005の9シナリオ、復元11、専用再起動9が成功。14:07時点で検証imageとproduction8081のapp/static一致を読取確認した。以後に始まったカメラ/AR/QRの追加実装・依存は別作業であり、EV02の結果を自動適用しない。現在の詳細はdocs/evaluation-frameworks/EV02-REPORT.md。

共有DESIGN/TASKS/CHANGELOGへEV02の独立した末尾節を追加。DESIGNの未commit AR節は今回の検証済み記録へ混ぜず、EV02節だけを部分stageする。共有チケット台帳には他作業の変更もあるため、EV02の完了snapshotとrevisionを証拠側にも保存する。実利用のDB/volumeや動画は削除・巻戻ししていない。

## 追補：停止解除後の現在の分担

14:02 JST：EV02のアプリ差分はまだcommit/stageしていない。共通indexへはゲーム側の部分stage/commitが完了するまで書き込まない。main.pyのstageログイン改修/account router/import整理、ProviderWorkspaceのdirty確認/useIdはEV02所有のまま。別作業のゲームhookだけのcommitを妨げない。production8081の再buildは別作業が担当中で、EV02は専用8082だけを再buildしている。provider-dashboard.cssの文字コントラスト3宣言を新たに修正し、検証中。

構成移動はd1bd8f9で確定し、以下の停止中メモは過去の状態となった。EV02実装を再開し、対象試験60件・Unicode追試27件・アカウント29件は成功。全体試験は専用basetemp/cacheを指定して実行中。実画面は別compose project `kou-eval-ev02`、port8082、volume `kou-eval-ev02_community-data` に分離し、実利用の8081を変更しない。

並行チャットは現地おみくじと動画・発表資料を担当し、main.py、ProviderWorkspace.tsx、Daytrip.tsxとOmikuji関係の新規ファイル、共通DESIGN/TASKS/CHANGELOGを所有する。EV02はそれらを凍結して引き渡した。自分の追加変更はEV02専有の評価文書と担当ソースへ限定する。main.pyには引き渡し前にaccount routerを追加済み。ProviderWorkspaceの未保存入力確認も引き渡し前の変更である。

静的再測定では型検査/Ruff成功、Oxlint82、Stylelint115、Bandit20（うち新規1件はrate-limit定数に対する検出）、C901 14。集計器の生結果は維持し、行番号変更等を含む差分を独立レビューする。全体・画面の結果を過去の構成移動試験の成功として扱わない。

## 過去の停止時点の記録（以下）

2026-11-10。このチャットで利用者が「追加基準で8項目を評価し、必要修正と再検証、文書化」を明示指定。別チャットのroot-layout-finalが実行中と連絡を受け、EV02の重複する編集/試験を停止した。

- 導入済み評価基盤はcommit b55bfb0（アプリソースを含まない）。EV01は導入完了。EV02は作業中。
- ev02-beforeの静的計測は保存済み。全pytestは専用プロセスツリーのみ停止し、合格扱いにしない。理由/証拠: artifacts/quality/ev02-before/coordination.json。
- 次のEV02試験は専用basetempを使用し、他の試験一時領域に干渉しない。
- 構成移動がGit確定するまで、実装担当2名はREAD-ONLY。現状の変更は戻していない。

## EV02が変更したソース（未検証、構成移動の検証結果に含めない）

frontend/src: Choice.tsx、ProviderWorkspace.tsx、KoPage.tsx、ExperienceReference.tsx、App.tsx、Circles.tsx、Journal.tsx、Marketplace.tsx、Occasions.tsx、PlanDiscovery.tsx、Preferences.tsx、ReflectionWorkspace.tsx。

入力破棄の確認、選択肢の焦点移動、ラベル関連付け、状態通知の意味付け、事業者変更時の古い情報の非表示。初期の一部tscは成功したが最後の変更は未検証。Preferencesのsave-bar CSSをoutputにも合わせる修正が残る。

backend/app: database.py、service.py、main.py、schemas.py、security.py。

新規scryptパラメータ強化と旧hashの互換更新、stage再認証token回転、写真flush/fsync、同意boolの厳格型確認、本文全体deadline。テスト未実行。main import整理と写真書込故障注入試験の対応が残る。

これらの変更を構成移動だけのコミットとして一括取り込まない。EV02担当が対象試験→全体→画面を検証して意味単位で保存する予定。

共通DESIGN/TASKSにはEV01の短い追記、docs/CHANGELOGとEVALUATION-TOOLSには導入記録を追記した。ASVS台帳/独立評価の記録作業は専有docs/evaluation-frameworks内で継続。アプリのDB/volume削除は行っていない。
