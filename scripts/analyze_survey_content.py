"""Local questionnaire content counts. No source text or person identifiers leave memory."""
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('C:/AI-Sprint/sample-data')
OUTPUT = ROOT / 'artifacts/survey-content-summary.json'
SOURCES = {'before':'09_アンケート回答_登録時.csv', 'after':'08_アンケート回答_参加後.csv'}
THRESHOLD = 10

# Fixed before the first run. Categories describe mentions, not inferred sentiment or demand.
TOPICS = {
    '自然・景観': r'自然|景色|景観|風景|眺め|紅葉|絶景',
    '地域・場所の再発見': r'再発見|発見|知らなかった|知らない場所|初めての場所|新しい場所|魅力|穴場',
    'スタンプ収集・ラリー': r'スタンプ|ラリー|集め|収集',
    '達成・完走': r'達成|制覇|コンプリート|完走|全[部箇所]|全て|すべて',
    '特典・景品': r'特典|景品|賞品|プレゼント|クーポン|お得|割引',
    '同行・交流': r'仲間|友人|友達|友だち|知人|家族|親子|夫婦|子ども|子供|交流|出会い|一緒|いっしょ',
    'スタッフ・案内者': r'スタッフ|ガイド|案内人|係員|店員|従業員|接客',
    '案内・地図・移動経路': r'案内|地図|マップ|アクセス|道順|ルート|移動|説明|看板|標識',
    '交通・駐車': r'交通|駐車|バス|電車|鉄道|渋滞|徒歩|歩行',
    '施設・店舗・スポット': r'施設|店舗|お店|スポット|トイレ|休憩所|飲食店',
    '食事・飲食': r'食事|食べ|料理|グルメ|ランチ|カフェ|飲食|おいし|美味',
    '歴史・文化': r'歴史|文化|神社|お寺|美術|博物館',
    '混雑・待ち時間': r'混雑|混ん|待ち時間|行列|人が多',
    '営業時間・休業': r'営業時間|営業日|休業|定休日|閉店|開店|閉館|開館',
    'アプリ・操作・通信': r'アプリ|操作|使いやす|使いにく|使いづら|分かりやす|わかりやす|分かりにく|わかりにく|通信|電波|ログイン|QR|サイト|画面',
    '開催時期・期間': r'開催|期間|日程|季節|時期|週末|平日|延長',
    '再参加・再訪・次回': r'再訪|再び|もう一度|また行|また来|また訪|また参加|次回|次の旅|リピート',
}
CHANNELS = {
    '架空SNSの投稿': r'^架空SNSの投稿$',
    '観光パンフレット': r'^星凪諸島観光パンフレット$',
    '友人からの紹介': r'^友人からの紹介$',
    '観光案内所': r'^観光案内所$',
    '旅の交流掲示板': r'^旅の交流掲示板$',
    'その他という回答': r'^その他$',
}
JOBS = {
    '会社員・団体職員': r'会社員|会社役員|団体職員|正社員|契約社員|派遣社員',
    '公務員': r'公務員',
    '自営業・自由業': r'自営業|自営|自由業|フリーランス|個人事業',
    '学生': r'学生|大学生|高校生|中学生|小学生',
    '家事・育児・主婦・主夫・その他': r'家事|育児|主婦|主夫|^その他$',
    'パート・アルバイト': r'パート|アルバイト',
    '無職・退職': r'無職|退職|年金生活',
}
SOURCE_REGIONS = ['七色野地方','星凪地方','水琴地方','霧灯地方','雲風地方','青綴地方']
REGIONS = {
    '北海道': ['北海道'], '東北':['青森県','岩手県','宮城県','秋田県','山形県','福島県'],
    '関東':['茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県'],
    '甲信越':['新潟県','山梨県','長野県'], '北陸':['富山県','石川県','福井県'],
    '東海':['岐阜県','静岡県','愛知県','三重県'],
    '近畿':['滋賀県','京都府','大阪府','兵庫県','奈良県','和歌山県'],
    '中国':['鳥取県','島根県','岡山県','広島県','山口県'],
    '四国':['徳島県','香川県','愛媛県','高知県'],
    '九州・沖縄':['福岡県','佐賀県','長崎県','熊本県','大分県','宮崎県','鹿児島県','沖縄県'],
}
NONE_RE = re.compile(r'^(?:特に(?:は)?(?:ありません|ないです|なし|ない)|ありません|なし|ない|要望なし|特になしです)[。.!！\s]*$')
REQUEST_RE = re.compile(r'ほしい|欲しい|希望|してもら|していただ|増やして|増やす|改善して|改善を|あると(?:よい|良い|嬉しい|うれしい)|できると(?:よい|良い|嬉しい|うれしい)')
DIFFICULTY_RE = re.compile(r'不満|分かりにく|わかりにく|使いにく|使いづら|残念|困|迷っ|混雑|混ん|待ち時間')
POSITIVE_RE = re.compile(r'楽しか|楽しい|楽しめ|よかった|良かった|嬉しか|うれしか|満足|使いやす|分かりやす|わかりやす|美しか|きれい|綺麗|便利')

