"""Optional retrieval experiment gates. Dense is OFF until a real benchmark wins."""
import argparse
import json
from video_kit import read


def rrf(rankings,k=60):
    scores={}
    for ranking in rankings:
        for rank,key in enumerate(dict.fromkeys(ranking),1): scores[key]=scores.get(key,0)+1/(k+rank)
    return sorted(scores,key=lambda key:(-scores[key],key))


def dense_allowed(report):
    return (report.get('data_class')=='production' and report.get('locked_queries') is True
        and report.get('n',0)>=20 and report.get('rights_errors')==0
        and report.get('citation_errors')==0 and report.get('hybrid_recall_at_3',0)>report.get('fts_recall_at_3',1)
        and report.get('p95_ms',float('inf'))<=report.get('locked_latency_budget_ms',0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--benchmark');a=p.parse_args()
    report=read(a.benchmark) if a.benchmark else {}
    print(json.dumps({'default':'hybrid' if dense_allowed(report) else 'fts5','dense_model_candidate':'intfloat/multilingual-e5-small','embedding_contract':{'query_prefix':'query: ','passage_prefix':'passage: ','normalize':True},'embeddings_built':False,'reason':'No dense model download or production benchmark implicitly triggered'}))
