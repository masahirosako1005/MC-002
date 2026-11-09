# 大会調査の独立照合・設計への採否

確認日：2026-11-09。対象期間：2024-11-09〜2026-11-09。受領原本は [CONTEST-RESEARCH-RECEIVED.md](CONTEST-RESEARCH-RECEIVED.md)。原本の報告値を、そのまま検証済み件数にはしない。

## 確認範囲と件数

- 受領表50行（A01〜A31、B01〜B19）の出典を照合した。先に確認した10件は保持し、残る40件について公式募集、主催者発表、大会管理下の受賞表示を開いて追確認した。リンクがあるだけでは確認済みにしない。
- **期間内の募集・開催または結果資料を確認できた候補は49件。AIを開発工程の主要手段とする主対象28件、AI製品・エージェント・デザインの関連競技21件。A06の1件は本文取得不能のため不採用・保留。** 「期間内募集の確認」は開催完了の証明ではない。
- **期間内49件のうち、名前のある受賞作品を確認できたのは40件、募集・開催・作品紹介までの確認は9件。** 受賞表示のみの行は賞名・順位・選考理由まで確認した扱いにしない。原本の「主31、関連19、結果42」は、この再分類・再確認値で置き換える。
- 主対象28件には公募・企業内・学生大会が混在する。また「AIを用いて制作することが中心」と「全作品でAIコード生成が必須」は同義ではない。**AI駆動開発の独立した50大会を確認する目標は未達**。主対象だけでは22件不足であり、関連競技や部門賞を加算して埋めない。
- 期間判定は2024-11-09〜2026-11-09に「応募・制作期間が一部重なる、または結果の公表が入る」とした。日付は応募、開催、結果、予定を区別する。開始日だけの集計ではない。
- 独立性は主催、開催回、年、期間で点検した。A06とA29の関係は未解決なのでA06を集計から除いた。残る49行に同一開催回の重複は見つからなかったが、全世界の大会を網羅した標本ではない。
- 設計の直接根拠として採用する10件は下表のまま維持する。追加39件は比較・反証材料。受賞の事実と、その理由についての本PJの推論を分ける。

## 採用する10大会の確認結果

以下の適用判断は本PJの推論であり、受賞の因果要因を証明するものではない。

