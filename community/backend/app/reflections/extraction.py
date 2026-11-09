import re
import unicodedata

METHOD='local-reflection-rules-v1'
ASPECTS={'guidance':'案内の分かりやすさ','response':'対応','experience':'体験内容','price':'価格への納得'}
PURPOSE='この振り返りから明確に読み取れる事業者の体験を自動で参考集計へ反映し、おすすめの補助に使います。公開するのは件数と定型の匿名要点だけです。'
NOTICE='旅行終了と実利用は本人の申告です。参加や見積の合意を、利用した証明にはしません。'
PRIVATE=re.compile(r'家族|子供|子ども|息子|娘|夫|妻|健康|病気|病院|薬|アレルギー|障害|妊娠|住所|自宅|電話|メール|写真|位置情報|緯度|経度|\b\d{2,4}-\d{2,4}-\d{3,4}\b|@|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}月\d{1,2}日|\d{4}年')
OTHER=re.compile(r'他社|別の会社|別の事業者|同行者|友人|天候|天気|雨|晴れ|雪|台風')
UNCERTAIN=re.compile(r'予定|期待|行きたい|楽しみ|はず|らしい|聞いた|未利用|利用していない|利用しなかった|まだ利用|仮に|例えば|たとえば|もし|ではなく|じゃなく|皮肉|さすが|笑|[wｗ]{2,}|[!?！？]{2,}|だったら|でしょう|だろう')
PATTERNS={
 'guidance':(r'(?:案内|説明)(?:は|が|も)?(?:とても|すごく)?(?:分かりやすかった|わかりやすかった|明確でした|丁寧でした)',r'(?:案内|説明)(?:は|が|も)?(?:分かりにくかった|わかりにくかった|不足していた|不十分でした)'),
 'response':(r'(?:対応|接客)(?:は|が|も)?(?:とても|すごく)?(?:丁寧でした|親切でした|早かった|よかった|良かった)',r'(?:対応|接客)(?:は|が|も)?(?:遅かった|不親切でした|悪かった|残念でした)'),
 'experience':(r'(?:体験|内容)(?:は|が|も)?(?:とても|すごく)?(?:楽しかった|充実していた|よかった|良かった)',r'(?:体験|内容)(?:は|が|も)?(?:退屈でした|退屈だった|つまらなかった|物足りなかった)'),
 'price':(r'(?:価格|料金)(?:は|が|に|も)?(?:納得できました|納得できた|見合っていました|妥当でした)',r'(?:価格|料金)(?:は|が|に|も)?(?:納得できなかった|納得できませんでした|高すぎました|高すぎた)'),
}


def excluded(reason):
    return dict(eligible=False,reason=reason,values=[dict(aspect_id=key,sentiment='excluded') for key in ASPECTS])


def extract(body,provider_name):
    text=unicodedata.normalize('NFKC',body).strip()
    if PRIVATE.search(text):
        return excluded('私的な情報を含むため、参考集計には使いません。')
    if OTHER.search(text):
        return excluded('他の対象や天候などが含まれるため、参考集計には使いません。')
    if UNCERTAIN.search(text):
        return excluded('予定・曖昧さ・皮肉などの可能性があるため、参考集計には使いません。')
    name=unicodedata.normalize('NFKC',provider_name)
    clauses=[part.strip() for part in re.split(r'[。\n]',text) if part.strip()]
    found={aspect:set() for aspect in ASPECTS}
    for index,clause in enumerate(clauses):
        prefix=next((target+'の' for target in (name,'この事業者') if clause.startswith(target+'の')),None)
        if prefix:
            clause=clause[len(prefix):]
        elif index==0:
            return excluded('対象の事業者と体験の結びつきが明確でないため、参考集計には使いません。')
        matched=False
        for aspect,patterns in PATTERNS.items():
            for sentiment,pattern in zip(('positive','negative'),patterns):
                # A whole clause must be understood. Trailing negation, quotation,
                # questions and changes of subject cannot inherit a partial match.
                if re.fullmatch(pattern,clause):
                    found[aspect].add(sentiment)
                    matched=True
        if not matched:
            return excluded('この書き方では明確な体験評価を読み取れません。参考集計には使いません。')
    if not any(found.values()):
        return excluded('この書き方では明確な体験評価を読み取れません。参考集計には使いません。')
    values=[dict(aspect_id=aspect,sentiment='mixed' if len(choices)>1 else next(iter(choices)) if choices else 'excluded') for aspect,choices in found.items()]
    return dict(eligible=True,reason='対象事業者の過去の体験表現を限定した規則で整理しました。本人が訂正・除外できます。',values=values)
