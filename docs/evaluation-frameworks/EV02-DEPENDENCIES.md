# EV02 依存監査

2026-11-10。実行中のappコンテナの `pip list` から17パッケージを取得し、固定バージョンをpip-auditで照会した。コードやユーザーの保存データは送信していない。npmはfrontendとtest/browserを別々に監査した。証拠は `artifacts/quality/ev02-dependencies/`。

- frontend / browser npm audit：いずれも既知の指摘0。
- Python：アプリ依存への指摘は0だが、コンテナ内pip 25.0.1に12件の報告があった。同じIDの重複を含み、一意のadvisory IDは6件。元の結果は保持した。
- 指摘は悪意あるパッケージの取得・展開等に関するもので、現行アプリから直接悪用できる12個の経路を発見した意味ではない。既存の「アプリ依存だけ0」という集計から範囲を広げた結果である。
- Dockerfileでpipを26.2へ固定更新してから依存を導入する。取得元：[PyPIの公式リリース](https://pypi.org/project/pip/26.2/)。修正版候補は監査結果のfix_versionsから選んだ。
- 修正後の隔離イメージ `kou-community-app:ev02` をビルドし、稼働コンテナから17パッケージを再取得した。pip 26.2を確認し、pip-audit再照会は既知の指摘0。証拠は `runtime-after-packages.json`、`runtime-after-requirements.txt`、`python-runtime-after.json`、`python-after.log`。指摘0はこの時点のPython依存照会範囲に限る。

OSパッケージ全体の脆弱性検査や侵入試験を行ったという記録ではない。pip-auditのキャッシュ読取警告は出たが、照会結果のJSONは生成されている。
