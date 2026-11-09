# 旅のコレクション API v1

既存 `/api/journal` は変更しない。以下は同じCookie認証、単一オリジン、API no-storeの追加API。

## 読み取り

`GET /api/collection` は本人の保存済み訪問と完了したゲームから計算する。DB更新・ゲーム生成・実績付与は行わない。

```ts
type Collection = {
  definition_version: '1';
  target_id: string | null;
  summary: { earned: number; total: number; completed_sets: number };
  sets: {
    id: 'places' | 'seasons' | 'journeys'; title: string; reward_label: string;
    earned: number; total: number; completed: boolean; earned_at: string | null;
  }[];
  trophies: Trophy[];
};
type Trophy = {
  id: string; set_id: string; title: string; description: string; motif: string;
  status: 'locked' | 'progress' | 'earned'; completed: boolean;
  earned_at: string | null; // 最初の段階を取得した証拠日時
  progress: { current: number; target: number; unit: string };
  stages: { id: string; title: string; target: number; current: number;
            completed: boolean; earned_at: string | null }[];
  missing_conditions: string[];
  next_action: {
    kind: 'visit' | 'puzzle' | 'season'; label: string; spot_id: string;
    season: 'spring' | 'summer' | 'autumn' | 'winter' | null;
    difficulty: 'beginner' | 'advanced' | null;
    available_from: string | null; // JSTのYYYY-MM-DD。訪問/営業の保証ではない
  } | null;
};
```

- `summary.earned` は少なくとも1段階獲得した種類数、全12種類。`status=earned`でも次段階が残る。
- `completed` は最終段階まで達成。`progress` は次の未達閾値（全達成なら最終閾値）に対し `current` を上限で丸める。
- `stages` は全段階を小さい順に返す。各段階の `current=min(実進捗,target)`。取得日時は条件に初めて達した記録日時で、再読込や年度更新では変わらない。
- `stages.id` は `{trophy_id}-{target}`。`motif` は場所4種が `watergate/sakura/coast/conference`、季節4種が `spring/summer/autumn/winter`、続く旅4種が順に `return/coast-seasons/conference-detour/mastery`。画像URLや利用者入力を返さない。
- セットの `earned` は最終段階まで達成した種類数。4種類すべての最終段階達成で称号 `reward_label` を取得。金銭・割引・外部特典を意味しない。
- `next_action` は任意URLを持たない。UIは既存のスポット・難易度・季節選択に反映する。季節待ちも明示し、利用可能になる日までは開始できると表現しない。全段階達成ならnull。

## 固定の12種類

| id | set_id | 名称 | 証拠・段階 |
|---|---|---|---|
| place-watergate | places | 水門の鍵 | 水門の訪問1回 |
| place-sakura | places | 桜社の花守り | 桜社の訪問1回 |
| place-coast | places | 凪の貝殻 | 海辺の訪問1回 |
| place-conference | places | 水都の招待状 | 会議館の訪問1回 |
| season-spring | seasons | 花を運ぶ水路 | 春の水門のゲーム完了1回 |
| season-summer | seasons | 夕涼みの水路 | 夏の水門のゲーム完了1回 |
| season-autumn | seasons | 紅葉を映す水路 | 秋の水門のゲーム完了1回 |
| season-winter | seasons | 灯りをつなぐ水路 | 冬の水門のゲーム完了1回 |
| return-path | journeys | また来た道 | 同じスポットを異なる2 / 3 / 5日に訪問 |
| coast-seasons | journeys | 海辺の四季帳 | 海辺を異なる2 / 3 / 4季節に訪問。年は通算 |
| conference-detour | journeys | 会議館から続く旅 | 会議館の初訪問日より後の異なる1 / 2 / 3日に、会議館以外を訪問 |
| watergate-mastery | journeys | 奥の水路の鍵束 | 上級の水門を異なる1 / 2 / 4季節で完了。年は通算 |

セットは `places:まちのしるし → 水都を歩く人`、`seasons:四季の水路 → 四季をつなぐ人`、`journeys:続く旅 → 水都に通う人`。

同日同スポットの再送は増やさない。別日なら同季節・同年でもvisitsに残る。保存候補・画面操作・ゲーム開始は条件に数えない。場所訪問だけで安産祈願・会議参加・海水浴などの体験完了を推定しない。「別日の訪問記録」であり、独立した旅行や実際の再訪効果を証明するものではない。

## 次に狙う1点

`PUT /api/collection/target` body `{trophy_id: string | null}` → `{target_id: string | null}`。

要認証、CSRF、Origin、JSON。上記固定IDだけ許可（未知ID/URL/余分な項目は422）。未獲得・獲得済みとも選択可能。nullは解除。本人の `collection_preferences` に保存し、復旧コードで同じ手帳へ戻った後も保持する。他者IDは入力に持たない。更新は原子的、同値再送は同じ選択結果。

## 保存と互換性

DB schema v3で `collection_preferences(user_id PRIMARY KEY REFERENCES users(id), trophy_id, updated_at)` を追加。v1/v2から履歴を保持して移行する。SQLite backup APIは全DBをコピーするため追加テーブルも対象。既存の訪問・実績・ゲーム・候補の形式を変更しない。

取得は定義v1と全年度の証拠から導出する。定義v1の条件とIDを後から変更・再利用しない。新条件は新定義として導入し、獲得済みを消すために旧定義を削除しない。証拠DBを失った場合の復元はバックアップに依存する。現地コードの共有や代理入力を識別する仕組みは既存範囲外で、GPSによる実在の検証とは扱わない。
