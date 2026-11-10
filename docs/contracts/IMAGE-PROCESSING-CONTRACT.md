# 画像と条件案内の処理方式（CP45）

最新指定により、通常起動・発表で実AIや外部APIを呼ばない。画像モデル/ONNX Runtime/NumPy/APIキーは通常実行に不要。既存のモデルコードとモデルファイル、画像資産、本人が保存したタグ・関心・投稿は削除しない。既存条件整理はローカルの数値抽出・テンプレート・実公開カタログ照合を続け、生成AIによる理解や予約成立とは表示しない。

## APIの最小変更

- `GET /api/bootstrap`の`model`は`{status:'guided',name:'写真のタグを自分で選ぶ',mode:'manual-with-predefined-assets',method:'manual-photo-tags-v1',inference_enabled:false,external_ai_enabled:false,description}`。
- 写真の`analysis.status`に`manual | guided`を追加。どちらも終端状態でpoll不要。`method`と`inference_enabled:false`を付ける。新規`model_version`はnull。
- 任意写真は`manual`、`tags:[]`、本人がタグを選んで保存する。認識中/解析失敗/再試行へ進ませない。
- 既知の公開素材4枚とバイト列のSHA-256が一致する場合だけ`guided`、`method:'predefined-photo-tags-v1'`、事前設定した`tags:[{id,label}]`を返す。確信度scoreは作らない。これは画像認識ではない。名前だけ同じ別写真や似た写真は対象外。候補は本人の選択なく投稿/関心へ保存しない。
- 過去のjobsは保存値を保持。旧queued/running/failed/succeededは読込応答で終端manualへ投影し、旧候補があれば`method:'saved-candidates-manual-review'`と区別する。旧model_versionは過去情報として保持し、今回の推論結果とは呼ばない。画面は現在の処理方式と候補の由来を表示する。
- `POST /api/media/{id}/analyze`は互換入口として残すが、新しい推論jobを作らず現在の終端候補を返す。本人認可・CSRFは維持。
- `GET /api/marketplace/capabilities`のhubは画像mode/method/inference_enabled=false/external_ai_enabled=falseと条件整理/カタログ照合の方式を返す。
- `GET /api/circles/help`は現local-catalog-rules-v1を維持し、ローカルの定型案内・条件整理であり生成AI/外部接続なしと明示する。

## 起動と保全

base composeはモデルbindを要求しない。startはモデルフォルダを検査しない。通常requirementsとDocker検査から推論依存を外し、従来依存は将来参照用の別ファイルへ保持する。workerは通常起動しない。モデルが存在しても通常の起動経路からロードしない。

将来の本番では外部AI adapterを実装予定だが、今回は実装しない。コードの出力境界にMOCの定型処理である旨と将来の置換点を注記する。認証・同意・構造検証・カタログ照合・保存は将来もサーバー側の責務とする。

以前に本人が削除済みにした写真の一時的なファイル削除失敗は、推論と分離した最大32件/回の保守処理で再試行する。起動時と明示削除後に実行し、active写真・covers・保存先外を対象にしない。新しい保守cursor設定だけを保存し、旧jobや本人データは書き換えない。

アップロードのサイズ/形式検証・EXIF除去・位置候補の明示opt-in・所有者権限は維持する。DBスキーマ変更は不要で、既存jobのタグ/版・投稿タグ・プロフィールを起動時に書き換えない。講の条件保存、候補保存、事業者招待の本人承諾、見積双方確認は実保存を続ける。

受入：モデル欠如/キー欠如/ネットワーク禁止下の起動、モデルimport未実行、任意画像→手動タグ投稿、既知素材候補/偽装名不使用、旧pending応答終端化と旧DB値保持、講の保存・招待・双方確認の回帰。Docker受入と隔離API試験を区別して記録する。
