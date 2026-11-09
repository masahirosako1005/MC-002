# 講コミュニティ：ローカル起動

ReactとPythonの新版プロトタイプ。旧版の8080とは別に、`http://127.0.0.1:8081`で動かす。Composeプロジェクトは`kou-community`、データvolumeは`kou-community_community-data`。旧版のコンテナー・DB・volumeを停止・削除・流用しない。

## 状態

2026-11-09：三役・中央画面をDockerへ取り込み、8081で起動した。schema 1から2へ移行し全29表を確認、既存の講2件・参加者6件・投稿7件・media7件・所属201件の全行ハッシュが移行前後で一致した。旧8080は継続稼働している。schema 1、schema 2それぞれのDB＋写真を保全・隔離復元済み。三役初回イメージではコンテナー20項目とLinuxのモデル読込み・生成写真4枚の推論を確認した。主担当の初回ブラウザー試験で保存した旅行計画・選択・相談・返信を含め、14表の再起動保持も確認した。現在は画面修正版（`index-B73dds9S.js` / `index-NztS_E8R.css`）へ更新し、配信ファイル一致と新旧health HTTP200を確認済み。今回backend/modelは変更しておらず、モデル・保全の試験は反復していない。三役画面9/9・左右の安全性8/8を再検証し、1440×900の上部見出し＋左右スマホの構図を確認した。通常Edgeの応答停止はCP27で調査中。旧版の試験件数や評価点は新版の証拠として扱わない。

## 構成

- `Dockerfile`：Node 24でReactをビルドし、Python 3.12の同一オリジン配信へ含める。
- `app`：`app.main:app`、8001番。非root UID10001、read-only rootfs、capabilityを除外。DBと権限付き画像は`/app/data`へ保存する。
- `gateway`：nginx、非root UID101。ホストの127.0.0.1:8081だけへ公開し、固定のappへ転送する。
- `models/`：開発時に取得したモデルを`/app/models`へ読取専用で渡す。実行中にダウンロードしない。
- `assets/`：生成した初期写真を`/app/seed-assets`へ読取専用で渡す。画像の公開ディレクトリではなく、バックエンドが権限付き保存領域へ取り込む入力。
- `.dockerignore`：バックエンドの必要ソースとフロントエンドだけをビルドへ含め、モデル・画像・DB・成果物を除外する。

モデルはMobileNetV2 ONNX（約14MB）、CPUでONNX Runtimeを使う。取得元・固定revision・ハッシュ・ライセンスは`models/manifest.json`、`models/MODEL-README.md`、`models/LICENSE`に記録する。取得スクリプト`models/fetch_model.py`は開発時専用であり、実行アプリから呼び出さない。モデルが使えない場合の表示を推論成功と偽らない。

LinuxコンテナーのONNX Runtime 1.31.1で実モデル読込みと4枚の生成写真の推論を確認した。読込0.62秒、`coast`は海辺0.9655、`coffee`はカフェ0.6065/食事0.1305、`table`は食事0.8231、`woodland`は候補なし。これは初回イメージの分類器を直接呼び出した確認であり、API処理・画面・分類精度全体の評価ではない。Windowsネイティブでは担当者が1.31.1の初期化終了と1.23.2のDLLエラーを確認しているため、完成アプリの推論はDockerのLinux環境で行う。

初回Linux実行時にはread-only環境でtelemetry device IDを永続化できない警告があった。コードはtelemetryを無効化し、appネットワークは外向き接続を持たない。警告を消すために書込権限や外向き通信を広げていない。

## 起動

初回はDocker/WSLと依存・モデルの取得が必要。既存PCではDockerが稼働している。`models/`と`assets/`を用意した後、PJルートで実行する。

```powershell
.\community\scripts\start.ps1 -Build
```

ビルド済みの起動は`-Build`を付けない。ビルドとモデル推論・他の重いビルドを同時に走らせない。現在の設定はapp768MiB・1.5CPU、gateway64MiB・0.5CPU。実測によって調整する。

```powershell
docker compose -p kou-community -f community/compose.yaml ps
docker compose -p kou-community -f community/compose.yaml logs --tail 50 app
docker compose -p kou-community -f community/compose.yaml stop
```

上記stopは新版だけが対象。`down -v`は保存を削除するので通常の終了手順として使わない。アプリの保存データや画像・認証情報を調査用サービスへ送らない。

## 結合確認

実ブラウザー・推論・ビルドが同時に動いていないことを確認した後、PJルートから実行する。

```powershell
.\.venv\Scripts\python.exe community/scripts/verify_container.py --restart
.\.venv\Scripts\python.exe community/scripts/verify_model.py
```

