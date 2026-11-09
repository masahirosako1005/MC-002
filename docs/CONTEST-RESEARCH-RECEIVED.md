# クラウド大会調査の受領記録（照合前）

取得日：2026-11-09。クラウド作業「AI大会比較調査報告」から取得。以下は調査担当の報告であり、本プロジェクトの主担当による全件出典照合は未完了。主対象31・関連19という件数は報告値で、検証済み件数とは区別する。取得上限によりレポート末尾の適用提案は未取得。50行の大会表を含む取得範囲を保存し、採用する事実を別途確認する。

今回に取り入れる価値が高いのは、**再訪したくなる独自の体験を、短い操作で実現し、その設計と検証を説明すること**です。受賞作品の外部サービス構成を移植する必要はありません。

調査では、**主対象31大会、関連19大会、計50大会**を一次資料まで追跡しました。ただし、受賞主体・賞まで確認できた結果比較の有効件数は**42大会（主対象23、関連19）**です。残り8大会は資料不足として分離しました。**AIを開発手段に使う主対象だけで50大会という目標には19大会不足**しており、関連大会を加えて達成扱いにはしていません。

**調査条件と読み方**

- 対象期間：2024年11月9日～2026年11月9日。開催・応募期間が重なる大会、または期間内に結果発表された大会を採用。
- 主対象：AIによるコーディング・設計・開発支援を競技の中心または明示された参加条件にする大会。AIアプリ開発も兼ねる場合はこちらを優先。
- 関連：AIアプリ・エージェントの開発が主題で、AIによる開発自体を必須と確認できない大会。
- 部門・地域賞・受賞作品は別大会として数えません。独立した日程の別開催回は各1大会です。
- 英語・日本語を中心に、中国語・韓国語・スペイン語・ポルトガル語でも探索。公式サイト、主催者管理のDevpost、公式ブログ・SNS、主催大学・運営者の報告を確認しました。世界全体の網羅的な母集団ではありません。
- 表の「評価理由」は主催者・審査員の公表内容です。「特徴」は公式紹介・作者の公開説明・掲載画面から確認できる内容で、実装性能の独立検証ではありません。「適用案」は私の推論です。
- 「未確認」は今回の調査で確認できなかった意味であり、非公開と断定するものではありません。公開デモはリンク・掲載画面・操作説明を調べましたが、全動画の通し視聴やアプリの実機試験は実施していません。

| 確認段階 | 主対象 | 関連 | 合計 |
|---|---:|---:|---:|
| 一次資料まで追跡した大会 | 31 | 19 | 50 |
| 受賞主体・賞を確認し、結果比較に採用 | 23 | 19 | **42** |
| 結果の確認が不足し、結果比較から除外 | 8 | 0 | **8** |

以下の表では上位作品を抜粋しています。全受賞作品の一覧ではありません。

**主対象：結果比較に採用した23大会**

