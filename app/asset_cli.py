"""Local stock library commands; used by app/cli.py assets and compact Library UI."""
import argparse,json,os,sys,sqlite3,contextlib
from pathlib import Path
from asset_store import Store

def default_root():return Path(os.environ.get('THC_ASSET_LIBRARY','D:/.codex/workspaces/talking-head-support/asset-library-v001'))

@contextlib.contextmanager
def collector(root):
    Path(root).mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(Path(root)/'collector.sqlite3',timeout=2)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS writer(id INTEGER PRIMARY KEY)');db.commit();db.execute('BEGIN IMMEDIATE');yield
    finally:db.rollback();db.close()

def run(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--library',type=Path,default=default_root())
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('discover');p.add_argument('--pages',type=int,default=1);p.add_argument('--per-query',type=int,default=50);p.add_argument('--queries',type=Path,help='Optional JSON mapping of known categories to concrete scene queries')
    p=sub.add_parser('collect');p.add_argument('--target',type=int,default=20);p.add_argument('--max-attempts',type=int);p.add_argument('--budget-gb',type=float,default=40);p.add_argument('--reserve-gb',type=float,default=30)
    sub.add_parser('status')
    p=sub.add_parser('search');p.add_argument('query');p.add_argument('--limit',type=int,default=10)
    p=sub.add_parser('index');p.add_argument('--force',action='store_true')
    p=sub.add_parser('embed');p.add_argument('--python',required=True);p.add_argument('--device',choices=['cpu','cuda:0'],default='cpu');p.add_argument('--limit',type=int)
    p=sub.add_parser('review-batch');p.add_argument('document',type=Path);p.add_argument('--evidence',type=Path,required=True)
    p=sub.add_parser('dataset');p.add_argument('--track',choices=['A','B'],required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--source',type=Path)
    p=sub.add_parser('plan');p.add_argument('context',type=Path);p.add_argument('--mode',choices=['B0','B1'],default='B1')
    p=sub.add_parser('catalog');p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('dedup-audit');p.add_argument('--upgrade-fingerprints',action='store_true')
    p=sub.add_parser('model-prepare');p.add_argument('dataset',type=Path);p.add_argument('--steps',type=int,default=4);p.add_argument('--max-tokens',type=int,default=1536);p.add_argument('--creator',default='local-experimental');p.add_argument('--style',default='locked-native');p.add_argument('--cycle',default='local-development-v1')
    p=sub.add_parser('model-train');p.add_argument('run_id');p.add_argument('--python',required=True);p.add_argument('--resume',action='store_true');p.add_argument('--stop-after',type=int)
    p=sub.add_parser('model-evaluate');p.add_argument('run_id');p.add_argument('--python',required=True);p.add_argument('--limit',type=int,default=4)
    p=sub.add_parser('model-rollback');p.add_argument('--track',choices=['A','B'],required=True);p.add_argument('--base-revision',type=int,required=True);p.add_argument('--creator',default='local-experimental');p.add_argument('--style',default='locked-native')
    sub.add_parser('models')
    args=parser.parse_args(argv)
    try:
        if args.action in ('discover','collect'):
            from asset_ingest import Ingestor
            importer=Ingestor(args.library,**({k:getattr(args,k) for k in ('budget_gb','reserve_gb')} if args.action=='collect' else {}))
            try:
                with collector(args.library):
                    if args.action=='discover':
                        if not 1<=args.pages<=10 or not 1<=args.per_query<=50:raise ValueError('Use1–10 pages and1–50 results per query')
                        queries=json.loads(args.queries.read_text(encoding='utf-8-sig')) if args.queries else None
                        importer.discover(args.per_query,args.pages,queries);result=importer.store.export()
                    else:
                        if not 1<=args.target<=10000:raise ValueError('Use a bounded source target')
                        result=importer.run(args.target,args.max_attempts)
            finally:importer.store.close()
        elif args.action.startswith('model-') or args.action=='models':
            import asset_models
            if args.action=='models':result=asset_models.registry(args.library)
            elif args.action=='model-prepare':result=asset_models.prepare(args.library,args.dataset,steps=args.steps,max_tokens=args.max_tokens,creator=args.creator,style=args.style,cycle=args.cycle)
            elif args.action=='model-train':result=asset_models.train(args.library,args.run_id,args.python,resume=args.resume,stop_after=args.stop_after)
            elif args.action=='model-evaluate':
                import asset_evals
                result=asset_evals.evaluate(args.library,args.run_id,args.python,args.limit)
            else:result=asset_models.rollback(args.library,args.track,args.base_revision,args.creator,args.style)
        elif args.action=='plan':
            import asset_planner,asset_retrieval
            ctx=json.loads(args.context.read_text(encoding='utf-8'));result=asset_planner.rules(ctx,asset_retrieval.rank_descriptors(ctx) if args.mode=='B1' else None)
        else:
            store=Store(args.library)
            if args.action=='status':result=store.stats()
            elif args.action=='dedup-audit':
                import asset_audit
                with collector(args.library):result=asset_audit.dedup(store,args.upgrade_fingerprints)
            elif args.action=='catalog':
                import asset_planner,asset_retrieval,asset_learning
                components=[]
                for a in asset_retrieval.eligible(store):
                    c=asset_planner.component(a);w=a['usable_windows'][0]
                    c.update(offset=w['source_in'],max_source_duration=w['source_out']-w['source_in'],permission_evidence='User-directed third-party illustration; source declaration: '+a['source_url']+' · '+str(a['license'].get('name'))+'; training rights not inferred')
                    c['tags']=[a['category']];c['description']=asset_retrieval.description(a);components.append(c)
                asset_learning.write(args.out,dict(format='thc-stock-component-catalog-v1',components=components,training_started=False))
                result=dict(path=str(args.out.resolve()),components=len(components),use='Pass this catalog to auto-edit --components; native renderer, recorded voice preserved, stock muted',human_approval=False)
            elif args.action=='dataset':
                import asset_learning
                if args.track=='B' and not args.source:raise ValueError('Track B needs the existing reconstruction dataset path')
                with collector(args.library):result=asset_learning.prepare_a(store,args.out) if args.track=='A' else asset_learning.prepare_b(args.source,args.out)
            elif args.action=='embed':
                import asset_embeddings
                result=asset_embeddings.build(store,args.python,args.device,args.limit)
            elif args.action=='review-batch':
                import asset_quality,asset_retrieval
                with collector(args.library):result=asset_quality.review(store,json.loads(args.document.read_text(encoding='utf-8')),args.evidence)
                result['retrieval']=asset_retrieval.build(store)
            else:
                import asset_retrieval
                result=asset_retrieval.build(store,args.force) if args.action=='index' else asset_retrieval.search(store,args.query,args.limit)
            store.close()
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except KeyboardInterrupt:
        print(json.dumps(dict(status='INTERRUPTED',resume='Same collect command resumes checkpoints/partial files; verified sources are not downloaded again.')));return 130
    except Exception as error:
        print(json.dumps(dict(status='ERROR',error=str(error)),ensure_ascii=False));return 3

if __name__=='__main__':sys.exit(run())
