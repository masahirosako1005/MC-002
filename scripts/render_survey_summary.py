"""Render aggregate questionnaire themes; never reads original personal CSVs."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

ROOT=Path(__file__).resolve().parents[1]

def main():
    d=json.loads((ROOT/'artifacts/survey-content-summary.json').read_text(encoding='utf-8'))
    good=d['post_survey']['good_points']
    requests=d['post_survey']['requests']
    groups={k:v for k,v in good['topics'].items() if v['count'] and v['count']>=10}
    groups['特になし']=good['none_response']
    # In this supplied dataset the four nonzero topics plus none are exclusive.
    assert sum(v['count'] for v in groups.values())==good['denominator']
    good_rows=sorted(groups.items(),key=lambda kv:kv[1]['count'],reverse=True)
    request_rows=sorted([(k,v) for k,v in requests['topics'].items() if v['count'] and v['count']>=10],key=lambda kv:kv[1]['count'],reverse=True)[:8]
    plt.rcParams.update({'font.family':FontProperties(fname='C:/Windows/Fonts/meiryo.ttc').get_name(),
                         'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False})
    fig,axes=plt.subplots(1,2,figsize=(14,7.2))
    fig.subplots_adjust(left=.16,right=.94,top=.76,bottom=.22,wspace=.85)
    fig.suptitle('参加後アンケート：良かった点と要望欄の内容',x=.05,y=.96,ha='left',fontsize=21)
    fig.text(.05,.89,'回答者287人 ／ 各割合の分母は287人 ／ 未回答者213人の評価は含みません',fontsize=12,color='#475569')
    for ax,rows,title,color in [(axes[0],good_rows,'良かった点（5分類）','#36778b'),(axes[1],request_rows,'要望欄で言及されたテーマ（上位8）','#a16935')]:
        ax.barh([k for k,v in rows],[v['percent'] for k,v in rows],height=.55,color=color)
        ax.invert_yaxis(); ax.set_xlim(0,48); ax.set_xticks([0,10,20,30,40]); ax.set_xlabel('回答者に占める割合（%）')
        ax.set_title(title,loc='left',fontsize=13,pad=15)
        ax.tick_params(axis='y',length=0)
        for i,(k,v) in enumerate(rows):ax.text(v['percent']+.7,i,f"{v['count']}人 / {100*v['count']/v['denominator']:.1f}%",va='center',fontsize=10)
        ax.set_axisbelow(True);ax.grid(axis='x',alpha=.14)
    fig.text(.05,.13,'良かった点は提供データ内で重複なし。要望欄は複数テーマに該当するため、割合の合計は100%を超えます。',fontsize=11)
    fig.text(.05,.085,'要望欄には感想も含まれます。右図はキーワードの言及数であり、その人数が改善を要求したという意味ではありません。',fontsize=10)
    fig.text(.05,.045,'良かった点は5種類、要望欄は26種類の文面。実測/合成・抽出方法は未確認のため、このサンプル内の記述統計です。',fontsize=10,color='#475569')
    fig.savefig(ROOT/'outputs/survey-content-trends.png',dpi=170,facecolor='white')
    plt.close(fig)
    report=ROOT/'docs/SAMPLE-DATA-TRENDS.md'
    base=report.read_text(encoding='utf-8').split('\n## 6. アンケート内容の統計')[0]
    base=base.replace('アンケート内容の集計は次節に追記する。','アンケート内容は次節に掲載する。')
    lines=['','## 6. アンケート内容の統計','',
           '![アンケート内容の集計](../outputs/survey-content-trends.png)','',
           '### 6.1 旅で良かった点（287人）','',
           'NFKC正規化と前後空白除去後の文面は5種類。テーマ辞書で各回答を分類すると、4テーマのいずれかにだけ該当する237人と「なし」50人となった。複数分類・未分類は0人。以下は重複なしで合計287人、100%。「特になし」は空欄や不満回答とは区別する。','']
    def table(title,rows):
        lines.extend([title,'','| 内容 | 人数 | 割合 |','|---|---:|---:|'])
        for k,v in rows:
            if v['suppressed']: lines.append(f'| {k} | 少数のため非表示 | — |')
            elif v['count']:
                lines.append(f"| {k} | {v['count']} | {100*v['count']/v['denominator']:.1f}% |")
        lines.append('')
    table('分母：参加後回答者287人。',good_rows)
    lines.extend(['同行・交流69人と自然・景観65人が上位。ただし差は4人にとどまり、交流が圧倒的な優先事項とは言えない。スタンプ55人、特典48人も記録されており、仲間機能だけの需要を示したものではない。','',
                  '### 6.2 要望欄に書かれたテーマ（287人・複数分類）','',
                  '各回答にテーマのキーワードがあるかを集計し、同じテーマは1回答につき1回だけ数えた。1回答が複数テーマに該当するため合計は100%を超える。全回答が少なくとも1テーマに該当し、空欄0・未分類0。ただし、これは意味分類の精度100%という意味ではない。','',
                  '**この欄には感想・肯定表現も含まれる。下表は改善要求の人数ではなく、テーマへの言及人数である。**'])
    all_requests=sorted(requests['topics'].items(),key=lambda kv:kv[1]['count'] or 0,reverse=True)
    table('分母：参加後回答者287人。',all_requests)
    context=requests['expression_context']
    status=context['mutually_exclusive_status']
    combined=[('希望または困難の表現あり',context['explicit_request_or_difficulty']),
              ('希望・困難表現がなく、肯定表現あり',status['希望・困難表現なし・肯定表現あり']),
              ('上記の表現辞書では未判定',status['上記表現では未判定'])]
    table('要望欄の表現を追加確認した結果（重複なし、分母287人）：',combined)
    lines.extend(['ここでの希望・困難・肯定は明示的な語の有無による分類であり、人手で確認した要望件数や感情の正解ではない。未判定192人を「要望なし」としない。同一回答内のテーマと希望語の共起も、当該テーマへの改善要求とは確定できない。',''])
    lines.extend(['テーマが多い案内・地図・経路などは、追加の聞き取りで「役立った点」「困った点」「改善したい点」を分けて確認する候補になる。現時点で94人が案内改善を要求したとは言えない。','',
                  '### 6.3 何で知ったか（500人・複数選択）','',
                  'セミコロンで選択肢を分割し、回答者ごとに同一選択肢を重複排除。未知選択肢0、空欄0、複数選択者191人、延べ選択数733。割合の分母は延べ733件ではなく回答者500人で、合計146.6%。'])
    table('分母：登録時回答者500人。',d['registration']['recognition_channels']['categories'].items())
    lines.extend(['各経路は23.0〜25.6%で分散している。単独で支配的な集客経路はこの集計から見られない。元選択肢に「架空SNSの投稿」という表記があり、実在サービスの利用実績や実測調査とは断定しない。観光パンフレット名に含まれる地域名は表示を省略した。','',
                  '### 6.4 職業と居住地域（各500人）',''])
    table('職業：辞書で広い区分にまとめ、重複なし・未分類0・未回答0。',d['registration']['occupation']['categories'].items())
    table('居住地域：提供CSV内の地域ラベル。実在都道府県への対応は未確認。',d['registration']['residence_region']['categories'].items())
    lines.extend(['職業の「家事・育児・主婦・主夫・その他」は異なる選択肢をまとめた区分であり、全員を同じ生活状況とみなさない。地域名から距離や都市/地方の違いを推定しない。','',
                  '### 6.5 文面の集中・分類の限界・再現','',
                  '良かった点は5種類の文面が全287回答を占める。要望欄は26種類、最多の同一文面27人、上位5文面で36.24%。自由な文章が287通りあるデータではなく、定型選択・合成等の生成方法が未確認である。文面の数を回答者数へ置き換えず、また同一文面を独立な需要の証拠として過大評価しない。','',
                  '分類は正規表現によるキーワード一致。否定、対象、希望、感想の文脈を完全には判定できない。最初の辞書を実データで確認後に選択肢分割と語彙を補い、最終辞書を保存した探索的分析である。外部評価用の正解データで分類精度を検証したものではない。','',
                  '集計：`scripts/analyze_survey_content.py`、数値正本：`artifacts/survey-content-summary.json`、作図・本節生成：`scripts/render_survey_summary.py`。元CSV2件の前後ハッシュ一致。認知経路の選択肢網羅・人数・延べ件数、良かった点の排他分類・合計287人は独立レビューでも確認した。氏名・ID・自由記述原文を出力しない。',''])
    report.write_text(base+'\n'.join(lines),encoding='utf-8')

if __name__=='__main__': main()
