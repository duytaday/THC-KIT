"""Local, rights-filtered reference index. Standard library; no media downloader."""
import argparse
import hashlib
import json
import math
import re
import sqlite3
import subprocess
import unicodedata
from pathlib import Path

SCHEMA = 1
SCOPES = ('view', 'index', 'train_commercial', 'distribute')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def norm(text):
    text = unicodedata.normalize('NFD', str(text).lower().replace('đ', 'd'))
    return ''.join(c for c in text if not unicodedata.combining(c))


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, encoding='utf-8', timeout=60)
    if p.returncode:
        raise ValueError('ffprobe failed: ' + p.stderr[-500:])
    data = json.loads(p.stdout)
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if not video:
        raise ValueError('No video stream')
    return {'duration_ms':round(float(data['format']['duration'])*1000), 'width':video['width'], 'height':video['height'], 'fps':video['avg_frame_rate'], 'audio':any(s['codec_type']=='audio' for s in data['streams'])}


def permission(right, scope):
    grant = right.get('grants', {}).get(scope, {})
    return right.get('revoked') is False and grant.get('allowed') is True and bool(grant.get('basis')) and bool(grant.get('date')) and bool(grant.get('purpose'))


def validate(manifest):
    if manifest.get('schema_version') != SCHEMA:
        raise ValueError('Unsupported schema_version')
    for key in ('assets', 'rights', 'segments'):
        ids = [r['id'] for r in manifest[key]]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate ' + key + ' IDs')
    rights = {r['id']:r for r in manifest['rights']}
    assets = {a['id']:a for a in manifest['assets']}
    for a in assets.values():
        if a['rights_id'] not in rights or a['role'] not in ('episode', 'style', 'technical') or not a.get('family_id'):
            raise ValueError('Invalid asset relation/role')
        if not re.fullmatch('[0-9a-f]{64}', a['sha256']):
            raise ValueError('Invalid asset SHA')
    for s in manifest['segments']:
        a = assets[s['asset_id']]
        if s['family_id'] != a['family_id'] or s['asset_sha256'] != a['sha256'] or s['rights_id'] != a['rights_id']:
            raise ValueError('Segment relation/hash mismatch: '+s['id'])
        if not all(type(s[k]) is int for k in ('t_in_ms','t_out_ms')) or not 0 <= s['t_in_ms'] < s['t_out_ms'] <= a['duration_ms']:
            raise ValueError('Segment time range invalid: '+s['id'])
        for key in ('lang','spoken_intent','visible_before','visible_during','visible_after','motion_parameters','editorial_reason','reviewer','recipe_id','motion_type','format'):
            if not s.get(key):
                raise ValueError('Missing segment '+key)
    return manifest


def scan(folder):
    folder = Path(folder)
    m = validate(read(folder/'references.json'))
    rights = {r['id']:r for r in m['rights']}
    errors = []
    probes = {}
    for a in m['assets']:
        path = Path(a['path'])
        try:
            if sha(path) != a['sha256']:
                raise ValueError('bytes changed; re-annotate asset')
            p = probe(path)
            if abs(p['duration_ms'] - a['duration_ms']) > 100:
                raise ValueError('duration changed')
            probes[a['id']] = p
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            errors.append({'asset_id':a['id'],'error':str(e)})
    valid = {a['id']:a for a in m['assets'] if a['id'] not in {e['asset_id'] for e in errors}}
    eligible = [s for s in m['segments'] if s['asset_id'] in valid and s.get('annotation_approved') is True and permission(rights[s['rights_id']], 'index')]
    # Rebuild in a transaction; deletes revoked/changed annotations and old FTS rows.
    db = sqlite3.connect(folder/'index.sqlite3')
    try:
        with db:
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS cards USING fts5(id UNINDEXED, text, tokenize="unicode61 remove_diacritics 2")')
            db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)')
            db.execute('DELETE FROM cards')
            for s in eligible:
                text = norm(' '.join(str(s[k]) for k in ('spoken_intent','visible_before','visible_during','visible_after','editorial_reason','motion_type','recipe_id')))
                db.execute('INSERT INTO cards(id,text) VALUES (?,?)',(s['id'],text))
            db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('manifest_hash',digest(m)))
            db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('schema_version',str(SCHEMA)))
    finally:
        db.close()
    families = {s['family_id'] for s in eligible}
    rag50 = {s['family_id'] for s in eligible if valid[s['asset_id']].get('engagement_verified') is True and valid[s['asset_id']].get('content_verified') is True and valid[s['asset_id']].get('data_class')=='production'}
    train = {a['family_id'] for a in valid.values() if a.get('data_class')=='production' and permission(rights[a['rights_id']], 'train_commercial')}
    result = {'schema_version':SCHEMA,'manifest_hash':digest(m),'assets_checked':len(m['assets']), 'probes':probes,'indexed_segments':len(eligible),'indexed_families':len(families),'rag50_eligible_families':len(rag50), 'train_rights_families':len(train),'errors':errors,'exact_duplicate_groups':[], 'near_duplicate_review':'Run fingerprint on authorized sources; family IDs remain provisional until reviewed.'}
    groups = {}
    for a in valid.values(): groups.setdefault(a['sha256'],[]).append(a['id'])
    result['exact_duplicate_groups'] = [g for g in groups.values() if len(g)>1]
    write(folder/'scan-result.json',result)
    return result


