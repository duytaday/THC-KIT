"""Inventory the owner-declared corpus without inventing creators, labels, or holdouts."""
import argparse,json
from pathlib import Path
from engine.references import inventory
from engine import media
import learning

def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--profiles',type=Path);p.add_argument('--legacy-manifest',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    inv=inventory(a.directory,50);assets={}
    legacy=json.loads(a.legacy_manifest.read_text(encoding='utf-8')) if a.legacy_manifest else {};prior={r['sha256']:r for r in sorted(legacy.get('assets',[]),key=lambda r:bool(r.get('presenter_verified'))) if r.get('id','').startswith('owner-ref-')}
    for r in inv['records']:
        if not r.get('analyzable'):continue
        h=r['sha256'];id_='reference-'+h[:20]+'-'+str(len(assets));asset=dict(id=id_,kind='reference',name=Path(r['path']).name,path=r['path'],duration=r['duration'],analysis={})
        if a.profiles and (a.profiles/(h+'.json')).exists():asset['analysis']=json.loads((a.profiles/(h+'.json')).read_text(encoding='utf-8'))
        old=prior.get(h,{});in_scope=bool(old.get('presenter_verified')) and not old.get('exclusion_reason') and not r.get('duplicate_of')
        asset['prior_curation']=dict(family=old.get('family_id'),exclusion=old.get('exclusion_reason'),presenter_candidate=old.get('presenter_verified',False),basis='Legacy selected-frame curation; not continuous temporal or hearing approval') if old else None
        asset['training']=learning.intake(asset,dict(include=in_scope if prior else True,permission='User declared ownership and explicitly requested training in this chat; recorded 2026-11-11. No redistribution permission inferred.',creator=old.get('creator_id') if old.get('creator_identity_verified') else '',series='',family=old.get('family_id',''),group_reviewed=False,presenter_verified=bool(old.get('presenter_verified')),content_evidence='Legacy selected-frame curation '+str(a.legacy_manifest) if old.get('presenter_verified') else '',reviewer='intake-only; no new editorial labels approved'))
        assets[id_]=asset
    media.write_json(a.out/'inventory.json',inv);media.write_json(a.out/'intake-workspace.json',dict(assets=assets,jobs={},exports=[]));report=learning.export(assets,a.out/'dataset-v001')
    summary={k:v for k,v in report.items() if k not in ('rows','sources','excluded')};summary['candidate_unlabeled_moments']=sum(len(a['training']['moments']) for a in assets.values());summary['prior_content_families']=len({x['prior_curation']['family'] for x in assets.values() if x.get('prior_curation')});summary['prior_presenter_candidate_families']=len({x['training']['family'] for x in assets.values() if x['training'].get('presenter_verified') and x['training'].get('include')});summary['requested']=50;summary['legacy_pilot']='40 steps completed previously; target-derived inference flags invalidated quality benchmark. Old adapter remains quarantined.';media.write_json(a.out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
