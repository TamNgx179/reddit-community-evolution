"""Development-only measurement sensitivity; never optimize forecasting scores."""

from collections import Counter
import json
from pathlib import Path

from sklearn.metrics import adjusted_rand_score

from reddit_sna.detection.leiden import detect_snapshots
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.pipelines.study_samples import load_month, read_csv
from reddit_sna.tracking.ged import importance, transitions


def measurement_diagnostics(month_directories, output):
    """Describe fixed threshold/resolution alternatives on development only.

    Configurations and dates were chosen before final evaluation. They produce
    different operational targets/partitions, not directly comparable predictor
    scores. None is eligible to replace the primary reference automatically.
    """
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    threshold_rows=[]
    source_months=['2016-12','2017-01','2017-02','2017-03','2017-04','2017-05']
    from reddit_sna.contracts import next_month
    for month in source_months:
        following=next_month(month)
        source,edges=load_month(month_directories[month],month)
        target,next_edges=load_month(month_directories[following],following)
        left,right=importance(source,edges),importance(target,next_edges)
        canonical=transitions(source,target,left,right)[1]
        for threshold in (.4,.5,.6):
            _,labels,reasons,_=transitions(source,target,left,right,threshold,threshold,.1)
            threshold_rows.append(dict(feature_month=month,label_month=following,alpha=threshold,beta=threshold,
                source_communities=len(source),support=dict(Counter(e.value if e else 'unresolved' for e in labels.values())),
                reasons=dict(Counter(reasons.values())),changed_from_primary=sum(labels[k]!=canonical[k] for k in source)))
    month='2016-03'  # Largest month in the existing training-record inventory.
    source=Path(month_directories[month])
    graph=json.loads((source/'snapshots.json').read_text(encoding='utf-8'))
    canonical={r['user_id']:r['community_id'] for r in read_csv(source/f'memberships/{month}/membership-seed0.csv')}
    resolution=[]
    for gamma in (.5,1.5):
        destination=output/f'gamma-{gamma:g}'
        result=detect_snapshots(source/'snapshots',destination,graph['identity_scope'],seeds=(0,),gamma=gamma,
            graph_protocol=graph['graph_protocol'],expected_months=[month])
        alternative={r['user_id']:r['community_id'] for r in read_csv(destination/f'{month}/membership-seed0.csv')}
        if alternative.keys()!=canonical.keys():
            raise ValueError('Resolution diagnostic lost reply endpoints')
        users=sorted(canonical)
        resolution.append(dict(gamma=gamma,month=month,
            ari_against_gamma1=float(adjusted_rand_score([canonical[u] for u in users],[alternative[u] for u in users])),
            detection=result))
    result=dict(scope='development-only measurement sensitivity; no forecasting selection',
        thresholds=threshold_rows,resolutions=resolution,primary_reference_changed=False)
    json_write(output/'measurement.json',result)
    return result