最初のコマンドは新版appを再起動し、同じCookieの本人情報・好み・所属が保持されること、独立volume、ローカル公開、権限制限、外向きTCP接続拒否、DB完全性・バックアップの表件数一致を確認する。旧8080は前後の稼働確認だけ行う。`--restart`なしでは再起動確認を省く。結果は`community/artifacts/container-verification.json`へ保存し、認証情報・個票は出力しない。

2つ目は公開bootstrapのmodel状態と、コンテナー内のCPU分類器を生成写真4枚で確認し、`community/artifacts/model-verification.json`へ保存する。候補なしと推論失敗を区別する。両スクリプトは日時付きの記録も保存するので、失敗後の再実行で元の結果を失わない。

検証で作るバックアップはvolume内の`/app/data/backups/`に置くDBのコピー。投稿写真ファイル自体は含まないため、これだけで写真を含む完全復元ができるとは扱わない。本運用のバックアップではDBと対応する`media/`、モデルの版、設定を合わせて保全する必要がある。

## DBと写真の一括保全・隔離復元

`scripts/full_snapshot.py`はDBと`media/`全体を同じ停止期間に保存する。バックアップの前に、ブラウザー試験や写真処理を担当者間で止める。`backup --allow-stop`は**新版appだけを短時間停止**し、終了時には元のappを再開する。旧8080は操作しない。

```powershell
.\.venv\Scripts\python.exe community/scripts/full_snapshot.py backup --allow-stop
```

保存先は必ず`community/backups/日時-識別子/`。DB本体とWAL/SHMを別作業領域へコピーしてからSQLite backupで独立DBを作るため、未checkpointのコミットも含む。`media/`を全件コピーし、各ファイルのサイズ・SHA-256、DB整合性・外部キー・スキーマ版・表件数を`manifest.json`へ保存する。完了manifestがないものは復元対象にしない。`runtime.json`には当時のDockerイメージIDとモデルmanifestを記録する。

実際に保全したschema 1の例：

```powershell
.\.venv\Scripts\python.exe community/scripts/full_snapshot.py verify --snapshot community/backups/20261109T054148Z-0b0b96873966
.\.venv\Scripts\python.exe community/scripts/full_snapshot.py restore --snapshot community/backups/20261109T054148Z-0b0b96873966
```

`restore`は**必ず新しい`kou-community-restore-…`volumeを作り**、ファイル一覧・ハッシュ・DB整合性・全表件数を照合する。空でない復元先へは書き込まない。現行volumeの上書き・削除・Composeの保存先切替は行わない。旧スキーマへ戻す必要がある場合は、復元されたvolumeを別構成で起動し、対応する旧イメージとモデルを確認してから別途切替を計画する。

バックアップには認証用データと写真が含まれる。Git・ソース配布物・クラウド調査へ含めない。モデル重みはこのバックアップに含めず、プロジェクトの`models/`を保持する。記録したDockerイメージも保持する。検証・復元用コンテナーは外部ネットワークなし、非root、read-only rootfs、限定mountで実行し、イメージを自動取得しない。

### 移行前保全の実測

- [合成試験](artifacts/snapshot-tests.json)：7項目成功。未checkpointのWAL保存、コミット行保持、正常検証、空の隔離先への復元、写真バイト一致、非空先拒否、写真破損の拒否を確認。初回はWindows bind mountルートの属性変更が拒否されたため、ルート属性を変えず内容をコピーする方式へ修正した。初回失敗は`artifacts/snapshot-tests-first.json`、後続試験の各結果はfixtureフォルダに保持する。
- [実バックアップ](artifacts/full-snapshot-20261109T054156496503Z.json)：schema 1、DB＋写真9ファイル、3,965,322 bytes。講2件・参加者6件、全15表。取得後appを再開。
- [独立した再検証](artifacts/full-snapshot-20261109T054201813688Z.json)：ファイル一覧・SHA・DB整合性・外部キー・表件数が一致。
- [隔離復元](artifacts/full-snapshot-20261109T054204273733Z.json)：新規volume`kou-community-restore-431549f81b054d22bcdac6f593a49ae0`へ復元し、同じ検査に成功。現行volume不変。終了後8081/8080ともhealth HTTP200。

この復元試験はschema 1のファイルとDBの一致確認。復元先からの全API・画面操作は対象外。続く稼働volumeのschema 2移行は別工程として実施し、[移行記録](artifacts/schema2-migration-container.json)へ保存した。

### schema 2の保全・再起動保持