def search(manifest_path, motion, query, lang=None, format_=None, role='style', limit=3, data_class='production', exclude_families=()):
    path = Path(manifest_path)
    m = validate(read(path))
    assets = {a['id']:a for a in m['assets']}
    rights = {r['id']:r for r in m['rights']}
    # Check disk bytes too, not only the manifest/cache signature.
    allowed = {}
    for s in m['segments']:
        a = assets[s['asset_id']]
        if (a['role'] == role and a.get('data_class')==data_class and a['family_id'] not in exclude_families and s['motion_type']==motion and (not lang or s['lang']==lang) and (not format_ or s['format']==format_) and s.get('annotation_approved') is True and permission(rights[s['rights_id']], 'index')):
            if a['id'] not in allowed:
                allowed[a['id']] = sha(a['path']) == a['sha256']
    db = sqlite3.connect(path.parent/'index.sqlite3')
    try:
        signature = db.execute('SELECT value FROM meta WHERE key=?',('manifest_hash',)).fetchone()
        if not signature or signature[0] != digest(m):
            raise ValueError('Stale index: run scan after byte, rights or annotation changes')
        # Materialize the eligible corpus before FTS ranking; rank statistics cannot
        # be affected by a revoked, disallowed-language or held-out asset.
        selected = [s for s in m['segments'] if allowed.get(s['asset_id']) and assets[s['asset_id']]['role']==role and assets[s['asset_id']].get('data_class')==data_class and s['family_id'] not in exclude_families and s['motion_type']==motion and (not lang or s['lang']==lang) and (not format_ or s['format']==format_) and s.get('annotation_approved') is True and permission(rights[s['rights_id']], 'index')]
        db.execute('CREATE VIRTUAL TABLE temp.eligible USING fts5(id UNINDEXED, text)')
        for s in selected:
            row = db.execute('SELECT text FROM cards WHERE id=?',(s['id'],)).fetchone()
            if row: db.execute('INSERT INTO eligible VALUES (?,?)',(s['id'],row[0]))
        tokens = re.findall(r'\w+', norm(query))
        if not tokens: return {'verdict':'REVIEW','results':[],'reason':'Empty query'}
        expression = ' OR '.join('"'+t+'"' for t in tokens)
        hits = db.execute('SELECT id,bm25(eligible) FROM eligible WHERE eligible MATCH ? ORDER BY bm25(eligible),id LIMIT ?', (expression,min(3,max(1,limit)))).fetchall()
        lookup = {s['id']:s for s in selected}
        results = []
        for key, score in hits:
            s = lookup[key]; a = assets[s['asset_id']]
            results.append({**s, 'segment_id':s['id'],'data_class':a['data_class'],'asset_path':a['path'],'score':score,'citation':{'asset_id':a['id'],'sha256':a['sha256'],'t_in_ms':s['t_in_ms'],'t_out_ms':s['t_out_ms']},'reuse_media_allowed':permission(rights[s['rights_id']],'distribute')})
        return {'verdict':'CANDIDATES' if results else 'REVIEW','results':results,'backend':'fts5','manifest_hash':digest(m),'manifest_path':str(path.resolve()),'data_class':data_class,'exclude_families':sorted(exclude_families)}
    finally:
        db.close()


