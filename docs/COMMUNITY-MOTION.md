# ログインと主要画面の動き（CP42）

2026-11-09。利用者指定を受けた追加設計。実装・検証結果は後段へ追記する。

## 公開資料の参照

- [Emil Kowalski: You Don't Need Animations](https://emilkowal.ski/ui/you-dont-need-animations)：Linearの制作例、押したときの小さな反応、位置の一貫性、頻繁な操作とキーボード操作で動きを省く判断を参照。
- [IBM Carbon: Motion](https://www.carbondesignsystem.com/building-blocks/foundations/motion/overview)：重要な場面と日常の操作で強さを分け、速く始まり滑らかに落ち着く動きを参照。
- [Linear: How we redesigned the Linear UI](https://linear.app/now/how-we-redesigned-the-linear-ui)：ナビゲーションの位置関係、整列、情報階層を保つ考え方を参照。アニメーションの実測根拠には使わない。

本文と掲載事例の説明を確認した。外部サイトにログインした操作や、そのサイトの動きを実測したとは主張しない。実装の時間・距離は本アプリ向けの設計判断である。

## Before / After / Why

| Before | After（設計） | Why |
|---|---|---|
| ログイン成功で画面が急に置換される | ホームを短いフェードと8px程度の移動で表示 | 入ったことを自然に伝える |
| 主要画面が瞬時に切り替わる | ナビを固定し内容だけ短く表示 | 移動先を追いやすくする |
| 入力操作と演出の区別がない | キーボード操作は即時、設定に応じて移動を省略 | 素早い操作と見やすさを保つ |

実装の制約：認証前後の旧画面を複製・保持しない。左右独立。入力や再取得では再生しない。連続操作を待たせない。transform/opacityのみを主に使い、外部ライブラリー・外部素材・実行時通信は追加しない。

## 実装と確認結果

`useNavigationMotion.ts` で新しい主内容だけをWAAPIで表示。ログイン220ms/8px、主要ナビ170ms/5px、`cubic-bezier(0.2, 0.8, 0.2, 1)`。ログイン送信時の入力方式を保存し、データ到着後に一度消費する。ナビ連打で前の動きを取り消す。キーボード起点・動きを減らす設定では即時表示、ログアウトでは旧DOMを破棄する。

Docker配信 index-i5zm2XlA.js で5段階成功。pointerログインと実測時間、片側の未ログイン維持、keyboardログイン/ナビのアニメーション0、同じタブ再選択で再生なし、連打でcancel、reducedで0、ログアウト後DOM消失、320px/200%、外部通信0・pageerror0を確認。証拠 `community/artifacts/motion/results.json`。独立したheadless環境でありCP27の通常Edge停止の修復確認ではない。
