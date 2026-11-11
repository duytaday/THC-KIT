"""Owner-authorized comparable cohorts only. Public discovery is never training data."""
import argparse
import json
import math
from datetime import date
from collections import defaultdict
from video_kit import read,write


def shortlist(rows,metric='shares_per_1000_views',window=28):
    if metric not in ('shares_per_1000_views','completion_rate') or window not in (7,28):raise ValueError('Lock metric and 7/28-day window before selection')
    groups=defaultdict(list);results=[];seen=set()
    for source in rows:
        r=dict(source)
        if r['video_id'] in seen:raise ValueError('Duplicate canonical video ID')
        seen.add(r['video_id'])
        r.update(engagement_status='engagement_unverified',shortlist=False,control=False,selection_metric=None,reason='Owner-authorized comparable analytics missing')
        try:
            start=date.fromisoformat(r.get('window_start',''));end=date.fromisoformat(r.get('window_end',''));published=date.fromisoformat(r.get('published_date',''))
            correct_window=start==published and (end-start).days==window
        except ValueError:correct_window=False
        if r.get('analytics_authorized') is True and r.get('analytics_source') and r.get('window_days')==window and correct_window:
            numerator=r.get('shares') if metric=='shares_per_1000_views' else r.get('completed_views')
            denominator=r.get('views') if metric=='shares_per_1000_views' else r.get('play_starts')
            numeric=lambda x:type(x) in (int,float) and math.isfinite(x) and x>=0
            if numeric(numerator) and numeric(denominator) and denominator>0 and (metric!='completion_rate' or numerator<=denominator):
                required=('creator_id','format','duration_bin','window_start','window_end')
                if all(r.get(k) for k in required):
                    value=numerator/denominator*(1000 if metric=='shares_per_1000_views' else 1)
                    r['selection_metric']={'name':metric,'numerator':numerator,'denominator':denominator,'value':value}
                    key=tuple(r[k] for k in required[:3])+(window,)
                    groups[key].append(r)
        results.append(r)
    for group in groups.values():
        if len(group)<10:
            for r in group:r['reason']=f'Only {len(group)} comparable videos; need >=10'
            continue
        ranked=sorted(group,key=lambda r:(-r['selection_metric']['value'],r['video_id']))
        count=math.ceil(len(ranked)/4)
        for i,r in enumerate(ranked):
            r.update(engagement_status='verified_owned_cohort',shortlist=i<count,control=len(ranked)//2<=i<len(ranked)//2+count,reason=f'Rank {i+1}/{len(ranked)} by locked {metric}; ties ordered by canonical ID, not causal effect')
    return {'metric':metric,'window_days':window,'candidates':results,'discovered':len(results),'engagement_verified':sum(r['engagement_status']=='verified_owned_cohort' for r in results),'shortlisted':sum(r['shortlist'] for r in results),'claim':'No causal retention claim; content and four rights scopes must be reviewed separately.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--metric',default='shares_per_1000_views');p.add_argument('--window',type=int,default=28);a=p.parse_args()
    result=shortlist(read(a.input),a.metric,a.window);write(a.out,result);print(json.dumps({k:v for k,v in result.items() if k!='candidates'},ensure_ascii=False))
