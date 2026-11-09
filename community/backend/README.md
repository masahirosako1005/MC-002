# 講コミュニティのローカル API

FastAPI / SQLite。起動入口は `app.main:app`、契約は [API-CONTRACT.md](../API-CONTRACT.md)。Docker を実行対象とし、旧版とは DB・Cookie・ポートを分離する。

## 保存と起動

- `APP_DB_PATH`：SQLite。WAL、外部キー、同期 FULL、書込みトランザクションで参加承諾と講成立を一体化。
- `MEDIA_DIR`：再エンコードした写真。DB と合わせてバックアップする。削除済み写真は権限判定で即時配信停止、削除失敗ファイルは worker が再試行する。
- `MODEL_DIR`：固定モデルとハッシュ manifest。実行時ダウンロードなし。
- `SEED_ASSET_DIR`：生成カタログ写真。公開カバーは固定 4 キーだけ、投稿画像の認可と分離する。
- `STATIC_DIR`：ビルド済み React。API の未知パスを HTML に置き換えない。
- `APP_ALLOWED_ORIGINS`：カンマ区切りの許可 origin。Cookie は HttpOnly / SameSite=Strict。HTTPS 時は `APP_COOKIE_SECURE=1`。

ローカル API 起動はこのディレクトリで `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`。依存は `requirements.txt`、試験は `requirements-dev.txt`。

初期操作ユーザーは `aoi` / `ren` / `mio`、試作用パスワードはそれぞれ `<username>-local-2026`。初回作成時に `KO_PASSWORD_AOI` / `KO_PASSWORD_REN` / `KO_PASSWORD_MIO` で変更可能。これは合成データ用の設定で、実個人データを扱う運用にそのまま使わない。197 人の追加架空会員はログイン不可、マッチ参加許可も初期無効。3 人の明示承諾は完走でき、5 人要求は人数不足を返す。

## API の範囲

ログイン・切替・ログアウト、コミュニティ作成・招待参加・退出、写真投稿・下書き・公開・削除、画像解析ジョブと手動タグ訂正、本人の関心とコミュニティ別利用/表示/参加許可、旅候補、同じコミュニティの仲間提案、参加/見送り、講の計画・任意の協力を提供する。

画像は JPEG / PNG / WebP の実体を検査し、単一フレーム・12 MiB・2,000 万画素上限。EXIF 除去と 1,600 px 以内への再エンコード後だけ保存する。画像デコードと分析は各 1 件ずつ。API の CSRF / Origin / Host / サイズ制限、所有者・現在所属の再確認、CSP / no-store を適用する。

画像分析は MobileNetV2 / ImageNet の画素入力による CPU 推論。固定クラスから場面タグ候補を作る。候補スコアは好みや行動の確率ではなく、精度評価済みの信頼度でもない。人物識別・属性・宗教・妊娠等の推論はしない。施設の正確な特定もしない。候補なし・モデル不準備・失敗は正直に返し、本人の手入力で回復できる。モデル取得経緯は `../models/MODEL-README.md`。

分析ジョブは期限付き lease と試行数を保存する。有効 lease を再起動で奪わず、期限切れは 2 回までで failed にする。古い実行結果は lease 一致時のみ反映する。利用者の明示的再実行は試行数をリセットする。

## 現時点の限界

- マッチ条件は本人確認済みの関心、同じ所属、3 種の許可。希望日は提案へ表示・保存するが、個人の空き日程や予算の自動照合は未実装。価格・所要時間はローカル旅行案の目安で、営業・空席・交通予約の確認ではない。
- 本人が確定した好みだけを持ち越す。投稿タグの集計候補を未承諾で別コミュニティの推薦に使わない。
- 退出した人は投稿/画像/講へのアクセスを失う。講メンバーの退出後の再編・再募集は未実装。
- SQLite とメディアを一組で復元する必要がある。アカウント削除、運用向けパスワード変更・復旧、マルチプロセス rate limit、全ユーザーの容量運用は今後の課題。
- Windows の ONNX Runtime DLL 読込みがこの PC で失敗するため、実推論の動作確認先は Linux Docker。API の通常試験ではモデルなしの回復も検証する。

## 試験

PJ 直下で `.venv/Scripts/python.exe -m pytest community/backend/tests -q --basetemp community/backend/.backend-test-tmp`。

2026-11-09：16 passed / 1 skipped（14.79 秒）。skip はこの Windows 環境の実モデル読込み失敗のみ。モデル位置は `community/models` を存在確認し、Linux では読込み失敗を skip しない。起動・認証、越権、画像検証/削除、3 人の明示承諾と重複応答、DB 失敗時の原子性、退出・許可取消、永続性、期限切れ分析の有限回復を検証した。Docker 結合とブラウザー試験は別担当が実施するため、この結果に含めない。
