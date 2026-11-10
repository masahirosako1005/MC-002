# 見出し用書体 Yuji Mai の出典と同梱

2026-11-10。利用者の筆書きに寄せたタイトル指定に合わせ、**Yuji Mai（佑字・舞）Regular / 400** を導入した。作者の漢字設計は楷書を参考に識別性も考慮したもので、純粋な草書とは説明しない。[公式日本語説明](https://github.com/Kinutafontfactory/Yuji/blob/efec977b14b57c19eb85d468edcfbbad13139e67/README-JP.md)

## 出典とライセンス

- 制作：Kinuta Font Factory / The Yuji Project Authors。書家・片岡佑之の原字による書体。
- 公式 repository：[Kinutafontfactory/Yuji](https://github.com/Kinutafontfactory/Yuji)
- 固定 commit：`efec977b14b57c19eb85d468edcfbbad13139e67`
- 元ファイル：[fonts/ttf/YujiMai-Regular.ttf](https://github.com/Kinutafontfactory/Yuji/blob/efec977b14b57c19eb85d468edcfbbad13139e67/fonts/ttf/YujiMai-Regular.ttf)
- ライセンス：[同じ commit の OFL.txt](https://github.com/Kinutafontfactory/Yuji/blob/efec977b14b57c19eb85d468edcfbbad13139e67/OFL.txt)。SIL Open Font License 1.1。ソフトウェアへの同梱・再配布を認め、著作権表示とライセンスの保持を要求する。フォント単体での販売や作者による推奨を示す扱いはしない。

ライセンスを変更せず公式の全文を同梱した。この版の著作権ヘッダーに Reserved Font Name の指定はない。WOFF2への形式変換は変更版として出典へ記録し、字体名・著作権メタデータを維持した。OS/Office由来の HG行書体・HG正楷書体・游明朝をコピーしていない。

## 同梱ファイルと配信

`community/frontend/public/fonts/yujimai/` に次の3ファイルを保存する。

| ファイル | 用途 |
| --- | --- |
| `YujiMai-Regular.woff2` | 全グリフを残したローカル配信フォント |
| `OFL.txt` | 上流の著作権表示・ライセンス全文 |
| `SOURCE.json` | 固定出典、バイト数、SHA-256、変換ツール、照合結果 |

URL は `/fonts/yujimai/YujiMai-Regular.woff2`。Google Fonts CDN等の外部配信や、実行時のネットワーク取得は使わない。元TTFは同じプロジェクト内で変換と照合を終えてから削除した。フォント導入担当によるCSS/React変更はない。見出しへの適用はフロント担当が行う。

## 変換と検証

開発用 `.venv` の FontTools **4.68.0** と Brotli **1.2.1** を使用。Brotliは変換用に追加し、バックエンドの実行時requirementsへは追加していない。公開資産ディレクトリを一時作業先とし、外部フォルダへフォントを保存していない。

変換は `fontTools.ttLib.woff2.compress(source_ttf, output_woff2)`。subset処理、字形編集、固定タイトルだけへの文字削減はしていない。

| 項目 | 結果 |
| --- | --- |
| 元TTF | 8,496,292 bytes |
| WOFF2 | 4,089,912 bytes（約51.9%削減） |
| グリフ | 9,504、順序と全グリフの座標・輪郭数を照合して一致 |
| Unicode対応 | best cmap 8,013 codepoints、全4 cmap subtableが一致 |
| 文字幅 | 全横組み・縦組み metrics 一致 |
| レイアウト等 | name / GSUB / BASE / post / gasp / OS/2 のテーブルデータ一致 |
| 除去されたテーブル | 空の DSIG（元署名数0）。標準WOFF2変換が除去するもので、グリフ削除ではない |
| 対象見出し例 | 「日帰りを探す」「講の開催」「旅の手帳」、十階級で使用する文字、「N西市」「ログイン」「アカウントを作る」の欠字0 |

元TTF SHA-256：`05d83b65204a5de6fc34c222057fc082f8c6e2e44c05a0d28f4189b3e54c54c2`

WOFF2 SHA-256：`8196c14a9c38184f78d56bfa06a8fc2609793404b9186521caef5e528de0b270`

OFL SHA-256：`ef7c85c72ae94381c8bc4832ae4e6fbabdeafa2bb8a31313cd75dce95a690256`

全グリフ保持は、上流にない希少漢字・絵文字を新しく収録したという意味ではない。利用者が入力する任意のタイトルには既存の日本語フォントへのfallbackを残す。フォントのブラウザー実表示、200%文字拡大、全体画面品質はフロント担当・主担当の統合確認対象であり、この変換検証だけで成功とは扱わない。

## 適用範囲と素材の判断

| Before | After（適用案） | Why |
| --- | --- | --- |
| 見出し全体がOS明朝 | `.wa-title-script` 等の専用指定で短い先頭タイトルだけ Yuji Mai / 400 | 本文・料金・操作・実績数字の読みやすさを維持する |
| タイトル約23pxと広めの字間 | 28〜32px、行高1.3、字間0〜0.02emから実画面で調整 | 筆画を潰さず、狭い画面と拡大でも見出しを読めるようにする |
| OSに書体がある場合だけ筆書き表示 | 同梱WOFF2＋`font-display: swap`＋既存明朝fallback | 外部通信・OS依存を減らし、読み込み中も文字を残す |

既存の巻物は `WaArt.tsx` の編集可能なSVGで、木版風の旅人イラストもローカル資産として存在する。線の硬さや余白の不一致はSVG/CSS側の調整対象にする。タイトルを画像へ焼き付けると拡大・選択・読み上げが難しくなるため、文字の画像化や新しい画像生成は今回の書体導入に使わない。emil-design-engの情報階層・見やすさの考え方を適用し、imagegenは必要性を検討した上で不使用とした。
