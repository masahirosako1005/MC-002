"""Read-only local CSV analysis. Emit group aggregates; never personal records."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
import hashlib
import json

from analyze_community_samples import read_sources, age_band, parse_date, SATISFACTION, spearman

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('C:/AI-Sprint/sample-data')

def pct(a, b):
    return round(a / b * 100, 1) if b else None

def analyze():
    tables, files = read_sources()
    users = {r['ユーザーID'].strip(): r for r in tables['users']}
    assert len(users) == len(tables['users']), 'Duplicate user keys'
    after = {r['user_id'].strip(): r for r in tables['after']}
    assert len(after) == len(tables['after']), 'Duplicate survey keys'
    stamps = Counter(r['ユーザID'].strip() for r in tables['stamps'])
    rewards = Counter(r['user_id'].strip() for r in tables['rewards'])
    days, spots = defaultdict(set), defaultdict(set)
    dates = []
    for r in tables['stamps']:
        d = parse_date(r['獲得日時'])
        assert d is not None, 'Invalid stamp timestamp'
        uid = r['ユーザID'].strip()
        days[uid].add(d.date().isoformat())
        spots[uid].add(r['スポット名'])
        dates.append(d.date().isoformat())
    sat_col = 'アンケート①(満足度を教えてください)'
    assert all(r[sat_col] in SATISFACTION for r in after.values()), 'Unknown satisfaction'
    sat = {u: SATISFACTION[r[sat_col]] for u, r in after.items()}
    def metrics(ids):
        n = len(ids)
        answered = [u for u in ids if u in sat]
        positive = sum(sat[u] >= 4 for u in answered)
        return dict(n=n, stamp_users=sum(stamps[u]>0 for u in ids),
                    mean_stamps=round(mean(stamps[u] for u in ids),2),
                    median_stamps=median(stamps[u] for u in ids),
                    multiple_days=sum(len(days[u])>=2 for u in ids),
                    respondents=len(answered), response_pct=pct(len(answered),n),
                    satisfied=positive, satisfied_pct=pct(positive,len(answered)))
    age_order = ['20歳未満','20代','30代','40代','50代','60代','70歳以上','形式不明・未回答']
    age_groups = {a:[u for u,r in users.items() if age_band(r['年代'])==a] for a in age_order}
    # Do not emit tiny groups or their derived percentages. No gender inference.
    sex_groups = {s:[u for u,r in users.items() if r['性別'].strip()==s] for s in ['男性','女性']}
    other = [u for u,r in users.items() if r['性別'].strip() not in ('男性','女性')]
    if other: sex_groups['その他・未回答'] = other
    def grouped(groups):
        result = {}
        for k,v in groups.items():
            if not v: continue
            if len(v)<10:
                result[k]={'n':'10人未満（非表示）'}
                continue
            m=metrics(v)
            if 0 < m['satisfied'] < 10:
                m['satisfied']='少数のため非表示'
                m['satisfied_pct']=None
            result[k]=m
        return result
    matched = {f['kind']:len({r[f['id_column']].strip() for r in tables[f['kind']]}-set(users)) for f in files}
    mismatch = {k:sum(int(r[col])!=counts[u] for u,r in users.items()) for k,col,counts in [('stamps','スタンプ獲得数',stamps),('rewards','特典獲得数',rewards)]}
    distribution = Counter({k:0 for k in ['0件','1〜3件','4〜6件','7件以上']})
    for u in users:
        n=stamps[u]; distribution['0件' if n==0 else '1〜3件' if n<=3 else '4〜6件' if n<=6 else '7件以上']+=1
    for f in files:
        f['unchanged'] = hashlib.sha256((SOURCE/f['name']).read_bytes()).hexdigest()==f['sha256_before']
    assert all(f['unchanged'] for f in files)
    result = dict(analyzed_utc=datetime.now(timezone.utc).isoformat(),
        files=[{k:f[k] for k in ['name','rows','unique_users','duplicate_complete_rows','missing_ids','sha256_before','unchanged']} for f in files],
        all=metrics(list(users)), age=grouped(age_groups), gender=grouped(sex_groups),
        stamp_date_range=[min(dates),max(dates)], stamp_rows=len(tables['stamps']),
        reward_rows=len(tables['rewards']), reward_users=len(rewards),
        unique_spots=len(set().union(*spots.values())), distribution=dict(distribution),
        satisfaction=dict(Counter(r[sat_col] for r in after.values())),
        respondent_activity={'answered':metrics([u for u in users if u in sat]),'unanswered':metrics([u for u in users if u not in sat])},
        correlations={'stamp_satisfaction':spearman([stamps[u] for u in sat],[sat[u] for u in sat])},
        unmatched_users=matched, count_mismatch=mismatch)
    out=ROOT/'artifacts/audience-trends-summary.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('5 CSV analyzed; only aggregate results saved; source hashes unchanged.')
    return result

def plot(result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font = FontProperties(fname='C:/Windows/Fonts/meiryo.ttc')
    plt.rcParams.update({'font.family':font.get_name(),'font.size':11,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#ccd2d8'})
    fig,axes=plt.subplots(2,2,figsize=(13,9))
    fig.subplots_adjust(left=.12,right=.95,top=.86,bottom=.13,hspace=.48,wspace=.4)
    fig.suptitle('提供サンプル500人の構成・活動・満足度',fontsize=21,x=.08,ha='left',y=.96)
    fig.text(.08,.91,'スタンプ記録：2026年10月1〜20日 ／ 満足度は参加後回答者287人のみ',fontsize=11,color='#475569')
    ages=list(result['age'])
    def bars(ax,labels,values,title,fmt,xmax):
        ax.barh(labels,values,color='#36778b',height=.58)
        ax.invert_yaxis(); ax.set_xlim(0,xmax)
        ax.set_title(title,loc='left',fontsize=13,pad=13)
        ax.tick_params(axis='y',length=0)
        for i,v in enumerate(values): ax.text(v+xmax*.02,i,fmt.format(v),va='center',fontsize=11)
        ax.set_axisbelow(True); ax.grid(axis='x',alpha=.13)
    bars(axes[0,0],ages,[result['age'][a]['n'] for a in ages],'登録者の年代構成（人）','{:.0f}',155)
    bars(axes[0,1],ages,[result['age'][a]['mean_stamps'] for a in ages],'1人当たりスタンプ履歴（件）','{:.2f}',8)
    sat_ages=[a for a in ages if result['age'][a]['satisfied_pct'] is not None]
    bars(axes[1,0],[f"{a}（回答{result['age'][a]['respondents']}人）" for a in sat_ages],
         [result['age'][a]['satisfied_pct'] for a in sat_ages],'回答者に占める満足の割合（%）','{:.1f}%',100)
    labels=['大変満足','やや満足','普通','やや不満','大変不満']
    bars(axes[1,1],labels,[result['satisfaction'][a] for a in labels],'参加後アンケートの満足度（人）','{:.0f}',130)
    fig.text(.08,.065,'満足＝「大変満足」＋「やや満足」。スタンプ平均の分母は各年代の全登録者（履歴なしを0件）。',fontsize=10)
    fig.text(.08,.035,'年代差は未調整の観測値。Webの好み・実訪問・再訪効果を示すものではありません。20歳未満の満足割合は少数のため非表示。',fontsize=9,color='#475569')
    fig.savefig(ROOT/'outputs/sample-data-trends.png',dpi=160,facecolor='white')
    plt.close(fig)

if __name__=='__main__':
    plot(analyze())