def normalize(value):
    return unicodedata.normalize('NFKC', value).strip()

def matches(value, dictionary):
    return [label for label, pattern in dictionary.items() if re.search(pattern,value,re.I)]

def publish(counts, n, exclusive=False):
    out = {}
    small = [k for k,v in counts.items() if 0<v<THRESHOLD]
    secondary = None
    if exclusive and len(small)==1:
        eligible = [k for k,v in counts.items() if v>=THRESHOLD]
        if eligible: secondary=min(eligible,key=lambda k:counts[k])
    for k,v in counts.items():
        suppressed = 0<v<THRESHOLD or k==secondary
        out[k]={'count':None if suppressed else v,'percent':None if suppressed else round(v/n*100,2) if n else None,
                'suppressed':suppressed,'denominator':n}
    return out

def dictionary_counts(values, dictionary, exclusive=False, split_semicolon=False):
    counts=Counter(dict.fromkeys(dictionary,0))
    unmatched=blank=multiple=0
    for v in values:
        selected=list({label for token in v.split(';') for label in matches(token.strip(),dictionary)}) if split_semicolon else matches(v,dictionary)
        blank+=not bool(v)
        unmatched+=bool(v) and not selected
        multiple+=len(selected)>1
        if exclusive and len(selected)>1:
            raise RuntimeError('Overlapping exclusive classification; no source values disclosed.')
        counts.update(selected)
    if exclusive:
        counts['未分類']=unmatched
        counts['未回答']=blank
    unknown_tokens=sum(not matches(token.strip(),dictionary) for v in values for token in v.split(';') if token.strip()) if split_semicolon else None
    if split_semicolon:assert unknown_tokens==0
    return {'categories':publish(counts,len(values),exclusive),'unclassified':unmatched,'blank':blank,
            'multiple_category_rows':multiple,'denominator':len(values),'multi_response':not exclusive,
            'total_selections':sum(counts.values()) if split_semicolon else None,'unknown_token_count':unknown_tokens}

def text_stats(values):
    count=Counter(v for v in values if v)
    freqs=sorted(count.values(),reverse=True)
    n=len(values)
    counts=Counter(dict.fromkeys(TOPICS,0))
    no_request=unclassified=negative=wish=positive=0
    for v in values:
        none=bool(NONE_RE.fullmatch(v))
        no_request+=none
        selected=[] if none else matches(v,TOPICS)
        counts.update(selected)
        unclassified+=bool(v) and not none and not selected
        negative+=bool(re.search(r'不要|いらない|必要[はも]?ない|不満|分かりにく|わかりにく|使いにく|使いづら|残念|困',v))
        wish+=bool(re.search(r'ほしい|欲しい|希望|増や|充実|あると|できると|してもら',v))
        positive+=bool(re.search(r'楽しか|楽しい|楽しめ|よかった|良かった|嬉しか|うれしか|満足',v))
    return {'denominator':n,'nonempty':sum(bool(v) for v in values),'topics':publish(counts,n),
       'none_response':publish({'なしの明示':no_request},n)['なしの明示'],
       'unclassified':publish({'未分類':unclassified},n)['未分類'],
       'concentration':{'distinct_exact_texts':len(count),'largest_text_count':max(freqs,default=0),
           'largest_text_percent':round(max(freqs,default=0)/n*100,2),'top3_percent':round(sum(freqs[:3])/n*100,2),
           'top5_percent':round(sum(freqs[:5])/n*100,2),'frequency_counts_without_text':[f for f in freqs if f>=THRESHOLD],
           'rare_texts_exist':any(f<THRESHOLD for f in freqs)},
       'classification_note':'回答者ごと・項目ごとに最大1カウント、複数テーマ可。語の言及数であり需要人数や感情判定ではない。'}

