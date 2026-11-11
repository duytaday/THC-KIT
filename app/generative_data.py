"""Source-bound private generative-video clips; separate from editorial selector labels."""
import argparse,json,subprocess
from pathlib import Path
from engine import media

def candidates(manifest,out):
    root=Path(out);root.mkdir(parents=True,exist_ok=False);m=json.loads(Path(manifest).read_text(encoding='utf-8'));assets={a['id']:a for a in m['assets']};rows=[]
    for id_,times in {'owner-ref-005':[4.9,18.4,48.2,50.5],'owner-ref-008':[2,7,13,19],'owner-ref-013':[2,7,12,17],'owner-ref-016':[1,3.5,6],'owner-ref-022':[4,15,28,40],'owner-ref-024':[4.5,8,16,30,40]}.items():
        a=assets[id_]
        for t in times:
            file=root/(id_+'-'+str(t)+'.jpg');media.ff('-ss',t,'-i',a['path'],'-frames:v','1','-vf','scale=240:426:force_original_aspect_ratio=decrease,pad=240:426:(ow-iw)/2:(oh-ih)/2',file);rows.append(dict(id=id_,time=t,path=str(file)))
    media.write_json(root/'candidates.json',rows)
    # A local HTML overview preserves each image's source/time label, no external assets.
    (root/'index.html').write_text('<meta charset="utf-8"><style>body{background:#eee;display:flex;flex-wrap:wrap}figure{margin:8px}img{width:180px}</style>'+''.join(f'<figure><img src="{Path(r["path"]).name}"><figcaption>{r["id"]} · {r["time"]}s</figcaption></figure>' for r in rows),encoding='utf-8')

def prepare(plan,manifest,out):
    root=Path(out);root.mkdir(parents=True,exist_ok=False);(root/'videos').mkdir();m=json.loads(Path(manifest).read_text(encoding='utf-8'));assets={a['id']:a for a in m['assets']};rights={r['id']:r for r in m['rights']};p=json.loads(Path(plan).read_text(encoding='utf-8'));rows=[]
    for i,shot in enumerate(p['shots']):
        a=assets[shot['source']];grant=rights[a['rights_id']]
        if grant.get('revoked') or not grant.get('grants',{}).get('train_commercial',{}).get('allowed'):raise ValueError('Training permission missing for '+a['id'])
        if media.sha(a['path'])!=a['sha256']:raise ValueError('Reference bytes changed.')
        start=shot['start'];duration=shot.get('duration',2.125);source_duration=shot.get('source_duration',duration)
        if start<0 or source_duration<=0 or start+source_duration>a['duration_ms']/1000:raise ValueError('Training range outside source.')
        file=root/'videos'/f'shot-{i:03d}.mp4';filters=[]
        if shot.get('crop'):filters.append('crop='+':'.join(map(str,shot['crop'])))
        filters+=[f'setpts=(PTS-STARTPTS)*{duration/source_duration}', 'tpad=stop_mode=clone:stop_duration=0.5','fps=8','scale=256:256:force_original_aspect_ratio=increase','crop=256:256','setsar=1']
        media.ff('-ss',start,'-t',source_duration,'-i',a['path'],'-an','-vf',','.join(filters),'-frames:v','17','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',file)
        rows.append(dict(id=f'shot-{i:03d}',video=str(file.relative_to(root)).replace('\\','/'),video_sha256=media.sha(file),caption=shot['caption'],source_sha256=a['sha256'],source_id=a['id'],family=a['family_id'],source_range=[start,start+source_duration],output_duration=duration,retime_factor=duration/source_duration,crop=shot.get('crop'),role=shot.get('role','train'),annotation_kind='agent_visual_experimental',review_scope='source first/middle/last decoded frames; no hearing or product-capability certification',caption_heard=False,rights_id=a['rights_id'],permission=grant['grants']['train_commercial']))
    families={}
    for r in rows:
        if r['family'] in families and families[r['family']]!=r['role']:raise ValueError('Source-family split leakage.')
        families[r['family']]=r['role']
    package=dict(schema_version=1,task='video_diffusion_lora',owner_training_authorized=True,private_only=True,source_manifest_sha256=media.sha(manifest),rows=rows,family_split=families,creator_split_verified=False,evaluation_scope='development holdout; no unseen-creator or independent finished-episode gain claim',synthesize_presenter_voice=False,product_proof=False,generated_disclosure_required=True)
    media.write_json(root/'generative-dataset.json',package);media.write_json(root/'dataset-metadata.json',dict(title='Talking Head Cutroom Generative Pilot',id='duytruyenthong/talking-head-cutroom-generative-pilot-20261111',licenses=[{'name':'other'}]))
    print(json.dumps(dict(clips=len(rows),training_clips=sum(r['role']=='train' for r in rows),hash=media.sha(root/'generative-dataset.json')),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['candidates','prepare']);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--plan',type=Path);a=p.parse_args()
    if a.action=='candidates':candidates(a.manifest,a.out)
    else:prepare(a.plan,a.manifest,a.out)