| ID・大会 | 再確認できた事実 | 留意・修正 | 今回の採用判断 |
|---|---|---|---|
| A01 Bolt 2025 | [公式募集](https://worldslargesthackathon.devpost.com/)は2025/5/30〜6/30。[主催者結果](https://bolt.new/blog/2025-bolt-hackathon-winners)はTailored LabsをGrand Prize、Weight Coach・KeyHavenを続く順位として掲載 | 具体的な動画編集性能は紹介文の主張で独立測定ではない。比較採点・個別選考理由は未確認 | 「訪問記録から次の旅を決める」一連の作業を優先。機能紹介を測定済み効果として借用しない |
| A02 Code with Kiro | [公式募集](https://kiro.devpost.com/)は2025/7/14〜9/15、価値・実装・アイデアを評価。[受賞表示](https://devpost.com/software/upload-drive-in)でUpload Drive-Inの1位を確認 | 原本のDocker活用を成功要因としては採用しない。作者は完全なDockerビルドを今後の簡略化案としても述べており、環境の完成状態は独立未検証 | 利用者の操作と管理の複雑さを分離。今回のDocker再現性は自分たちの実測で示す |
| A03 Kiroween 2025 | [規則](https://kiroween-2025.devpost.com/rules)は応募2025/10/31〜12/5、結果発表予定2026/1/30。[受賞表示](https://devpost.com/software/kiro-interactionkit)でInteractionKitの総合1位を確認 | [審査欄](https://kiroween-2025.devpost.com/)は価値、Kiro活用、品質とデザイン。2025年内に結果が出たと解釈しない。個別講評は未確認 | 水門操作そのものを謎解きにする。見栄えだけでなく操作と意味を結ぶ。カメラ必須ジェスチャーは採用しない |
| A04 AWS Game Builder Challenge | [募集・審査](https://awsdevchallenge.devpost.com/)は2024/11/1〜2025/1/14、実装・独創性・UX。[受賞表示](https://devpost.com/software/fbf-farm-build-fight)はFBF: Farm, Build, Fight!のBest Game | 開始日は対象窓より前。応募期間の重なりで採用。今回確認したのはBest Gameであり、原本の他作品の細かな順位・講評は再確認していない | 正答可能な課題、ヒント、手応えを持つゲームを実装。スポンサーのAWS利用要件は今回のローカル制約に合わず不採用 |
| A15 Neos Vietnam 2026 | [主催者記事](https://news.neoscorp.jp/news-vn-hackathon-vibecoding/)で2026/3/24〜27・30、Office zombiesの資産管理システム優勝を確認。完成度25、開発プレイブック25、AI開発20、創造性15、発表15 | 社内4チームの大会。大規模国際公募と同じ母集団として集計しない。実用的な一連の機能と再利用可能な開発過程は主催者が評価理由として記載 | 実装→測定→修正の履歴、異常系の証拠、起動手順を成果物に残す。配点は今回の公式点に転用しない |
| B07 Google Cloud Japan 第2回 | [主催者結果](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol2?tab=projects)でFlatJam最優秀、学校だよりAI2位、Vibe Planning3位を確認。UIの対象者適合、現場の反応、定量評価による改善がそれぞれ講評にある | AIアプリ競技の関連事例。AIを開発手段とする競技の件数には足さない | 初めての旅行者にも分かる操作、候補選択の時間・誤操作の測定を採用。未実施のユーザー調査結果は作らない |
| B09 Google Cloud Japan 第4回 | [主催者結果](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol4?tab=projects)でAnatom-AI最優秀、BrickQuest優秀賞。認知負荷、検証・改善ループ、一貫した体験を講評 | 原本の応募期限2026/2/15と最終ピッチ2026/3/19は別の段階。募集期間を大会全期間と書かない | 旅のしおり・手帳・次の旅の役割を分離し、情報の量より判断に必要な情報を優先する |
| B14 OpenAI Open Model Hackathon | [募集・審査](https://openai2025.devpost.com/)にモデル活用、デザインと安全、影響、独創性。[公式結果](https://openai2025.devpost.com/updates/37529-and-the-winners-are)でRoboChefのBest Overall、Memory PalaceのBest Local AgentとBest of Humanity | モデルを使う製品の競技。ローカル動作の紹介は実装の独立監査ではなく、無条件に安全という保証にもならない | 履歴を外部送信しない利用価値を採用。ローカル生成AIの追加は今回の再訪目的に必須でないため採用しない |
| B15 NVIDIA NeMo Agent Toolkit | [主催者結果](https://developer.nvidia.com/blog/hackathon-winners-bring-agentic-ai-to-life-with-the-nvidia-nemo-agent-toolkit/)は2025/7/17公開。Route Optimization Agentを1位として紹介 | 正確な開催始終日と全配点は未確認。結果発表日の条件で対象内。制約付き経路計画の紹介を性能の独立検証と扱わない | 往復移動＋滞在＋余裕時間を制約にし、会議に戻れる候補だけを提示。大規模最適化基盤は採用しない |
| B18 Liquid AI Hack01 | [主催者結果](https://www.liquid.ai/blog/hack01-hack-the-edge-take-the-dare)は2025/8/22公開。Liquid LexifyがJudges’ Choice、Knight NightがAudience Choice | 開催始終日、全配点、比較採点は未確認。観客賞と審査員賞を同じ順位に変換しない | 完全ローカルの価値を通信遮断と保存の証拠で説明。「遅延ゼロ」等の紹介表現は自作品の性能に転用しない |

## 全50行の出典照合結果

確認日：2026-11-09。**R**＝作品名と受賞の対応を確認、**G**＝公式大会ギャラリーのWinner表示を確認（順位未確定）、**P**＝募集・開催・作品紹介のみ、**H**＝本文未取得のため採用保留。R/Gも作品の品質や性能の独立検証を意味しない。主＝AI開発中心、関連＝AIアプリ/デザイン等。日付の年を省略した範囲は左端と同年。

| ID・大会 | 分類／判定 | 確認できた期間・公表日 | 公式根拠、受賞／成果、修正・保留事項 |
|---|---|---|---|
| A01 Bolt 2025 | 主／R | 応募2025/5/30–6/30 | [募集](https://worldslargesthackathon.devpost.com/)・[結果](https://bolt.new/blog/2025-bolt-hackathon-winners)。Tailored Labs総合賞。先行10件の確認を維持 |
| A02 Code with Kiro | 主／R | 応募2025/7/14–9/15 | [募集](https://kiro.devpost.com/)・[受賞](https://devpost.com/software/upload-drive-in)。Upload Drive-In 1位。Docker完成を勝因とする原本解釈は不採用 |
| A03 Kiroween | 主／R | 応募2025/10/31–12/5、発表予定2026/1/30 | [規則](https://kiroween-2025.devpost.com/rules)・[受賞](https://devpost.com/software/kiro-interactionkit)。InteractionKit総合1位。名称年と発表年を分離 |
| A04 AWS Game Builder | 主／R | 応募2024/11/1–2025/1/14 | [募集](https://awsdevchallenge.devpost.com/)・[受賞](https://devpost.com/software/fbf-farm-build-fight)。FBFのBest Game。開始日は窓外、応募期間の重なりで採用 |
| A05 AWS Hong Kong | 主／G | 応募2025/8/15–9/30 | [募集](https://aws-hong-kong-hackathon.devpost.com/)はQ Developer/Kiro、価値・実装・革新を評価。[公式一覧](https://aws-hong-kong-hackathon.devpost.com/project-gallery)でHAECO Bay Management SystemにWinner。Grand Prizeの順位対応は保留 |
| A06 Lovable AI Showdown | 未確定／H | 原本2025/6/14–16を未確認 | [元URL](https://aishowdown.lovable.app/)を開いたが本文取得不能。検索断片だけでRateSmart等の受賞・日程を確定しない。A29との関係未解決。期間集計・勝因比較とも不採用 |
| A07 Lovable $40k Build | 主／R | 結果投稿2025/4/8 | [Lovable公式投稿](https://www.linkedin.com/posts/lovable-dev_we-hosted-a-40k-lovable-build-competition-activity-7315280476200419328-yBg5)。Stardust Analytics総合、SkillStep startup、DreamCatcher website。投稿HTMLのdatePublishedを確認。応募日不明、6月のA06と同一視しない |
| A08 Replit Agent 4 | 主／R | 公開大会データ2026/3/24–4/18 UTC | [大会](https://buildathons.replit.app/agent-4-buildathon)・[公式公開結果](https://buildathons.replit.app/api/public/winners?buildathonId=c137b0d5-81b0-424e-9f61-7bf583bee433)。The Hive（旧Engineering Launchpad）Overall Winner。原本4/9との段階差は未確定。週次賞を別大会に数えない |
| A09 Replit 10 Year | 関連／R | 公開大会データ2026/5/2–5/3 UTC | [大会](https://buildathons.replit.app/replit-10-year-buildathon)・[公式公開結果](https://buildathons.replit.app/api/public/winners?buildathonId=c18c51f4-428d-414c-a797-cdf62fd11058)。Modal Literacy For Deaf Students総合賞。Agent開放の施策はあるがAI開発必須規定を確認できず、主から関連へ変更 |
| A10 Replit Designathon | 関連／R | 公開大会データ2026/8/4–8/11 UTC | [大会](https://buildathons.replit.app/replit-designathon)・[公式公開結果](https://buildathons.replit.app/api/public/winners?buildathonId=c60777a2-8f40-4565-8e4e-27021681f438)。Dictionary of Invisible Feelings総合賞。AI開発必須と原本の細かな重みは未確認、関連へ変更 |
| A11 Claude Code Opus 4.6 | 主／R | 結果公開2026/4/20 | [主催者結果](https://claude.com/resources/articles/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon)。CrossBeam 1位、Elisa 2位、PostVisit.ai 3位。Claude Codeで1週間制作。同記事が次の4.7回を明示しA12との別開催を確認。作者のテスト数は独立未検証 |
| A12 Claude Code Opus 4.7 | 主／R | 結果公開2026/6/15 | [主催者結果](https://claude.com/resources/articles/meet-the-winners-of-built-with-opus-4-7-claude-code-hackathon)。Medkit 1位、WrenchBoard 2位。原本の4月応募日程までは再確定せず、結果日で対象内 |
| A13 Claude Opus 4.8 Build Day | 主／R | 開催2026/6/13、結果公開6/17 | [主催者結果](https://claude.com/resources/articles/meet-the-winners-of-our-claude-opus-4-8-build-day-hackathon)。San Franciscoの12時間回、Tekton 1位、SimFrancisco 2位。オンラインのA11・A12と別開催。テスト数の紹介は主催者による性能監査ではない |
| A14 Ottawa Vibe Coding | 主／G | 開催2025/5/3 | [募集](https://vibe-coding-hackathon.devpost.com/)・[公式一覧](https://vibe-coding-hackathon.devpost.com/project-gallery)。AIツールによる制作、FocusFriendにWinner。原本のBest AI Agent賞名との対応は保留 |
| A15 Neos Vietnam | 主／R | 開催2026/3/24–27・30 | [主催者結果](https://news.neoscorp.jp/news-vn-hackathon-vibecoding/)。Office zombies優勝。社内4チームという母集団の違いを保持 |
| A16 HackIndia Vibe Coding | 主／R | 結果公開2026/6/20 | [主催者結果](https://hackindia.org/news/vibe-coding-hackathon-2026-winners-announced-mandimind-ai-takes-the-crown)。MandiMind AI 1位、CogniFlow 2位。1位の公表総点91に対し掲載内訳合計89。デモ加点との関係不明のため91を比較点として採用しない |
| A17 Bring Your Vibe | 主／R | 告知2025/10/13、募集制作10月、結果11月 | [主催者運営記事](https://forum.decentraland.org/t/dcl-regenesis-labs-bring-your-vibe-hackathon-news-announcements/24669)でGhost Town 1位。[規則](https://bringyourvibe.decentraland.org/rules)はAIツール1つ以上、締切10/29。原告知の制作終期10/27と混同せず、AIは構想・モデル制作も可でコード生成必須ではない |
| A18 Vibe Jam 2025 | 主／R | 2025年4月回 | [主催者アーカイブ](https://vibejam.com/2025/)。80%以上AIコード・素材、即時Web起動。Great Taxi Assignment Gold、Vibeware Silver。A26への翌年リンクがあり別回を確認 |
| A19 ISM Lithuania | 主／R | 結果記事2025/12/4（前週の5日間） | [大学主催者記事](https://www.ism.lt/en/inside-lithuanias-largest-vibecoding-hackathon/)。FocusAI 1位、Tailysis 2位、KineziAI 3位。原本の厳密な開始日を推定で補わない。学生教育イベントとして別層 |
| A20 OpenAI Hackathon 2026 | 主／G | 応募2026/7/13–7/21 | [募集](https://openai.devpost.com/)はCodex/GPT活用の制作。[公式一覧](https://openai.devpost.com/project-gallery)にSecond Voice、veTriage、EchoCanvas、MechanicaのWinner。部門と順位の全対応は未確定、4部門を4大会に数えない |
| A21 AI Dev Days | 主／R | 制作2026/2/10–3/15、結果記事5/11 | [Microsoft公式要件](https://github.com/Azure/AI-Dev-Days-Hackathon)にGitHub Copilot活用、審査5項目各20%。[主催者結果](https://techcommunity.microsoft.com/blog/azure-events/announcing-the-ai-dev-days-hackathon-winners/4513528)でQuipuとPRismが各Grand Prize。要件表の発表予定3/25を実発表日と扱わない |
| A22 NYU VibeCode | 主／P | 2025/10/10 workshop、締切10/24・10/31 | [運営サイト](https://nyuvibecode.vercel.app/)はLLM使用、手動コード編集不可。[同サイトからの審査表](https://nyuvibecode.github.io/)は機能・UX等5項目各20点。LanguageGame等の受賞対応は読めず保留。大学全体の公認という追加主張はしない |
| A23 REX Labs Vibe Coding LATAM | 主／R | 開催2025/10/18 | [主催者日付資料](https://rex-labs.lovable.app/prensa)・[大会結果](https://rex-labs.lovable.app/hackathon/vibe-coding-2025)。Apoyo Comunitario Chile 1位、Culture Pulse 2位。原本のブログURLでは本文を取得できず、主催者の別ページで補完 |
| A24 AWS Global Vibe | 主／P | 制作予定2025/10/15–12/1 | [AWS社員による募集記事](https://builder.aws.com/content/2vps1wpyQtzpdWPvj8yJ4IqxyFP)はQ Developer/Kiro中心。[AWSイベント案内](https://startups.aws.com/events/aws-global-vibe-ai-coding-hackathon-2025)でも実在確認。DoraHacks先は取得不可、12/19は発表予定であり実受賞未確認。日程・募集の比較のみ |
| A25 Replit Mobile App Buildathon | 主／P | 公式配信画面の締切2026/2/13 23:59 PST | [大会](https://mobile-buildathon.replit.app/)の公開配信JSに締切を確認。[主催者記事2026/2/20](https://replit.com/blog/building-mobile-apps-on-replit)はFlash NewsとAgentでの制作を紹介。原本1/15開始とSpookseek ARの賞対応は未確認。制作例を受賞例に読み替えない |
| A26 Vibe Jam 2026 | 主／P | 制作2026/4/1–5/1 | [公式募集](https://vibejam.com/)は90%以上AIコード、4/1以降の新規制作。2025回と別条件・別年。閲覧時に受賞作品本文を取得できず勝因比較には不採用 |
| A27 SLL Vibe Coding | 主／P | 掲載期間2025/9/17–9/18 | [公式募集](https://sll-vibe-coding-hackathon.devpost.com/)。AIによる迅速な試作の競技。受賞作品と賞の対応未確認、募集条件のみ採用候補 |
| A28 Rio AI Hackathon | 主／P | 掲載期間2025/11/7–11/8 | [公式募集](https://rio-ai-hackathon.devpost.com/)はLovable等でEdTechを制作。2025年なので下限2024/11/9より後。受賞未確認。6時間制作の記載とサイト掲載期間を区別 |
| A29 The AI Collective | 主／P | 開催2025/6/14 | [公式募集](https://the-ai-collective-hackathon.devpost.com/)で5時間、Lovable使用、4基準各25%。受賞未確認。A06との重複可能性は解消していないためA06を除き、この1行だけ数える |
| A30 Manus × AI Crafters | 主／P | 開催2025/7/4 | [主催者開催報告](https://www.manus.im/events/all/vibe-coding-hackathon-by-manus-ai-x-ai-crafters)。Casablanca、2時間の制作後に審査員・観客が選出。表彰実施は確認したが作品名がなく、名前付き受賞40件には含めない。元URLの移転を補完 |
| A31 Gyeonggi Climate GG | 主／P | 開催2025/12/13 | [運営者報告](https://second-team.com/hackathon/climate-gg)。Claude Code、リポジトリ・セッション記録、AIと人の審査を記載。受賞作品・点数未確認。運営紹介だけでAI審査の妥当性を証明しない |
| B01 Chrome Built-in AI 2024 | 関連／R | 結果公開2025/1/13 | [主催者結果](https://developer.chrome.com/blog/ai-challenge-winners)。WP on-device AI assistant、Mochi等。2024年開始でも結果が窓内。モデルを使う製品の競技でAIコード生成必須ではない |
| B02 Chrome Built-in AI 2025 | 関連／G | 応募2025/9/9–10/31 | [募集](https://googlechromeai2025.devpost.com/)・[公式一覧](https://googlechromeai2025.devpost.com/project-gallery)。AAC Board AI、TrailにWinner。賞種別は未再確定。B01と別年回 |
| B03 ADK Multi-Agent | 関連／G | 応募2025/5/12–6/23 | [募集](https://googlecloudmultiagents.devpost.com/)・[公式一覧](https://googlecloudmultiagents.devpost.com/project-gallery)。Sales ShortcutにWinner。原本のGrand Prize順位対応は保留 |
| B04 GKE Turns 10 | 関連／G | 応募2025/8/18–9/22 | [募集](https://gketurns10.devpost.com/)・[公式一覧](https://gketurns10.devpost.com/project-gallery)。Cart-to-KitchenにWinner。Grand Prize予定表示と実際の賞対応を混同しない |
| B05 ElevenLabs Worldwide | 関連／R | 開催2025/2/22–23、結果2/28 | [主催者結果](https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon)。Gibberlink Global top、Hugo Tour Guide online 1位。[募集](https://elevenlabs-worldwide-hackathon.devpost.com/)の掲載範囲2/21–24と現地開催日を区別。各会場・online賞は1大会の内訳 |
| B06 Google Cloud Japan 第1回 | 関連／R | 応募2024/12/19–2025/2/10、結果3/15 | [主催者結果](https://zenn.dev/hackathons/2024-google-cloud-japan-ai-hackathon?tab=projects)。eCoino最優秀、Manabiya 2位、Internal Times 3位。第2〜4回と別日程 |
| B07 Google Cloud Japan 第2回 | 関連／R | 2025年の第2回結果 | [主催者結果](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol2?tab=projects)。FlatJam最優秀等。先行10件で確認した講評を維持、3作品を3大会と数えない |
| B08 Google Cloud Japan 第3回 | 関連／R | 応募2025/8/5–9/24、結果11/5 | [主催者結果](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol3?tab=projects)。Fuchsia（フクシア）最優秀、PawMate等の部門賞。現場の課題と実装の講評を確認 |
| B09 Google Cloud Japan 第4回 | 関連／R | 応募締切2026/2/15、最終ピッチ3/19 | [主催者結果](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol4?tab=projects)。Anatom-AI最優秀、BrickQuest優秀。先行確認を維持 |
| B10 Microsoft Agent 2026 | 関連／R | 応募2026/4/7–6/18 | [主催者結果](https://zenn.dev/hackathons/microsoft-agent-hackathon-2026?tab=projects)。越見波Agent、Agentic Gig Flowが企業・個人の最優秀。2部門を2大会にしない |
| B11 AWS AI Agent Global | 関連／G | 応募2025/9/8–10/22 | [募集](https://aws-agent-hackathon.devpost.com/)・[公式一覧](https://aws-agent-hackathon.devpost.com/project-gallery)。EcoLafaekにWinner。Q/Kiroの選択肢があることだけでAI開発必須としない。1位対応は保留 |
| B12 Gemini 3 | 関連／G | 応募2025/12/17–2026/2/9 | [募集](https://gemini3.devpost.com/)・[公式一覧](https://gemini3.devpost.com/project-gallery)。GlobotにWinner。モデル活用の製品競技、Grand Prizeの対応未確定 |
| B13 Gemini Live Agent | 関連／G | 応募2026/2/16–3/16 | [募集](https://geminiliveagentchallenge.devpost.com/)・[公式一覧](https://geminiliveagentchallenge.devpost.com/project-gallery)。ORION、Wand、John KeatsにWinner。B12とは別期間・別競技。各順位未確定 |
| B14 OpenAI Open Model | 関連／R | 2025年回の結果 | [募集](https://openai2025.devpost.com/)・[主催者結果](https://openai2025.devpost.com/updates/37529-and-the-winners-are)。RoboChef総合、Memory Palace部門賞。先行確認を維持。A20と別年・別要件 |
| B15 NVIDIA NeMo Toolkit | 関連／R | 結果公開2025/7/17 | [主催者結果](https://developer.nvidia.com/blog/hackathon-winners-bring-agentic-ai-to-life-with-the-nvidia-nemo-agent-toolkit/)。Route Optimization Agent 1位。開催始終日は未確定 |
| B16 GitLab AI Hackathon | 関連／G | 応募2026/2/9–3/25 | [募集](https://gitlab.devpost.com/)・[公式一覧](https://gitlab.devpost.com/project-gallery)。LOREにWinner。開発工程向けAI製品の競技とAI支援で開発する競技を分離。43テストの作者説明を審査員の講評と扱わない |
| B17 Agent Academy | 関連／R | 制作2026/5/12–6/2、結果6/18 | [主催者結果](https://devblogs.microsoft.com/powerplatform/agent-academy-hackathon-winners/)。Performance Development AssistantのRecruit 1位、VendorGuardのOperative 1位。部門別競技、AIアプリ制作の関連例 |
| B18 Liquid AI Hack01 | 関連／R | 結果公開2025/8/22 | [主催者結果](https://www.liquid.ai/blog/hack01-hack-the-edge-take-the-dare)。Liquid Lexify審査員賞、Knight Night観客賞。開催始終日未確定、賞の違いを維持 |
| B19 Liquid AI × W&B Tokyo | 関連／R | 開催2025/10/11–12、主催者発表11/4 | [主催者結果投稿](https://www.linkedin.com/posts/liquid-ai-inc_our-first-in-person-liquid-ai-x-weights-activity-7391475739155517440-bmKR)と[受賞者所属企業の一次発表11/6](https://www.j-com.co.jp/news/info_20251106.html)。SafeGuide Gold。B18オンライン回とは開催地・日付・作品が異なる |

### 読み取り方法と残る限界

- Replit A08〜A10は通常ページがJavaScript描画のため、サイト自身が使用する[公開大会一覧](https://buildathons.replit.app/api/public/buildathons/visible)と各公開受賞データを読んだ。A25は同様に公開配信された画面コード内の締切表示、主催者記事を読んだ。認証を要する管理画面や非公開情報は根拠にしていない。
- A07の相対表示「1年前」は根拠にせず、同じ公式投稿の構造化データ `datePublished=2025-04-08T07:52:56.832Z` を確認した。本文の受賞対応と日付を別々に確認している。
- A06はHTTPエラーまたは本文なしであり、ページが存在しないと断定できない。期間・受賞・A29との関係を確認できるまで不採用。今回、対象期間外と確定した行は0件だが、これを全50件の期間内確認と表現しない。
- R/Gの40件は「少なくとも1つの名前付き受賞作品が確認できた大会」の数。Pの9件はA22・A24・A25・A26・A27・A28・A29・A30・A31。実際に賞がなかったという意味ではない。
- 年次回（A18/A26、B01/B02）、シリーズ回（A11〜A13、B06〜B09）、同社の別大会（A08〜A10/A25、A20/B14、B18/B19）は異なる日程・名称・要件で区別。週次賞、部門賞、都市会場賞、受賞作品数は大会数に加算しない。
- 審査表の配点、一般的な募集要件、主催者による個別講評、作者の制作説明は別の証拠である。落選作品との比較や統計的因果検証はしていないため「この要素が勝因」と断定しない。

### 追加照合から得た設計判断

| 確認した公式事実 | 本PJの推論・採否 | 確認に使う自作品の証拠 |
|---|---|---|
| A21は実装、現実の課題、UXと説明等を別項目で評価 | 審査項目ごとに実装と説明の根拠を結びつける。Azure利用や他大会の配点は転用しない | 設計書、評価表、操作・異常系テスト |
| A18/A26はブラウザーで直ちに遊べることを重視 | 最初の謎に早く触れられる導線を維持。AI生成割合は今回の品質指標にしない | 初期画面から水門操作までのブラウザー検証 |
| A25の主催者紹介は制作終盤の実機・公開動作の差を扱う | 起動した事実だけで完了せず、保存・復旧・拡大表示まで測る | Docker、別ブラウザー復旧、200%拡大の記録 |
| B05のHugo Tour Guideはonline 1位で旅程・文化情報を組み合わせる | 観光情報と次の行動を同じ導線でつなぐ。音声AIや外部APIはローカル要件に合わず不採用 | 会議周遊候補の所要時間と次の旅への保存 |
| A16の公表総点と内訳に差がある | 他大会の点数を権威として借用せず、自分たちの分母・加点・未測定を明示する | EVALUATION.mdの固定項目と証拠リンク |

## 実装・評価への採否

| 採用する判断 | 対応する実装・証拠 | 根拠の種類 |
|---|---|---|
| AとBの主要動線を保存まで完結させる | API統合試験、ブラウザー操作、次の旅の再表示 | A15の講評＋本PJの目的 |
| 対象者に合う認知負荷とUI | 3画面の役割、ヒント、戻る操作、文字拡大、操作課題 | B07・B09の講評を参考にした推論 |
| 定量評価を修正につなぐ | EVALUATION.mdの固定項目・差分、検証ログ | B07の旅行計画作品への講評＋利用者の明示要件 |
| 再現性を成果物の一部にする | Docker、起動手順、バックアップ復元、例外処理 | A02の制作説明を踏まえた独自の品質判断 |
| ローカル完結の価値を証明する | 外部通信遮断、履歴保存、権限検証 | B14・B18の主催者紹介を参考。独立した測定を実施 |
| 会議の制約を提案理由にする | 往復・滞在・余裕時間の表示と境界テスト | B15の制約付き経路計画を参考にした推論 |

不採用：スポンサー固有クラウドへの接続、賞のためだけのAIモデル追加、他大会の配点平均による今回の採点推定、受賞作の性能値の転用。保留：A06の出典・独立性、P判定9件の受賞確認、G判定の細かな賞対応、実利用者の再訪率向上、全50大会の統計的勝因。

発表で使える表現は「候補50件の出典を照合し、期間内資料49件、うち名前付き受賞作品40件を確認した。AI開発中心28件と関連競技21件を分け、特に10大会の募集・講評を参考に体験の完結性・対象者に合うUI・測定改善を設計へ取り入れた」。全50件の全記述を検証済み、50件すべてがAI駆動開発大会、またはこの手法で優勝できるとは述べない。