| ID・大会／一次資料URL | 開催・応募期間／国・地域／主催 | ルール・審査基準 | 上位作品・賞 | 公表された評価理由 | 公開資料で確認できる特徴 | 今回への適用案〈推論〉 |
|---|---|---|---|---|---|---|
| A01 [World’s Largest Hackathon presented by Bolt](https://worldslargesthackathon.devpost.com/) | 2025/5/30～6/30／世界・オンライン／StackBlitz・Bolt | Boltを主要な開発手段に使用。影響、アイデア、技術実装、デザイン・UX | **Tailored Labs：総合優勝**、Weight Coach：2位、KeyHaven：3位 | 個別の比較採点・選出理由は未確認。公式記事は機能を紹介 | 動画編集、食材からの献立、API鍵管理という具体的な作業を一貫した体験にする | 「観光地検索」より「前回の続きから次の訪問を決める」作業に絞る。 |
| A02 [Code with Kiro](https://kiro.devpost.com/) | 2025/7/14～9/15／世界・オンライン／Kiro | Kiro利用、公開コード、開発過程の説明。価値、実装、独創性 | **Upload Drive-In：1位** | 個別講評は未確認 | 作者説明では、利用者向けの簡単なアップロード操作と、管理者向け設定を分離。Dockerを使った開発環境 | 旅行者の操作を簡単にし、データ管理・設定の複雑さを裏側に収める。 |
| A03 [Kiroween 2025](https://kiroween-2025.devpost.com/) | 2025/10/31～12/5／世界・オンライン／Kiro | Kiroで動くアプリを開発。価値、Kiro活用、創造性。公開コードと3分デモ | **InteractionKit：総合1位** | 個別講評は未確認 | ジェスチャー操作のゲーム・アプリ制作を支援。Python、MediaPipe等を使用 | 奇抜な見た目だけでなく、操作そのものが体験の意味につながる独自性を検討。 |
| A04 [AWS Game Builder Challenge](https://awsdevchallenge.devpost.com/) | 2024/11/1～2025/1/14※／世界・オンライン／AWS | Amazon Qによる開発・最適化とAWSサービス利用が必須。実装、独創性、UX等の賞 | **Farm, Build, Fight：最優秀ゲーム**、Blitzer：2位、Dual Knights：3位 | 公式紹介は資源管理と戦闘の組合せ、クラウド連携等を称賛。個別点数は未確認 | 複数のゲーム要素を遊べる体験に統合 | 再訪の収集・達成要素は、訪問目的につながる範囲で採用する。 |
| A05 [AWS AI Hackathon Hong Kong](https://aws-hong-kong-hackathon.devpost.com/) | 2025/8/15～9/30／香港／AWS Hong Kong | Q DeveloperまたはKiro必須。業務価値、実装、独創性。公開コード・3分デモ | **HAECO Bay Management System：Grand Prize** | 個別講評は未確認 | 航空機整備区画の制約を定義し、配置案と日程を可視化。手動変更も可能 | 滞在時間・移動距離・既訪問を明示的な制約として扱い、提案後に編集できるようにする。 |
| A06 [Lovable AI Showdown](https://aishowdown.lovable.app/) | 2025/6/14～16／世界・オンライン／Lovable、各モデル提供社 | Lovableで開発し、プロンプトの90％超を一つのモデルに集中。品質、デザイン、機能、有用性 | **RateSmart：OpenAI枠、Pixelflow：Anthropic枠、Talki：Gemini枠**。各$10,000 | 個別講評は未確認。総合優勝は今回の確定記録から除外 | レビュー管理、無限キャンバス、会話練習という異なるUI | 同じ推薦機能でも、旅の記憶を扱う操作形式で差別化する。 |
| A07 [Lovable $40k Build Competitionの結果](https://www.linkedin.com/posts/lovable-dev_we-hosted-a-40k-lovable-build-competition-activity-7315280476200419328-yBg5) | 2025年春／オンライン／Lovableほか。正確な応募始終日は未確認 | Lovableによる制作。部門別表彰。詳細配点は未確認 | **Stardust Analytics：総合優勝$10,000**、SkillStep：Best Startup、Dream Catcher：Best Website | 個別講評は未確認 | 分析製品・起業案・Web表現を別の強みとして表彰 | 自作品の主な強みを定め、発想・UI・説明を同じ価値に向ける。 |
| A08 [Replit Agent 4 Buildathon](https://buildathons.replit.app/agent-4-buildathon) | 2026/3/24～4/9、結果4/17／世界・オンライン／Replit | 3週間で探索、MVP、公開へ進む。週次提出あり。過去回の完全な配点は未確認 | **The Hive：Overall Winner表示** | 個別講評は未確認 | ハードウェア学生の制作記録・競技・コミュニティを統合。週次賞と総合賞は同一大会内 | 動いた最終画面だけでなく、改善の履歴を説明できるようにする。 |
| A09 [Replit 10 Year Buildathon](https://buildathons.replit.app/replit-10-year-buildathon) | 2026/5/2～3の24時間／世界・オンライン／Replit | Replitで制作。過去回の詳細配点は未確認 | **Modal Literacy For Deaf：総合優勝**、Paper Trail：2位、Meeting Bingo：3位 | 優勝作は導入体験、アクセシビリティ、画面を支える個人的な背景を評価 | 特定の学習者に合わせた識字支援。家族の情報整理や会議ゲームも上位 | 片手操作・読みやすさ・初回導入を、対象旅行者に合わせて設計する。 |
| A10 [Replit Designathon](https://buildathons.replit.app/replit-designathon) | 2026/8/4～11／世界・オンライン／Replit | 第一印象3倍、デザイン2倍、機能1倍、制作過程公開0.5倍 | **The Dictionary of Invisible Feelings：優勝**、Learn coding & electronics：2位、Eastern Canada Symposium：3位 | 優勝作の独自の概念、作り込み、穏やかな流れ。部門賞では導入体験や制作過程の説明も評価 | 言葉にしにくい感情から辞書に入る。独自性と落ち着いた操作を両立 | 「前回の旅で残った気持ち」から再訪先を探す入口を検討。 |
| A11 [Built with Opus 4.6](https://cerebralvalley.ai/e/claude-code-hackathon) | 2026/2/10～17／世界・オンライン／Anthropic・Cerebral Valley | Claude Codeで1週間制作。Claudeチームが審査。詳細配点は未確認 | **CrossBeam：1位**、Elisa：2位、PostVisit.ai：3位 | 個別の審査員講評は未確認。公式記事は当事者の課題と制作過程を紹介 | 許認可書類の整理、子ども向け視覚IDE、受診後支援。Elisaのテスト数は作者説明 | 再訪に詳しい利用者の困り事を起点にし、AI生成コードの検証責任を持つ。 |
| A12 [Built with Opus 4.7の結果](https://claude.com/resources/articles/meet-the-winners-of-built-with-opus-4-7-claude-code-hackathon) | 2026/4/21～28／世界・オンライン／Anthropic・Cerebral Valley | Claude Codeによる制作。詳細配点は未確認 | **Medkit：1位**、Wrench Board：2位、Maieutic：3位 | 個別の比較採点は未確認 | 医療練習、基板修理、コード理解教育。仕様・責務の分離や検証過程を紹介 | React画面、Pythonの推薦ロジック、保存処理を責務で分ける。 |
| A13 [Claude Opus 4.8 Build Day](https://claude.com/resources/articles/meet-the-winners-of-our-claude-opus-4-8-build-day-hackathon) | 2026/6/13、12時間／米国SF／Anthropic | Opus 4.8で動くデモを制作。詳細配点は未確認 | **Tekton：1位**、Sim Francisco：2位、Custom Universe：3位 | 個別講評は未確認 | Tektonは歴史建築の3D部材と根拠資料を結ぶ。検証工程は作者説明 | 観光解説に出典と更新日を付け、事実と復元・推測を区別する。 |
| A14 [Vibe Code-a-thon](https://vibe-coding-hackathon.devpost.com/) | 2025/5/3／カナダ・オタワ／AI Tinkerers | AI開発ツールで制作。「動く」「UIが使いやすい」を明記。2～3分発表 | **FocusFriend：Best AI Agent**ほか | 個別講評は未確認 | 集中支援。公開作品ページにReact・Python等を記載 | プレゼンだけでなく、再訪先選択から保存までの動作を見せる。 |
| A15 [HACKATHON VIBE CODING AI 2026](https://news.neoscorp.jp/news-vn-hackathon-vibecoding/) | 2026/3/24～27・30／ベトナム／Neos Vietnam | 完成度25、開発プレイブック25、AIエンジニアリング20、創造性15、発表15 | **Office zombies「資産一元管理システム」：優勝** | 実用的な一連の機能、実装力、戦略的AIワークフロー、再利用可能な開発過程 | 購入から廃棄までの状態を追跡 | 「発想→設計→生成→検証→修正」を具体例付きで記録する。 |
| A16 [HackIndia Vibe Coding Hackathon 2026の結果](https://hackindia.org/news/vibe-coding-hackathon-2026-winners-announced-mandimind-ai-takes-the-crown) | 2026年6月、結果6/20／インド・オンライン／HackIndia・Sharp Economy | AI開発利用20、課題20、使いやすさ12、配備14、コード14、複雑性12、理解8 | **MandiMind AI：1位91点**、CogniFlow：2位89点、RoadSense AI：3位87点 | 優勝作は課題・AI利用満点、コード14/14。動くデモ、公開データ、実装を評価 | 農家の市場判断、分析、道路リスクを具体的な対象者に提供 | 使用技術数より、正しく動く証拠・対象者・操作性を説明する。 |
| A17 [Bring Your Vibe](https://forum.decentraland.org/t/dcl-regenesis-labs-bring-your-vibe-hackathon-news-announcements/24669) | 2025/10/13～11/9、制作10/15～27／世界・オンライン／DCL Regenesis Labs | AIツールを少なくとも1つ使用し、DCL Worldと制作コンテンツを提出。雰囲気等を審査 | **Ghost Town：1位**、Fever Dream：2位、7 Days in Hell：3位 | 個別講評は未確認 | 空間体験とテーマを統一。制作過程の公開も要件 | 土地の記憶・季節・物語を、画面と操作の共通テーマにする。 |
| A18 [Bolt Vibe Coding Game Jam 2025](https://vibejam.com/2025/) | 2025年4月／世界・オンライン／Pieter Levels | 当該年アーカイブではAI制作80％以上。無料、Webですぐ遊べる、ログイン不要 | **The Great Taxi Assignment：金**、Vibeware：銀、Vector Tango：銅 | 個別講評・配点は未確認 | 入口の待ち時間・登録を減らす競技条件 | アカウント作成前に、再訪の価値が分かる体験を開始できるようにする。 |
| A19 [ISM Student Vibecoding Hackathon](https://www.ism.lt/en/inside-lithuanias-largest-vibecoding-hackathon/) | 2025/11/24～28／リトアニア・ビリニュス／ISM大学 | AIで動くアプリを制作。予選・Demo Day。詳細配点は未確認 | **FocusAI：1位**、Tailysis：2位、KineziAI：3位 | 審査員の個別講評は未確認 | 仮想ユーザーでの企画検討、ペット状態の把握、専門家が関与する運動支援 | 仮想ユーザー評価を実利用者の評価と混同せず、実際の旅行者から反応を得る。 |
| A20 [OpenAI Build Week](https://openai.devpost.com/) | 2026/7/13～21／世界・オンライン／OpenAI | CodexとGPT-5.6で制作。実装、デザイン・UX、影響、アイデア | **Second Voice、veTriage、Echo Canvas、Mechanica：各部門1位**。1大会として集計 | 個別の比較点数は未確認。公式紹介は具体的な利用課題と設計判断を説明 | 利用者の確認、決定的な計算とAIの役割分担、歴史情報の出典表示 | 保存・推薦順位・所要時間計算は検証可能にし、観光情報の確実性を表示。 |
| A21 [AI Dev Days Hackathon](https://github.com/Azure/AI-Dev-Days-Hackathon) | 制作2026/2/10～3/15／世界・オンライン／Microsoft | Copilotによる開発支援を明記。実装、エージェント設計、影響、UX・発表、部門適合を各20％ | **Quipu、PRism：二つのGrand Prize** | 個別の詳細採点は未確認 | PRismは変更のリスク説明、Quipuは自治体向け災害兆候の整理 | テスト結果を合否だけで終えず、残るリスクを説明する。 |
| A22 [NYU Vibe Coding Hackathon 2025](https://nyuvibecode.vercel.app/) | 2025年10月、締切10/24・31／非同期オンライン／NYU関係運営者 | LLM必須、手動編集禁止。機能、UX、影響、プロンプト、可読性各20点 | **Language Game〔Striped BearZ〕：Launch首位、Pluto：Build首位、Mind Spark〔Sparrows〕：Spark首位** | 個別講評は未確認。数値得点は非公開方針 | プロンプト、ソース、性能報告、1分デモを要求。例外処理・文書と実動作の一致も審査 | コード可読性と例外処理を独立して評価し、動かない機能を成果に含めない。 |
| A23 [Hackathon Vibe Coding 2025／Vibe Coding LATAM](https://rex-labs.lovable.app/blog/45-prototipos-con-ia-en-10-horas) | 2025/10/18、10時間／チリ発オンライン／Vibe Coding LATAM・REX Labs | AIで動く試作品を制作。完全な配点表は未確認 | **Apoyo Comunitario Chile：1位**、Culture Pulse：2位、PersonUp：Buk課題賞 | 主催者の振り返りでは、狭い課題を一連の動作として解決し、実演できた点 | 実在する利用課題を持ち込み、制作範囲を絞る | 「再訪先を一つ決めて保存する」主要動線をまず完成させる。 |

※A04は開始日が対象期間前ですが、応募・結果が対象期間に重なります。

**主対象：結果比較から除外した8大会**

開催・規則の資料は参考になりますが、ここから受賞傾向や勝因を導いていません。

| ID・大会／一次資料URL | 期間／地域／主催 | 確認できた規則・評価 | 上位作品・賞・評価理由の確認状況 | 特徴と今回への適用案〈推論〉 |
|---|---|---|---|---|
| A24 [AWS Global Vibe 2025](https://builder.aws.com/content/2vps1wpyQtzpdWPvj8yJ4IqxyFP) | 2025/10/15～12/1／世界・オンライン／AWS | Q Developer・KiroによるAI開発。複数トラック | 公式募集は確認。DoraHacks結果ページ取得失敗。受賞比較から除外 | 開発過程を含む制作競技として参考。サービス構成の転用はしない。 |
| A25 [Replit Mobile App Buildathon](https://mobile-buildathon.replit.app/) | 2026/1/15～2/13／世界・オンライン／Replit | Replitでモバイルアプリを作りTestFlightへ。完全な審査表は未確認 | **SpookSeek ARに作者の受賞申告あり**。公式の賞・順位対応を確定できず除外 | 公式制作紹介はカメラ・動き・触覚と実機での不具合修正を説明。スマホ固有の使い方と実機確認は参考になる。 |
| A26 [Cursor Vibe Jam 2026](https://vibejam.com/) | 2026/4/1～5/1／世界・オンライン／Pieter Levels | コード90％以上AI生成。無料、登録不要、重い読み込みを避ける | 作品データと規則は確認。今回取得した資料では最終受賞対応を確定できず除外 | 初回体験の速さを重視。観光アプリでも起動時の大きな画像・3D読み込みを抑える。 |
| A27 [Sustainable Living Lab Vibe Coding Hackathon](https://sll-vibe-coding-hackathon.devpost.com/) | 2025/9/17～18／オンライン／Sustainable Living Lab | Cursor・Lovable等で持続可能性の課題を解く。公開審査欄は発表の構成・伝達 | ギャラリーは確認したが受賞表示を確定できず除外 | 問題・利用者・効果・ロードマップの説明構成は参考。掲載作品を受賞作と扱わない。 |
| A28 [Rio AI Hackathon／HackRio](https://rio-ai-hackathon.devpost.com/) | 2025/11/7～8表記／ブラジル・リオ／Quest.eduほか | 課題、事業・発表、ツール活用、技術品質。2分デモ等 | ギャラリー未公開表示。上位作品・理由未確認 | 対象者と短いデモの明確化は参考。開催ページの予定賞を受賞実績に換算しない。 |
| A29 [AI Collective × Lovable × Roam](https://the-ai-collective-hackathon.devpost.com/) | 2025/6/14／米国・カナダ＋オンライン／AI Collective等 | Lovable内で制作、外部インフラ禁止、5時間。短い紹介・デモ提出 | ギャラリーは確認。優勝作の確定に至らず除外 | 制約内で完結させる競技として参考。ただしLovable内完結は今回の実行時自立性とは異なる。 |
| A30 [Manus AI × AI Crafters Vibe Coding Hackathon](https://events.manus.im/es-419/events/vibe-coding-hackathon-by-manus-ai-x-ai-crafters) | 2025/7/4／モロッコ・カサブランカ／Manus・AI Crafters | 2時間制作後、メンター選抜、審査員・観客が選出 | 開催・表彰実施は公式報告で確認。作品名、賞対応、配点未確認 | 短時間で他人に伝わる実演を作る点のみ参考。受賞要因分析には使用しない。 |
| A31 [京畿気候Vibe Coding Hackathon](https://second-team.com/hackathon/climate-gg) | 2025/12/13／韓国・京畿道／京畿道・道議会、運営SecondTeam | Claude Code。コード・配備URL・セッション記録提出。人間とAIの混合審査 | 実施報告を確認。上位作品・賞対応未確認 | プロンプト、コード品質、創造性を併せて見る方式。開発記録の提出設計に応用できる。 |

**関連事例：AIアプリ・エージェントを作る19大会**

AI開発支援ツールを使った参加者がいても、それだけでは主対象に移していません。

| ID・大会／一次資料URL | 開催・応募期間／国・地域／主催 | 審査基準・条件 | 上位作品・賞 | 公表された評価理由 | 公開資料で確認できる特徴 | 今回への適用案〈推論〉 |
|---|---|---|---|---|---|---|
| B01 [Chrome Built-in AI Challenge 2024の結果](https://developer.chrome.com/blog/ai-challenge-winners) | 2024/10/1～12/3※／世界・オンライン／Google | 機能、目的、内容、UX、技術実行。Chrome組込みAI使用 | **WP on-device AI assistant：実用Webアプリ賞、Mochi：実用拡張賞** | 実際の課題、有用性、使いやすさ、技術面を評価 | 端末内文章支援、読みにくい文章の調整 | 外部依存なしの価値を、プライバシーと利用しやすさで説明する。 |
| B02 [Chrome Built-in AI Challenge 2025](https://googlechromeai2025.devpost.com/) | 2025/9/9～10/31／世界・オンライン／Google | 機能、目的、内容、UX、技術実行。組込みAI等 | **AAC Board AI：Most Helpful Web App、Trail：Best Hybrid Web App** | AACは意思伝達支援、Trailはネットなしの探索支援。部門評価の説明あり | AACは私的・オフラインな文章支援。Trailはハイブリッド方式でオフライン利用を支援 | 「オフライン対応」と「初回から外部依存なし」を区別して実証する。 |
| B03 [ADK Hackathon](https://googlecloudmultiagents.devpost.com/) | 2025/5/12～6/23／世界・オンライン／Google Cloud | 実装50％、独創性30％、デモ・文書20％。複数エージェント | **SalesShortcut：Grand Prize** | 個別採点は未確認。公式紹介は販売業務を連続して扱う構成を説明 | 見込み客調査から提案・連絡までの業務を統合 | 入力→推薦→比較→保存を分断せず、全体の完結性を見せる。 |
| B04 [GKE Turns 10 Hackathon](https://gketurns10.devpost.com/) | 2025/8/18～9/22／世界・オンライン／Google Cloud | 実装40％、デモ・発表40％、独創性20％。既存アプリへ独立コンポーネント追加 | **The cart-to-kitchen AI assistant on GKE：Grand Prize** | 個別採点は未確認 | 買物かごの内容から料理を提案。既存のデータを次の行動へ結ぶ | 前回の訪問記録から、次に楽しめる行動を提案する。 |
| B05 [ElevenLabs Worldwide Hackathon](https://elevenlabs-worldwide-hackathon.devpost.com/) | 2025/2/22～23／世界・複数会場＋オンライン／ElevenLabs・a16z等 | 音声AI・エージェント制作。完全な配点は今回未確認 | **Gibberlink：世界最優秀、Hugo Tour Guide：オンライン1位** | Gibberlinkは印象的なデモに審査員が全員一致。Hugoは機能豊かな位置対応の旅行体験を称賛 | 経路、現地解説、質問対応をまとめる旅行ガイド | 旅行者の状況に合う一連の体験と、印象に残る短い実演を作る。 |
| B06 [第1回 AI Agent Hackathon with Google Cloud](https://zenn.dev/hackathons/2024-google-cloud-japan-ai-hackathon?tab=projects) | 2024/12/19～2025/2/10／日本／Zenn、Google Cloud協賛 | 独創性、課題・解決策、実現性。コード、構成図、3分デモ等 | **eCoino：最優秀、Manabiya AI：2位、社内のぞき見新聞：3位** | 個別の受賞理由は今回未確認 | 利用者・課題・構成・動作を一組の提出物として要求 | 同じ構成で説明資料を組み、画面だけに評価を委ねない。 |
| B07 [第2回 AI Agent Hackathon with Google Cloud](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol2?tab=projects) | 2025/4/14～6/30／日本／Zenn | 独創性、課題・解決策、実現性 | **FlatJam：最優秀、学校だよりAI：2位、Vibe Planning：3位** | FlatJamは初心者に合うUIと相談のしやすさ。学校だよりAIは現場の反応。Vibe Planningは精度・性能の測定と改善 | 音楽初心者への選択支援、教師の業務、旅行計画を具体化 | 再訪者の選択負担を減らし、推薦と操作の改善を数値で説明する。 |
| B08 [第3回 AI Agent Hackathon with Google Cloud](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol3?tab=projects) | 2025/8/5～9/24／日本／Zenn | 課題の新規性、解決策の有効性、実装品質・拡張性 | **フクシア：最優秀**。PawMate、言の葉、RouteKeeperAI等：優秀賞 | フクシアは現場理解とテストまでの実行。言の葉は人間が介入できる実用性 | 専門業務、行動根拠の可視化、利用者の判断余地 | 自動推薦を押し付けず、理由確認・差し替え・取消を用意。 |
| B09 [第4回 Agentic AI Hackathon with Google Cloud](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol4?tab=projects) | 2025/12/10～2026/2/15／日本／Zenn | 課題の新規性、有効性、実装品質・拡張性 | **Anatom-AI：最優秀**。Bananacraft、KOTOWARI Link、BrickQuest：優秀賞 | Anatom-AIは美しいUI、認知負荷を下げる対話。BrickQuestは物理検証・改善ループと体験の一貫性 | 複雑な対象の視覚化、検証結果を体験に反映 | 情報量を増やすより、再訪の判断に必要な差分を見せる。 |
| B10 [Microsoft Agent Hackathon powered by TED](https://zenn.dev/hackathons/microsoft-agent-hackathon-2026?tab=projects) | 2026/4/7～6/18／日本／クラスメソッド、東京エレクトロンデバイス協賛 | 業務影響、アプローチ、完成度・実現性。実務で動くことを重視 | **越見波エージェント：企業最優秀、Agentic Gig-Flow：個人最優秀** | 現場の課題、完成度、業務を簡単にする着眼点 | 異常の把握、発注から記帳までの一連の処理 | 訪問記録から次の計画まで、同じデータが自然に引き継がれる設計にする。 |
| B11 [AWS AI Agent Global Hackathon](https://aws-agent-hackathon.devpost.com/) | 2025/9/8～10/22／世界・オンライン／AWS | 技術50％、価値20％、創造性10％、機能10％、デモ10％。再現性を明記 | **EcoLafaek：1位** | 個別講評は今回未確認 | 環境保護のモバイル・管理画面・バックエンドと構成文書を公開 | Dockerからの起動と同じ結果の再現を、実装力の証拠にする。 |
| B12 [Gemini 3 Hackathon](https://gemini3.devpost.com/) | 2025/12/17～2026/2/9／世界・オンライン／Google DeepMind | 実装40％、影響20％、独創性30％、デモ10％ | **Globot：Grand Prize** | 個別講評は今回未確認 | 公開資料では地図、複数役割、ログ、人間の確認を備える物流リスク画面 | 推薦の根拠と処理状態を利用者が理解できるようにする。 |
| B13 [Gemini Live Agent Challenge](https://geminiliveagentchallenge.devpost.com/) | 2026/2/16～3/16／世界・オンライン／Google Cloud | 独創性・マルチモーダルUX40％、実装30％、デモ30％。例外処理を明記 | **ORION：Grand Prize、Wand：UX賞、JohnKeats.AI：技術・設計賞** | Wandは割込みと視覚文脈の自然さ、JohnKeats.AIは堅牢で整ったバックエンド | 音声・視覚を操作の文脈に統合 | 入力途中の変更、キャンセル、処理失敗からの復帰を体験として設計。 |
| B14 [OpenAI Open Model Hackathon](https://openai2025.devpost.com/) | 2025/8/5～9/11／世界・オンライン／OpenAI・各協賛者 | gpt-oss活用、デザインと利用者の安全、影響、独創性 | **RoboChef：Best Overall、Memory Palace：Best Local Agent＋Best of Humanity** | 個別採点は未確認。公式発表は各作品の価値と仕組みを説明 | Memory Palaceは写真・映像・音声をローカルに保ち、記憶を物語として振り返る | 前回の旅の記録を本人の端末に保持し、再訪のきっかけにする。 |
| B15 [NVIDIA NeMo Agent Toolkit Hackathonの結果](https://developer.nvidia.com/blog/hackathon-winners-bring-agentic-ai-to-life-with-the-nvidia-nemo-agent-toolkit/) | 2025年、2週間。結果7/17／オンライン／NVIDIA。正確な始終日は未確認 | 現実への適用、技術実行、エージェント活用 | **Route Optimization Agent：1位、OpenCodeReview：2位、Travel Planner and Experience Agent：3位** | 制約を扱う経路計画、モデル交換可能性、旅行機能の豊富さ等を公式紹介 | 旅行作品にはAPI障害時のローカル代替DB、記憶、地図 | 今回は代替機能にとどめず、同梱データを通常経路として設計する。 |
| B16 [GitLab AI Hackathon](https://gitlab.devpost.com/) | 2026/2/9～3/25／世界・オンライン／GitLab、Google Cloud・Anthropic協賛 | 技術、デザイン、影響、アイデア。開発工程を支援するエージェント | **LORE：Grand Prize、GraphDev：Anthropic Grand Prize** | LOREは製品らしい完成度と43テストを称賛。GraphDevはデモとUX、変更影響の理解を評価 | 知識の循環防止、変更影響の可視化、検証を設計に組み込む | テストの件数ではなく、どの故障・境界条件を防ぐかを示す。 |
| B17 [Agent Academy Hackathonの結果](https://devblogs.microsoft.com/powerplatform/agent-academy-hackathon-winners/) | 2026/5/12～6/2／世界・オンライン／Microsoft | Copilot Studioで制作。学習段階別審査。完全な配点表は今回未確認 | **Performance Development Assistant：Recruit 1位、VendorGuard：Operative 1位** | 前者は技術実行9/10。VendorGuardは大会最高得点と公表 | ルールをデータ化。確認・人間への引継ぎを備える作品も掲載 | データ削除・インポート等の重要操作は確認と復旧方法を持たせる。 |
| B18 [Liquid AI Hack01](https://www.liquid.ai/blog/hack01-hack-the-edge-take-the-dare) | 2025年、結果8/22／オンライン／Liquid AI。正確な始終日は未確認 | 端末内AIがテーマ。完全な配点表は未確認 | **Liquid Lexify：Judges’ Choice、Knight Night：Audience Choice** | Lexifyは利用者の制御と端末内完結、Knight Nightは習慣改善とプライバシーを評価 | ローカル文章支援、第三者へ共有しない利用状況管理 | 「旅行履歴が外へ出ない」を、機能と設計図で説明する。 |
| B19 [Liquid AI Hackathon in Tokyoの主催者発表](https://www.linkedin.com/posts/liquid-ai-inc_our-first-in-person-liquid-ai-x-weights-activity-7391475739155517440-bmKR) | 2025/10/11～12／日本・東京／Liquid AI・Weights & Biases等 | LFMを使い、日本向け課題で能力を実証 | **SafeGuide：1位・Gold、AI Bike：2位** | 詳細な個別採点は未確認 | SafeGuideは接続がなくても利用できる防災案内。受賞企業も日程と作品を公表 | 接続不能時に何ができるかを、実際の制約条件の下で示す。 |

※B01も開始日が対象期間前です。**開始日が期間内にある大会だけ**に限定する場合、A04・B01を除いて追跡48大会、結果比較40大会になります。

**10大会前後の中間知見から、最終的に残った判断**

中間段階で見えた「動くこと・分かりやすさ・具体的な課題・開発過程の説明」は、その後の資料でも参考になる観点でした。ただし、次のように精度を上げて解釈する必要があります。

| 要因 | 公開資料による裏付け | 今回に使える判断 | 言えないこと |
|---|---|---|---|
| 対象者に合う独自UI | FlatJamは初心者の知識負担とUI選択を講評。Anatom-AIは認知負荷を下げる体験を評価 | 見慣れない画面を作るより、再訪者に合う入口・選び方を作る | 独自UIだけで勝てるとは言えない |
| 問題から完了までの一貫性 | ネオスは一連の機能と実用性、LATAM運営者は狭い課題を解いて実演した点を評価 | 多機能化より、再訪先決定・保存・再表示を完成させる | 機能が少ないほど高評価になるという因果関係は未確認 |
| 説明も成果物の一部 | ネオスはプレイブック25点。ADKはデモ・文書20％、GKEは発表40％ | 価値、操作、構成、検証を短時間で理解できる提出物にする | 大会間の配点を平均して今回の正解にはできない |
| 測定と改善 | Vibe Planningは精度・性能の測定、学校だよりAIは教師の反応を講評 | 推薦結果と操作の改善を実測で説明する | 公開数値だけで測定方法や一般化可能性は保証されない |
| 工程・設計・テスト | NYUは可読性・例外処理、GitLabはテストや循環防止、AWS Agentは再現性を重視 | 不正入力、保存失敗、空データ、再起動を含む検証を見せる | 受賞した全作品のコードが安全とは言えない |
| ローカル完結の利用価値 | Hack01、SafeGuide、Memory Palace等 | 通信不能への強さ、履歴の保持、プライバシーを利用価値として示す | ローカル方式そのものが受賞を引き起こしたとは言えない |

これらは、審査基準・講評・紹介に繰り返し現れる観点です。**非受賞作品との条件を揃えた比較、審査員別得点、開発時間、既存資産などが不足しており、統計的・因果的な「勝因」にはできません。** また、主催者の製品紹介や作者の制作談は、審査員による評価理由と区別しています。
