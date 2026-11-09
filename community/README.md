# 講コミュニティ：ローカル起動

ReactとPythonの新版プロトタイプ。旧版の8080とは別に、`http://127.0.0.1:8081`で動かす。Composeプロジェクトは`kou-community`、データvolumeは`kou-community_community-data`。旧版のコンテナー・DB・volumeを停止・削除・流用しない。

## 状態

2026-11-09：最終API・画面を取り込んだDockerビルド、8081起動、Linuxのモデル読込み・推論、再起動・記録保持・コンテナー設定の確認を実施した。旧8080は継続稼働している。旧版の試験件数や評価点は新版の証拠として扱わない。広範な画面操作・コミュニティ成立の検証は主担当が別に行う。

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

### 今回の実測記録

| 証拠 | 確認結果 | 限界 |
|---|---|---|
| [container-verification.json](artifacts/container-verification.json) | 21チェック成功。非root・capability 0・NoNewPrivs・read-only実設定/書込拒否・内部ネットワーク・外向TCP不可・独立volume・127.0.0.1公開・DB整合/外部キー・再起動後の本人情報/好み/所属一致・DBバックアップ一致・旧8080健康を確認 | コンテナー/APIの確認であり、全UI・全権限パターン・写真ファイルの完全バックアップ復元の保証ではない |
| [model-verification.json](artifacts/model-verification.json) | bootstrap ready、ONNX Runtime 1.31.1、CPUExecutionProvider、モデルSHA-256一致。読込0.4986秒、生成4枚の推論各0.2072〜0.2745秒、全呼出し成功 | 精度評価用データセットではない。候補スコアは本人の好みの確率ではなく、木立の写真は候補0件。実利用者の体験・推薦効果は未測定 |
| Docker stats（確認終了後の1回測定） | 新app87.45MiB/768MiB、新gateway2.273MiB/64MiB、旧app/旧gatewayも稼働。ホスト空き約2.26GiB | 推論中のピークメモリ・長時間負荷ではない。並列ビルド・大量の写真処理前には再確認する |

コンテナー記録には実イメージID・起動時刻・メモリ/CPU/PIDの実設定も保存した。構成を変えたら旧記録だけを根拠に合格とせず、該当する確認をやり直す。

## 実行時の境界

appは外向き通信を持たないinternal networkのみへ接続する。gatewayはブラウザー入口とappを接続するため別ネットワークも持つ。gateway全体の外向き通信をOSファイアウォールで遮断したという意味ではない。アプリの画像・モデル・フォント・APIはローカルで提供する。

JSON書込みはOriginとCSRF、画像は同じ保護に加えてバックエンドで形式・大きさを検査する。gatewayは12MiB画像とmultipartの余裕として本文13MiBを上限にする。実際の画像上限はAPI契約の12MiB/20MP。写真は静的公開せず、現在の所属・所有者を確認するAPI経由で配信する。

API・ログイン・データ条件は[API-CONTRACT.md](API-CONTRACT.md)を参照。認証設定の実データ運用、公開インターネット運用、実利用者による有効性は別途検証が必要。

構成の参考：[Docker Compose networks](https://docs.docker.com/reference/compose-file/networks/)、[Docker Compose services](https://docs.docker.com/reference/compose-file/services/)（2026-11-09確認）。これらの設定を採用しただけで全面的な安全性を証明するものではない。