def context_stats(values):
    """Exploratory phrase markers after the first pass; no full semantic judgement."""
    statuses=Counter(dict.fromkeys(['希望表現あり','希望表現なし・困難表現あり','希望・困難表現なし・肯定表現あり','なしの明示','上記表現では未判定'],0))
    topic_request=Counter(dict.fromkeys(TOPICS,0))
    topic_difficulty=Counter(dict.fromkeys(TOPICS,0))
    topic_positive_only=Counter(dict.fromkeys(TOPICS,0))
    for v in values:
        request=bool(REQUEST_RE.search(v)); difficulty=bool(DIFFICULTY_RE.search(v));positive=bool(POSITIVE_RE.search(v))
        none=bool(NONE_RE.fullmatch(v))
        label='なしの明示' if none else '希望表現あり' if request else '希望表現なし・困難表現あり' if difficulty else '希望・困難表現なし・肯定表現あり' if positive else '上記表現では未判定'
        statuses[label]+=1
        selected=matches(v,TOPICS)
        if request:topic_request.update(selected)
        if difficulty:topic_difficulty.update(selected)
        if positive and not request and not difficulty:topic_positive_only.update(selected)
    assert sum(statuses.values())==len(values)
    return {'mutually_exclusive_status':publish(statuses,len(values),True),
      'explicit_request_or_difficulty':publish({'明示的希望または困難表現':statuses['希望表現あり']+statuses['希望表現なし・困難表現あり']},len(values))['明示的希望または困難表現'],
      'topic_and_request_phrase':publish(topic_request,len(values)),
      'topic_and_difficulty_phrase':publish(topic_difficulty,len(values)),
      'topic_and_positive_without_request_or_difficulty_phrase':publish(topic_positive_only,len(values)),
      'request_regex':REQUEST_RE.pattern,'difficulty_regex':DIFFICULTY_RE.pattern,'positive_regex':POSITIVE_RE.pattern,
      'meaning':'同じ回答内でテーマ語と表現が共起した件数。構文上の係り受けや皮肉は未評価。希望が当該テーマを改善する要求かは未確定。肯定だけの言及を改善課題に変換しない。',
      'timing':'初回テーマ集計後に追加した探索的な表現分類。原文からの人手正解ラベルによる検証は未実施。'}

