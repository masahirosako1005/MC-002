/* Local presentation content. No runtime network calls. */
window.KOU_DECK = {
  "version": "four-and-a-half-minute-v2-friction",
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
      "id": "friction",
      "type": "friction",
      "section": "01 問題提起",
      "title": "旅の準備で、アプリを何度も行き来する",
      "subtitle": "「また行きたい」から、予定が決まるまで。",
      "stages": [
        {
          "service": "LINE",
          "action": "グループを作る",
          "obstacle": "誰が同じ趣味？"
        },
        {
          "service": "Instagram",
          "action": "友人の好みを探す",
          "obstacle": "写真から探し直す"
        },
        {
          "service": "LINE",
          "action": "仲間を招待する",
          "obstacle": "一人ずつ声をかける"
        },
        {
          "service": "Instagram",
          "action": "行き先を探す",
          "obstacle": "候補をまた共有する"
        },
        {
          "service": "予約サイト",
          "action": "予約・連絡する",
          "obstacle": "条件を伝え直す"
        }
      ],
      "takeaway": "「また行こう」が、旅の準備で止まっていませんか。",
      "footnote": "日常の旅行計画を想定した場面例です。アプリ間の移動が再訪に及ぼす影響は未測定です。",
      "duration": 25,
      "notes": "LINEでグループを作ろうにも、誰が同じ趣味か分からない。Instagramで友達の好みを探し、LINEに戻って誘う。次はまたInstagramで行き先探し。候補を共有して日程を合わせ、最後は別のサイトで予約。「また行こう」までの準備、こんなに行ったり来たりしていませんか。",
      "sources": [
        "../DESIGN.md"
      ],
      "start": 0,
      "end": 25
    },
    {
      "id": "essence",
      "type": "essence",
      "section": "02 本質課題",
      "title": "好みの発見が、仲間との合意や相談につながらない",
      "subtitle": "一人が見つけた情報を、次の人・次の場所へ運び直している。",
      "gaps": [
        {
          "title": "関心 → 仲間",
          "problem": "誰が何を好きか分からない",
          "response": "写真・関心から仲間候補へ"
        },
        {
          "title": "候補 → 合意",
          "problem": "候補と条件が会話に散らばる",
          "response": "講で行き先と条件を決める"
        },
        {
          "title": "合意 → 事業者",
          "problem": "決めた条件をもう一度伝える",
          "response": "共有を確認して直接相談へ"
        }
      ],
      "takeaway": "関心・仲間・行き先・相談を、一続きにする必要がある。",
      "footnote": "前のページの場面例から整理した設計上の課題です。負担の大きさや再訪への因果は未測定です。",
      "duration": 15,
      "notes": "本質は、情報の引き継ぎです。個人の「好き」を仲間との合意につなぎ、決めた条件を事業者へ伝え直す。その負担が、一人の幹事に集中しています。",
      "sources": [
        "../DESIGN.md"
      ],
      "start": 25,
      "end": 40
    },
    {
      "id": "intro",
      "type": "cover",
      "section": "03 講の提案",
      "title": "講",
      "subtitle": "旅の準備の分断を、講でぶっ壊す。",
      "definition": "共通の目的で集まり、少しずつ力を持ち寄る仲間。",
      "prompts": [
        "写真・関心から仲間候補へ",
        "講で行き先と条件を決める",
        "共有を確認して直接相談へ"
      ],
      "image": "../frontend/public/art/wa/travel-woodcut-v1-960.webp",
      "duration": 20,
      "notes": "この分断を、私たちは「講」という考え方でぶっ壊しにきました。講は、共通の目的で集まり、少しずつ力を持ち寄る仲間。写真から関心を共有し、仲間と行き先を選び、事業者と直接相談する。その一連の準備を、一つの場につなげます。",
      "sources": [
        "../DESIGN.md"
      ],
      "start": 40,
      "end": 60,
      "footnote": "講に投稿した写真と本人が許可した関心を利用します。LINE・Instagramとの実連携や予約決済の代行はありません。"
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
      "start": 60,
      "end": 80
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
      "start": 80,
      "end": 165,
      "footnote": "現在の案内はローカルの規則・定型処理です。汎用の写真認識AIや外部AIには接続していません。"
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
      "start": 165,
      "end": 190
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
      "start": 190,
      "end": 215
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
      "start": 215,
      "end": 240
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
      "notes": "事業者は市全体の来訪傾向を見ながら、相談した講に次の体験を提案できます。旅の準備を一つにつなぎ、地域に通う目的を育てる。再訪まで支える「講」を提案します。ありがとうございました。",
      "sources": [
        "../docs/CITY-DASHBOARD-ACCEPTANCE.md",
        "../docs/contracts/REFLECTIONS-CONTRACT.md"
      ],
      "start": 240,
      "end": 260
    }
  ],
  "limit": 270
};