def revoke(folder, rights_id):
    folder = Path(folder); path = folder/'references.json'; m=read(path)
    right=next(r for r in m['rights'] if r['id']==rights_id)
    right['revoked']=True; right['version']=right.get('version',1)+1
    write(path,m)
    for model in (folder/'adapters').glob('*/provenance.json'):
        p=read(model)
        if rights_id in p.get('rights_ids',[]):
            p['status']='QUARANTINED_REVOKED_SOURCE';write(model,p)
    return scan(folder)


def add_source(folder, submission):
    """Import a creator-supplied local asset, never a URL download."""
    folder=Path(folder);m=read(folder/'references.json');item=read(submission)
    asset=item['asset'];right=item['rights'];segments=item['segments']
    if asset['sha256']!=sha(asset['path']):raise ValueError('Submission hash does not match local media')
    actual=probe(asset['path'])
    if abs(actual['duration_ms']-asset['duration_ms'])>100:raise ValueError('Submission duration mismatch')
    for row in [asset,right,*segments]:
        if not row.get('id'):raise ValueError('Submission IDs required')
    existing_assets={a['id']:a for a in m['assets']}
    if asset['id'] in existing_assets:
        prior_right=next((r for r in m['rights'] if r['id']==right['id']),None)
        prior_segments=[s for s in m['segments'] if s['asset_id']==asset['id']]
        if existing_assets[asset['id']]!=asset or prior_right!=right or sorted(prior_segments,key=lambda s:s['id'])!=sorted(segments,key=lambda s:s['id']):raise ValueError('Conflicting source revision; review ledger update explicitly')
        return scan(folder)
    candidate={**m,'assets':m['assets']+[asset],'segments':m['segments']+segments}
    existing_right=next((r for r in m['rights'] if r['id']==right['id']),None)
    if existing_right is not None and existing_right!=right:raise ValueError('Conflicting rights ledger')
    candidate['rights']=m['rights']+([] if existing_right else [right])
    validate(candidate)
    write(folder/'references.json',candidate)
    return scan(folder)


def fingerprint(path):
    """Near-duplicate candidates only; never automatically merges families."""
    p=probe(path); duration=p['duration_ms']/1000
    frame=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-vf',f'fps=1/{max(duration/8,.1)},scale=9:8,format=gray','-frames:v','8','-f','rawvideo','-'],capture_output=True,check=True,timeout=90).stdout
    hashes=[]
    for offset in range(0,len(frame)-71,72):
        x=frame[offset:offset+72]; bits=[x[r*9+c]>x[r*9+c+1] for r in range(8) for c in range(8)]
        hashes.append(f'{sum(int(b)<<i for i,b in enumerate(bits)):016x}')
    audio=None
    if p['audio']:
        audio=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-t','30','-vn','-ac','1','-ar','8000','-f','s16le','-'],capture_output=True,check=True,timeout=90).stdout
    return {'sha256':sha(path),'duration_ms':p['duration_ms'],'frame_dhash':hashes,'decoded_first30s_audio_sha256':hashlib.sha256(audio).hexdigest() if audio else None,'caution':'dHash is a candidate heuristic; decoded PCM hash is exact only, not a perceptual audio match. Review near duplicates manually.'}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    x=sub.add_parser('scan');x.add_argument('folder')
    x=sub.add_parser('search');x.add_argument('manifest');x.add_argument('motion');x.add_argument('query');x.add_argument('--lang');x.add_argument('--format');x.add_argument('--role',default='style',choices=['episode','style','technical']);x.add_argument('--data-class',default='production',choices=['production','fixture']);x.add_argument('--exclude-family',action='append',default=[])
    x=sub.add_parser('revoke');x.add_argument('folder');x.add_argument('rights_id')
    x=sub.add_parser('add-source');x.add_argument('folder');x.add_argument('submission')
    x=sub.add_parser('fingerprint');x.add_argument('file')
    a=p.parse_args()
    if a.cmd=='scan': result=scan(a.folder)
    elif a.cmd=='search': result=search(a.manifest,a.motion,a.query,a.lang,a.format,a.role,data_class=a.data_class,exclude_families=a.exclude_family)
    elif a.cmd=='revoke': result=revoke(a.folder,a.rights_id)
    elif a.cmd=='add-source': result=add_source(a.folder,a.submission)
    else: result=fingerprint(a.file)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    return 1 if result.get('errors') else 0


if __name__=='__main__':
    try: raise SystemExit(main())
    except (ValueError,OSError,KeyError,StopIteration,sqlite3.Error,subprocess.SubprocessError) as e:
        raise SystemExit('BLOCKED: '+str(e))