def run():
    tables={};meta={}
    for kind,name in SOURCES.items():
        raw=(SOURCE/name).read_bytes()
        for enc in ['utf-8-sig','cp932']:
            try: decoded=raw.decode(enc);break
            except UnicodeDecodeError: continue
        rows=list(csv.DictReader(io.StringIO(decoded)))
        assert all(None not in r and all(v is not None for v in r.values()) for r in rows)
        assert len({r['user_id'] for r in rows})==len(rows)
        tables[kind]=rows;meta[kind]={'filename':name,'rows':len(rows),'sha256':hashlib.sha256(raw).hexdigest()}
    b,a=tables['before'],tables['after']
    channel=next(c for c in b[0] if '何で知り' in c)
    jobs=next(c for c in b[0] if '職業' in c)
    region=next(c for c in b[0] if '居住地' in c)
    good=next(c for c in a[0] if '良かった点' in c)
    request=next(c for c in a[0] if '要望' in c)
    residence_counts=Counter(dict.fromkeys(SOURCE_REGIONS,0));residence_counts.update({'未分類':0,'未回答':0})
    for r in b:
        v=normalize(r[region]);found=[k for k in SOURCE_REGIONS if v==k]
        assert len(found)<=1
        residence_counts[found[0] if found else '未分類' if v else '未回答']+=1
    assert sum(residence_counts.values())==len(b)
    good_values=[normalize(r[good]) for r in a];request_values=[normalize(r[request]) for r in a]
    good_assignments=[['なし'] if NONE_RE.fullmatch(v) else matches(v,TOPICS) for v in good_values]
    good_validation={'rows':len(good_values),'exactly_one_category_rows':sum(len(x)==1 for x in good_assignments),
        'multiple_category_rows':sum(len(x)>1 for x in good_assignments),'unclassified_rows':sum(len(x)==0 for x in good_assignments),
        'distinct_texts':len(set(good_values)),
        'every_distinct_text_exactly_one_category':all(len(['なし'] if NONE_RE.fullmatch(v) else matches(v,TOPICS))==1 for v in set(good_values)),
        'classification_total':sum(len(x) for x in good_assignments),
        'meaning':'機械的辞書対応を全287回答・5異文面について確認。原文やハッシュは出力しない。意図の人手判定精度とは区別する。'}
    assert good_validation['classification_total']==len(good_values)
    assert good_validation['every_distinct_text_exactly_one_category']
    result={'analysis_utc':datetime.now(timezone.utc).isoformat(),'sources':meta,
      'registration':{'recognition_channels':dictionary_counts([normalize(r[channel]) for r in b],CHANNELS,split_semicolon=True),
       'occupation':dictionary_counts([normalize(r[jobs]) for r in b],JOBS,True),
       'residence_region':{'categories':publish(residence_counts,len(b),True),'denominator':len(b),'exclusive':True,
          'meaning':'提供CSVの地域ラベル。実在都道府県・地理的距離・居住人口への対応は未確認。'}},
      'post_survey':{'good_points':{**text_stats(good_values),'exclusive_validation':good_validation},
        'requests':{**text_stats(request_values),'expression_context':context_stats(request_values)}},
      'method':{'version':'survey-content-v3','threshold':THRESHOLD,'topics_regex':TOPICS,'channels_regex':CHANNELS,
       'jobs_regex':JOBS,'source_regions':SOURCE_REGIONS,'none_regex':NONE_RE.pattern,
       'normalization':'NFKCおよび前後空白除去。自由記述テーマ辞書は初回実行前に固定。登録時のカテゴリ対応は初回の未分類を受け、10件以上の選択肢ラベルを確認して更新。認知経路はセミコロンで分割し回答者内重複排除。',
       'first_pass_diagnostics':{'unclassified_channel_rows':60,'unclassified_occupation_rows':49,'unclassified_residence_rows':500},
       'validation':'一人一回答、列構造、地域合計、カテゴリ排他性、合成文5条件を確認。原文全件の人手意味判定・正解ラベル比較は未実施。',
       'limits':['良かった点欄と要望欄を別集計。否定・希望・肯定の語は別集計で、全文の意図を保証しない。',
          '複数分類の合計は回答者数を超え得る。辞書未一致は言及なしや関心なしの証明にならない。',
          '登録時の経路は確認済み選択肢を分割した人数。同一回答内の同じカテゴリは一回のみ計上。',
          '提供サンプルの実測・合成・選択式等の由来未確認。母集団推定や因果判断には用いない。',
          '少数カテゴリは非表示。排他的な集計で少数が1セルのみのとき補完抑制。匿名性の保証ではない。']},
      'source_unchanged':all(hashlib.sha256((SOURCE/SOURCES[k]).read_bytes()).hexdigest()==meta[k]['sha256'] for k in SOURCES)}
    assert result['source_unchanged']
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={k:v for k,v in result.items() if k in ('registration','post_survey','source_unchanged')}
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':run()