主担当の画面試験が停止した時間に、旅行計画・相談・返信を保存済みのschema 2を保全した。[実測記録](artifacts/schema2-persistence.json)には次を区別して保存している。

- 保存先`backups/20261109T055041Z-9862048da5c5`。DB＋写真9ファイル、4,096,394 bytes、全29表。旅行計画・条件・内部会話・選択・相談・返信各1件、冪等キー3件を含む。
- 既存講・参加者・投稿・写真、新しい旅行計画と関連記録の14表について、appの停止・再開前後で件数と全行SHAが一致。
- 独立したverifyと、新規volume`kou-community-restore-ec75912fd2944b13bc4e2021dcf2003b`へのrestoreが成功。全ファイルSHA・DB完全性・外部キー・29表件数が一致。現行volumeへ戻していない。
- 最後に旧8080・新8081ともhealth HTTP200。復元先のAPI・画面を起動した検査ではない。復元時点の認証・所属も保存されるため、実運用で切り替える場合は、その後に取り消した権限やセッションを再無効化する。

同じ確認を行う場合は画面・写真処理を止めた時間に実行する。このコマンドはschema 2を前提とし、新版appを短時間停止・再開する。

```powershell
.\.venv\Scripts\python.exe community/scripts/verify_marketplace_persistence.py --allow-stop
```

### 今回の実測記録

| 証拠 | 確認結果 | 限界 |
|---|---|---|
| [container-verification.json](artifacts/container-verification.json) | 三役初回イメージ`7dcac589…`で20チェック成功。非root・capability 0・NoNewPrivs・read-only実設定/書込拒否・内部ネットワーク・外向TCP不可・独立volume・127.0.0.1公開・DB整合/外部キー・DBバックアップ一致・旧8080健康を確認 | この実行はrestart_tested=false。baselineで実施した再起動保持21項目の記録は日時付きファイルへ保持。全UI・全権限・写真完全復元の保証ではない |
| [frontend-refresh-deployment.json](artifacts/frontend-refresh-deployment.json) | 画面修正版`ba2c2758…`へ更新。HTML内のJS/CSS名一致、両ファイルと8080/8081 health HTTP200 | frontendのみの更新。モデル・保全・20項目をこのイメージで再実行したという記録ではない |
| [schema2-migration-container.json](artifacts/schema2-migration-container.json) | schema 1→2、29表。講・参加者・投稿・media・所属の件数と全行SHAが一致 | 対象5表の既存行保持。新機能の全操作や選択・相談の再起動保持は別試験 |
| [model-verification.json](artifacts/model-verification.json) | bootstrap ready、ONNX Runtime 1.31.1、CPUExecutionProvider、モデルSHA-256一致。読込0.2721秒、生成4枚の推論各0.2338〜0.266秒、全呼出し成功 | 精度評価用データセットではない。候補スコアは本人の好みの確率ではなく、木立の写真は候補0件。実利用者の体験・推薦効果は未測定 |
| Docker stats（確認終了後の1回測定） | 新app87.45MiB/768MiB、新gateway2.273MiB/64MiB、旧app/旧gatewayも稼働。ホスト空き約2.26GiB | 推論中のピークメモリ・長時間負荷ではない。並列ビルド・大量の写真処理前には再確認する |

コンテナー記録には実イメージID・起動時刻・メモリ/CPU/PIDの実設定も保存した。構成を変えたら旧記録だけを根拠に合格とせず、該当する確認をやり直す。

## 実行時の境界

appは外向き通信を持たないinternal networkのみへ接続する。gatewayはブラウザー入口とappを接続するため別ネットワークも持つ。gateway全体の外向き通信をOSファイアウォールで遮断したという意味ではない。アプリの画像・モデル・フォント・APIはローカルで提供する。

JSON書込みはOriginとCSRF、画像は同じ保護に加えてバックエンドで形式・大きさを検査する。gatewayは12MiB画像とmultipartの余裕として本文13MiBを上限にする。実際の画像上限はAPI契約の12MiB/20MP。写真は静的公開せず、現在の所属・所有者を確認するAPI経由で配信する。

API・ログイン・データ条件は[API-CONTRACT.md](API-CONTRACT.md)を参照。認証設定の実データ運用、公開インターネット運用、実利用者による有効性は別途検証が必要。

構成の参考：[Docker Compose networks](https://docs.docker.com/reference/compose-file/networks/)、[Docker Compose services](https://docs.docker.com/reference/compose-file/services/)（2026-11-09確認）。これらの設定を採用しただけで全面的な安全性を証明するものではない。
