"""Probe gallery isolation from a separate optimizer process, using synthetic markers."""
import argparse, hashlib, json, subprocess, sys, urllib.error, urllib.request
from pathlib import Path
from engine import media


def probe(url,dev,sealed,query):
    def get(path):
        try:
            with urllib.request.urlopen(url+path,timeout=30) as r:return r.status,r.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    code,body=get('/api/evals/gallery/search?q=Development');authorized=json.loads(body) if code==200 else []
    hidden_code,hidden=get('/api/evals/gallery/search?q='+query)
    good,content=get('/api/evals/gallery/clip/'+dev);bad,_=get('/api/evals/gallery/clip/'+sealed)
    result=dict(process_role='optimizer',development_search=code==200 and len(authorized)==1,sealed_search_denied=hidden_code==200 and json.loads(hidden)==[],
        development_direct=good==200,sealed_direct_denied=bad==403,development_media_sha256=hashlib.sha256(content).hexdigest() if good==200 else None,
        sealed_catalog_or_media_read=False,scope='Application/API capability; not an OS sandbox against arbitrary same-user code')
    print(json.dumps(result));return result


def run(out,app):
    from editing_replay import Editor
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);ws=out/'workspace';ws.mkdir();sealer=out/'independent-scorer';sealer.mkdir()
    for directory,color in ((ws,'green'),(sealer,'magenta')):
        media.ff('-f','lavfi','-i',f'color=c={color}:s=360x640:r=30:d=1','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',1,*media.video_encoder_args(),'-c:a','aac','-ar',48000,directory/'marker.mp4')
    # The actual held-out content marker and catalog remain solely with the scorer.
    (sealer/'labels.json').write_text(json.dumps({'marker':'SYNTHETIC_SEALED_CONTENT_NOT_FOR_OPTIMIZER','clip_id':'known-sealed-id'}))
    media.write_json(ws/'evaluation-access.json',dict(role='optimizer',partition='development',clips=[dict(id='authorized-development',label='Development synthetic marker',file='marker.mp4',sha256=media.sha(ws/'marker.mp4'))]))
    editor=Editor(app,out)
    try:
        command=[sys.executable,str(Path(__file__).resolve()),'--probe',editor.url,'--dev','authorized-development','--sealed','known-sealed-id','--query','SEALED']
        p=subprocess.run(command,capture_output=True,check=True,**media.launch_options());(out/'optimizer-process.log').write_bytes(p.stdout+p.stderr);result=json.loads(p.stdout)
        trace=[json.loads(line) for line in (ws/'evaluation-reads.jsonl').read_text().splitlines()]
        actual_reads=[r['sha256'] for r in trace if r['allowed'] and r.get('sha256')]
        result.update(actual_read_digests=actual_reads,all_reads_authorized=actual_reads==[media.sha(ws/'marker.mp4')],
            sealed_marker_in_optimizer_catalog_or_trace=any('SYNTHETIC_SEALED_CONTENT_NOT_FOR_OPTIMIZER' in p.read_text(errors='ignore') for p in ws.rglob('*') if p.is_file() and p.suffix in ('.json','.jsonl')),
            real_final_cohort_touched=False)
        if not all(result[k] for k in ('development_search','sealed_search_denied','development_direct','sealed_direct_denied','all_reads_authorized')) or result['sealed_marker_in_optimizer_catalog_or_trace']:raise AssertionError(result)
        media.write_json(out/'results.json',result);return result
    finally:editor.stop()


def main():
    p=argparse.ArgumentParser();p.add_argument('--probe');p.add_argument('--dev');p.add_argument('--sealed');p.add_argument('--query');p.add_argument('--out',type=Path);p.add_argument('--app',type=Path,default=Path(__file__).parent);a=p.parse_args()
    if a.probe:probe(a.probe,a.dev,a.sealed,a.query)
    else:print(json.dumps(run(a.out,a.app),indent=2))


if __name__=='__main__':main()
