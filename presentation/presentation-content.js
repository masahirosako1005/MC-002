/* Local presentation content. No runtime network calls. */
window.KOU_DECK = {
  "version": "four-and-a-half-minute-v1",
  "title": "講｜4分半以内の発表",
  "duration": 260,
  "speechDuration": 175,
  "video": {
    "src": "../outputs/kou-revisit-intro-v13.mp4",
    "captions": "../outputs/kou-revisit-intro-v13-ja.vtt",
    "duration": 77.9,
    "slot": 85,
    "poster": "../artifacts/video-revisit/v13/final/decoded-01-login_before.png"
  },
  "slides": [
    {
      "id": "intro",
      "type": "cover",
      "section": "課題と提案",
      "title": "講",
      "subtitle": "仲間探しと事業者への相談をまとめ、地域への再訪を支える",
      "definition": "共通の目的のために集まり、少しずつ協力する仲間。",
      "prompts": [
        "誰を誘うか",
        "どこへ行くか",
        "誰がお店と相談するか"
      ],
      "image": "../frontend/public/art/wa/travel-woodcut-v1-960.webp",
      "duration": 20,
      "notes": "「また行こう」と話しても、次の予定が決まらない。私たちの「講」は、仲間探しと事業者への相談をまとめるサービスです。共通の目的で集まり、少しずつ協力する「講」の考え方を、旅行計画に取り入れました。",
      "sources": [
        "../DESIGN.md"
      ],
      "start": 0,
      "end": 20
    },
    {
      "id": "evidence",
      "type": "evidence",
      "section": "データからの着目",
      "title": "一緒に楽しむ体験と、地域の魅力",
      "subtitle": "参加後アンケートで「良かった点」に挙がったテーマ",
      "metrics": [
        {
          "label": "同行・交流",
          "count": 69,
          "total": 287,
          "percent": 24
        },
        {
          "label": "自然・景観",
          "count": 65,
          "total": 287,
          "percent": 22.6
        }
      ],
      "takeaway": "写真や関心の共有を、今回の旅を計画する「講」へ。",
      "footnote": "提供サンプル500人のうち回答287人。需要や再訪効果を証明する数値ではありません。",
      "duration": 20,
      "notes": "提供サンプルの回答者287人では、旅で良かった点として、同行・交流が69人、自然・景観が65人でした。人と地域の体験をつなぐ設計に着目しました。まず、実際の操作をご覧ください。",
      "sources": [
        "../docs/COMMUNITY-UX-RATIONALE.md",
        "../artifacts/survey-content-summary.json"
      ],
      "start": 20,
      "end": 40
    },
    {
      "id": "usage",
      "type": "video",
      "section": "操作紹介",
      "title": "ログインから、事業者との相談まで",
      "subtitle": "写真・関心 → 仲間候補 → 行き先を選ぶ → 共有相談",
      "duration": 85,
      "notes": "【読み上げません】約78秒の動画を音声付きで再生します。85秒枠の残り約7秒は、再生開始と次のスライドへの切替に使います。動画終了後、次へ進みます。",
      "sources": [
        "../docs/REVISIT-VIDEO.md"
      ],
      "start": 40,
      "end": 125
    },
    {
      "id": "program",
      "type": "program",
      "section": "再訪の仕組み 1",
      "title": "何度か通って完成する「通う旅」",
      "subtitle": "次に訪れる目的を、体験の中に組み込む。",
      "steps": [
        {
          "title": "成形",
          "description": "自分の器を作る"
        },
        {
          "title": "絵付け",
          "description": "色や模様を付ける"
        },
        {
          "title": "受け取り",
          "description": "完成した器を持ち帰る"
        }
      ],
      "takeaway": "前回の進捗を残し、事業者から次の工程を提案。",
      "image": "assets/current/program-progress.jpg",
      "footnote": "参加登録・予定と、実施確認後の進捗を分けて管理します。",
      "duration": 25,
      "notes": "再訪の仕組みは三つです。一つ目は「通う旅」。陶芸なら、器を作り、次は絵付け、最後は受け取り。同じ場所に何度か通うことで、一つの目的が完成します。本人は進捗を確認でき、事業者は共有相談で「次は絵付けを」と誘えます。",
      "sources": [
        "../docs/JOURNEY-PROGRAMS-CONTRACT.md"
      ],
      "start": 125,
      "end": 150
    },
    {
      "id": "leader",
      "type": "leader",
      "section": "再訪の仕組み 2",
      "title": "企画を担う「先達」に、追加ポイント",
      "subtitle": "次の講を開く人に、貢献に応じた特典を。",
      "steps": [
        {
          "title": "企画・開催",
          "description": "日程や旅先との調整を担う"
        },
        {
          "title": "実施確認",
          "description": "役割と実際の参加を確認"
        },
        {
          "title": "追加ポイント",
          "description": "階級やクーポンの特典へ"
        }
      ],
      "image": "assets/current/rank-phone.jpg",
      "takeaway": "企画する人のメリットが、次の旅行計画のきっかけになる。",
      "footnote": "企画しただけで付与せず、役割承諾・実施確認に基づいて判定します。",
      "duration": 25,
      "notes": "二つ目は、企画を担う「先達」への追加ポイントです。日程やお店との調整を担った人に、実施確認に応じて加点し、階級やクーポンの特典につなげます。企画する人にメリットを返すことで、次の講を開くきっかけを増やす狙いです。",
      "sources": [
        "../DESIGN.md"
      ],
      "start": 150,
      "end": 175
    },
    {
      "id": "zone",
      "type": "zone",
      "section": "再訪の仕組み 3",
      "title": "20〜40kmのターゲティングゾーン",
      "subtitle": "限られた割引予算を、繰り返し来やすい地域へ。",
      "range": {
        "min": 20,
        "max": 40,
        "unit": "km"
      },
      "items": [
        "対象地域へ追加割引",
        "事業者が予算上限を設定",
        "割引の確保・利用・取消を管理"
      ],
      "image": "assets/current/zone-coupon.jpg",
      "footnote": "今回採用した参考距離の条件です。実道路距離や、実証された最適距離ではありません。",
      "duration": 25,
      "notes": "三つ目は、20〜40キロの地域への追加割引です。限られた予算を、日帰りで繰り返し来やすいと想定する地域に重点配分します。事業者は予算上限も設定できます。この距離は今回の設定で、最適な範囲かどうかは今後検証します。",
      "sources": [
        "../docs/DAYTRIP-ROUTES.md",
        "../DESIGN.md"
      ],
      "start": 175,
      "end": 200
    },
    {
      "id": "business",
      "type": "business",
      "section": "事業者の価値",
      "title": "自社の相談と、N西市全体の傾向を確認",
      "subtitle": "次の体験を提案し、来訪・再訪・居住地域を把握。",
      "items": [
        "講へ既存コースを提案",
        "自社と市全体を切り替えて集計",
        "同意した振り返りを参考情報に"
      ],
      "image": "assets/current/city-dashboard.jpg",
      "footnote": "数値は架空の運用データ。地域は共有許可・少人数抑制付きの集計。内輪の会話・写真は公開しません。",
      "duration": 20,
      "notes": "事業者は、相談した講に次の体験を提案できます。自社だけでなく、N西市全体の来訪・再訪や、どの地域から来ているかも把握できます。全員の利用申告と同意がそろった専用の振り返りだけを、事業者選びの参考にします。",
      "sources": [
        "../docs/CITY-DASHBOARD-ACCEPTANCE.md",
        "../docs/contracts/REFLECTIONS-CONTRACT.md"
      ],
      "start": 200,
      "end": 220
    },
    {
      "id": "quality",
      "type": "quality",
      "section": "実装と検証",
      "title": "動作を確かめ、再訪効果を測る",
      "technology": [
        "React",
        "Python",
        "Docker"
      ],
      "metric": {
        "number": 433,
        "label": "品質評価対象版で成功したテスト",
        "scope": "EV02・21eb465／細分32件は別集計"
      },
      "verified": [
        "保存・権限・復元",
        "文字拡大・キーボード操作"
      ],
      "next": [
        "30日・90日後の再訪率",
        "再訪1回あたりの割引コスト"
      ],
      "footnote": "案内は外部AIを呼ばないローカル処理。未解決の静的指摘・未検証項目があり、実際の再訪効果は未測定です。",
      "closing": "仲間と予定を決めやすく、地域に通う目的が続く。",
      "duration": 40,
      "notes": "実装はReactとPythonを中心に、Dockerでローカル動作します。案内は現在、登録情報とルールを使っており、外部AIには接続していません。\n\n開発ではAIで実装とレビューを分担し、測定・修正・再測定を行いました。品質評価対象版では433件のテストが成功しています。\n\n実際の再訪効果はこれからです。30日・90日後の再訪率と、一回の再訪につながる割引コストを測ります。仲間と予定を決めやすく、地域に通う目的が続く。それを支える「講」を提案します。ありがとうございました。",
      "sources": [
        "../docs/evaluation-frameworks/EV02-REPORT.md",
        "../DESIGN.md"
      ],
      "start": 220,
      "end": 260
    }
  ],
  "limit": 270
};
