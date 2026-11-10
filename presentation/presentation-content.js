/* Local presentation content. No runtime network calls. */
window.KOU_DECK = {
  "version": "four-and-a-half-minute-v4-presenters",
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
      "title": "旅行の準備、使うサービスがバラバラ。",
      "stages": [
        {
          "service": "Instagram",
          "action": "行き先を探す"
        },
        {
          "service": "LINE",
          "action": "みんなで相談する"
        },
        {
          "service": "楽天トラベル",
          "action": "宿を予約する"
        }
      ],
      "takeaway": "行きたいのに、準備が面倒。",
      "footnote": "旅行準備の一例",
      "duration": 25,
      "notes": "例えば、Instagramで行き先を探して、LINEでみんなに相談。宿の予約は楽天トラベルへ。行き先を変えたら、またLINEで相談です。行きたいだけなのに、使うサービスはバラバラ。何度も行き来する準備が、旅行へのハードルになっています。",
      "sources": [
        "../DESIGN.md"
      ],
      "start": 0,
      "end": 25,
      "speaker": "野村",
      "speaker_role": "01 問題提起"
    },
    {
      "id": "essence",
      "type": "essence",
      "section": "02 本質課題",
      "title": "再訪を気軽にするには、準備をひと続きに。",
      "subtitle": "次の旅でも、探し直す・伝え直す手間を減らす。",
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
      "takeaway": "探す・仲間と決める・事業者に相談する。この流れを途切れさせない。",
      "footnote": "前のページの場面例から整理した設計上の課題です。負担の大きさや再訪への因果は未測定です。",
      "duration": 15,
      "notes": "また気軽に行くには、探す・誘う・相談する準備が、ひと続きにつながることが大切です。探し直す、伝え直す手間をどう減らすか。ここから梅木が、「講」を説明します。",
      "sources": [
        "../DESIGN.md"
      ],
      "start": 25,
      "end": 40,
      "speaker": "野村",
      "speaker_role": "02 本質課題",
      "handoff": {
        "to": "梅木",
        "text": "このページを話し終えたら、3枚目へ進めて梅木さんに交代。",
        "spoken": false
      }
    },
    {
      "id": "intro",
      "type": "cover",
      "section": "03 講の提案",
      "title": "講",
      "subtitle": "仲間探しから事業者への相談まで、一つの「講」で。",
      "definition": "共通の目的で集まり、少しずつ力を持ち寄る仲間。",
      "prompts": [
        "写真・関心から仲間候補へ",
        "講で行き先と条件を決める",
        "共有を確認して直接相談へ"
      ],
      "image": "../frontend/public/art/wa/travel-woodcut-v1-960.webp",
      "duration": 20,
      "notes": "この分断を、私たちは「講」でぶっ壊しにきました。写真から仲間候補を見つけ、行き先を決め、選んだ事業者に直接相談する。準備をひと続きにして、次の旅行を始める負担を減らす提案です。講は、目的のために力を持ち寄る仲間です。",
      "sources": [
        "../DESIGN.md"
      ],
      "start": 40,
      "end": 60,
      "footnote": "講に投稿した写真と本人が許可した関心を利用します。LINE・Instagramとの実連携や予約決済の代行はありません。",
      "speaker": "梅木",
      "speaker_role": "03 講の提案"
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
      "end": 80,
      "speaker": "梅木",
      "speaker_role": "データからの着目"
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
      "footnote": "現在の案内はローカルの規則・定型処理です。汎用の写真認識AIや外部AIには接続していません。",
      "speaker": "梅木",
      "speaker_role": "操作紹介",
      "handoff": {
        "to": "樋口",
        "text": "動画終了後、6枚目へ。樋口さんが再訪の仕組みを話し始める。",
        "spoken": false
      }
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
      "end": 190,
      "speaker": "樋口",
      "speaker_role": "再訪の仕組み 1"
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
      "end": 215,
      "speaker": "樋口",
      "speaker_role": "再訪の仕組み 2"
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
      "notes": "三つ目は、20〜40キロの地域への追加割引です。限られた予算を、繰り返し来やすいと想定する地域に重点配分します。予算上限も設定でき、この距離が最適かは今後検証します。最後に野村から、事業者側の価値をお伝えします。",
      "sources": [
        "../docs/DAYTRIP-ROUTES.md",
        "../DESIGN.md"
      ],
      "start": 215,
      "end": 240,
      "speaker": "樋口",
      "speaker_role": "再訪の仕組み 3",
      "handoff": {
        "to": "野村",
        "text": "9枚目へ進め、野村さんへ戻す。野村さんが事業者の価値と締めを担当。",
        "spoken": false
      }
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
      "end": 260,
      "speaker": "野村",
      "speaker_role": "事業者の価値"
    }
  ],
  "limit": 270,
  "presenter_plan": [
    {
      "name": "野村",
      "segments": [
        {
          "slides": [
            1,
            2
          ],
          "start": 0,
          "end": 40,
          "role": "問題提起・本質課題"
        },
        {
          "slides": [
            9
          ],
          "start": 240,
          "end": 260,
          "role": "事業者の価値・締め"
        }
      ],
      "speech_seconds": 60,
      "video_seconds": 0
    },
    {
      "name": "梅木",
      "segments": [
        {
          "slides": [
            3,
            4,
            5
          ],
          "start": 40,
          "end": 165,
          "role": "講の提案・根拠・動画紹介"
        }
      ],
      "speech_seconds": 40,
      "video_seconds": 85
    },
    {
      "name": "樋口",
      "segments": [
        {
          "slides": [
            6,
            7,
            8
          ],
          "start": 165,
          "end": 240,
          "role": "動画後の再訪3施策"
        }
      ],
      "speech_seconds": 75,
      "video_seconds": 0
    }
  ]
};
