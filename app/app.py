import tempfile, zipfile
import argparse, json, logging, os, re, secrets, shutil, sys, threading, traceback, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from workspace import Workspace, HERE, ACTIVE, ident

UI = HERE / "ui"
MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".mp4": "video/mp4",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".srt": "application/x-subrip",
    ".json": "application/json",
    ".woff2": "font/woff2",
    ".zip": "application/zip",
}
EXPORT_NAMES = {
    "mp4": "edit.mp4",
    "srt": "captions.srt",
    "qc": "qc.json",
    "project": "project.json",
    'voice_stem':'voice.wav','sfx_stem':'sfx.wav','music_stem':'music.wav','cues':'cue-sheet.json',
}


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_bytes(self, code, body, kind):
        self._response_code=code
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def result(self, value, code=200):
        self.send_bytes(
            code, json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8"
        )

    def local(self, mutating=False):
        if self.headers.get("Host") != self.server.host:
            raise ValueError("Invalid local host.")
        if mutating and self.headers.get("X-Cutroom-Key", "") != self.server.secret:
            raise ValueError("Reload this local workspace to reconnect.")
        if self.headers.get("Origin") not in (None, "http://" + self.server.host):
            raise ValueError("Only this local workspace can access the editor.")

    def file(self, f, label=None):
        size = f.stat().st_size
        start = 0
        end = size - 1
        code = 200
        header = self.headers.get("Range")
        if header:
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
            if not m or not any(m.groups()):
                return self.result({"error": "Invalid byte range"}, 416)
            if m[1]:
                start = int(m[1])
                end = min(end, int(m[2])) if m[2] else end
            else:
                start = max(0, size - int(m[2]))
            if start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            code = 206
        self.send_response(code)
        self.send_header("Content-Type", MIME.get(f.suffix, "application/octet-stream"))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("X-Content-Type-Options", "nosniff")
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if label:
            self.send_header(
                "Content-Disposition",
                "attachment; filename*=UTF-8''" + urllib.parse.quote(label, safe=""),
            )
        self.end_headers()
        with f.open("rb") as reader:
            reader.seek(start)
            remaining = end - start + 1
            while remaining:
                data = reader.read(min(remaining, 512 * 1024))
                if not data:
                    break
                self.wfile.write(data)
                remaining -= len(data)

    def do_GET(self):
        try:
            self.local()
            u = urllib.parse.urlsplit(self.path)
            p = u.path
            ws = self.server.ws
            if p == "/api/state":
                return self.result({**ws.snapshot(), "key": self.server.secret})
            if p=='/api/evals/gallery/search':
                return self.result(ws.evaluation_access.search(urllib.parse.parse_qs(u.query).get('q',[''])[0]))
            if p.startswith('/api/evals/gallery/clip/'):
                return self.file(ws.evaluation_access.clip(p.rsplit('/',1)[-1]))
            if p == '/api/components':
                from components import inventory
                return self.result(inventory())
            if p.startswith('/benchmarks/'):
                _,_,id_,name=p.split('/')
                if not re.fullmatch(r'[a-f0-9]{32}',id_) or name not in ('index.html','review.js','review-data.json','report.vi.md','results.json') and not re.fullmatch(r'(video|reference)-\d+\.mp4',name):raise ValueError('Unknown benchmark file')
                return self.file(ws.root/'benchmarks'/id_/name)
            if p.startswith('/artifacts/'):
                _,_,id_,kind=p.split('/');record=ws.data.get('artifacts',{})[id_]
                name={'preview':'preview.mp4','thumb':'thumbnail.jpg','source':'scene.json','timeline':'timeline.json'}[kind]
                return self.file(Path(record['folder'])/name,(record['plan']['title']+'-'+str(record['version'])+Path(name).suffix) if 'download' in urllib.parse.parse_qs(u.query) else None)
            if p.startswith('/animations/'):
                _,_,id_,kind=p.split('/');record=ws.data['animation_library'][id_]
                return self.file(Path(record['folder'])/({'preview':'preview.mp4','template':'template.json'}[kind]))
            if p.startswith('/openings/'):
                _,_,id_,kind=p.split('/');record=ws.data.get('opening_auditions',{})[id_]
                return self.file(Path(record['folder'])/{'host':'host.mp4','proof':'proof.mp4','receipt':'receipt.json'}[kind])
            if p.startswith('/generated/'):
                _,_,run_id,index=p.split('/');run=ws.data['generative_runs'][run_id];output=run['receipt']['outputs'][int(index)]
                return self.file(Path(run['folder'])/output['file'])
            if p in ('/sounds/click.wav','/sounds/slide.wav','/sounds/chime.wav'):
                return self.file(HERE/'sounds'/Path(p).name)
            if p.startswith("/assets/"):
                _, _, aid, view = p.split("/")
                assert view in ("thumb", "media")
                a = ws.data["assets"][aid]
                ws.evaluation_access.asset(a)
                f = Path(a["path"])
                return self.file(ws.root/'assets'/(aid+'.jpg') if view == "thumb" else f)
            if p == "/downloads/latest.zip":
                # Build one archive at a time, using disk space instead of retaining video bytes in memory.
                with ws.archive_lock:
                    with ws.lock:
                        latest = {e["job"]: dict(e) for e in ws.data["exports"]}
                    requested = urllib.parse.parse_qs(u.query).get("jobs")
                    if requested:
                        chosen = set(requested[0].split(","))
                        latest = {k: v for k, v in latest.items() if k in chosen}
                    if not latest:
                        raise ValueError("Render a recording first.")
                    with tempfile.TemporaryDirectory(dir=ws.root / "work") as work:
                        dest = Path(work) / "batch.zip"
                        with zipfile.ZipFile(dest, "w", allowZip64=True) as archive:
                            for entry in latest.values():
                                safe = (
                                    re.sub(
                                        r"[^\w .-]", "_", Path(entry["name"]).stem, flags=re.UNICODE
                                    )[:75].strip(" .")
                                    or "Clip"
                                )
                                sub = "Edit " + entry["id"][:8] + " - " + safe + "/"
                                for name in EXPORT_NAMES.values():
                                    source=Path(entry['folder'])/name
                                    if not source.exists() and name=='qc.json':source=Path(entry['folder'])/'edit-review.json'
                                    if source.exists():archive.write(source,sub+name)
                        return self.file(dest, "Cutroom-latest-edits.zip")
            if p.startswith("/exports/"):
                _, _, eid, kind = p.split("/")
                entry = ws.export(eid)
                if kind=='hook':
                    import hook_review
                    with ws.archive_lock:f=hook_review.render(entry)
                    return self.file(f)
                if kind in ('audition-voice','audition-voice_sfx','audition-full'):
                    import audition
                    with ws.archive_lock:f=audition.render(Path(entry['folder']),kind.removeprefix('audition-'))
                    return self.file(f)
                f = Path(entry["folder"]) / EXPORT_NAMES[kind]
                if kind=='qc' and not f.exists():f=Path(entry['folder'])/'edit-review.json'
                label = (
                    Path(ws.data['jobs'][entry['job']].get('label') or entry["name"]).stem + '-v'+str([e['id'] for e in ws.data['exports'] if e['job']==entry['job']].index(eid)+1).zfill(3)+"-" + eid[:6] + f.suffix
                    if "download" in urllib.parse.parse_qs(u.query)
                    else None
                )
                return self.file(f, label)
            if p == "/":
                p = "/index.html"
            if p not in ("/index.html", "/app.js", "/style.css", "/icon.svg", "/dm-sans.woff2"):
                return self.result({"error": "Not found"}, 404)
            f = UI / p[1:]
            self.send_bytes(200, f.read_bytes(), MIME[f.suffix])
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except PermissionError as e:
            self.result({'error':str(e)},403)
        except (ValueError, KeyError, AssertionError, FileNotFoundError, StopIteration):
            self.result({"error": "Item not found or invalid request"}, 404)

    def do_POST(self):
        try:
            self.local(True)
            ws = self.server.ws
            u = urllib.parse.urlsplit(self.path)
            if self.headers.get('X-Cutroom-Turn') and not u.path.startswith('/api/conversations/'):
                import editing_conversations
                self._public_turn=self.headers['X-Cutroom-Turn'];self._before_turn=editing_conversations.require_open(ws,self._public_turn)
            p = u.path
            n = int(self.headers.get("Content-Length", "-1"))
            if p=='/api/generative-package':
                if not 0<n<=300*1024**2:raise ValueError('Import a compact ZIP under300MB containing one completed run, adapter and previews.')
                tmp=ws.root/'work'/(ident()+'.zip')
                try:
                    with tmp.open('wb') as f:
                        left=n
                        while left:
                            block=self.rfile.read(min(1024**2,left))
                            if not block:raise ValueError('Upload interrupted.')
                            f.write(block);left-=len(block)
                    query=urllib.parse.parse_qs(u.query);return self.result({'id':ws.generative.import_package(tmp,query.get('kernel',[''])[0])})
                finally:tmp.unlink(missing_ok=True)
            if p=='/api/motion-package':
                if not 0<n<=100*1024**2:raise ValueError('Import a compact animation-spec adapter ZIP under 100MB')
                tmp=ws.root/'work'/(ident()+'.zip')
                try:
                    with tmp.open('wb') as f:
                        left=n
                        while left:
                            block=self.rfile.read(min(1024**2,left))
                            if not block:raise ValueError('Upload interrupted')
                            f.write(block);left-=len(block)
                    import motion_policy
                    return self.result(motion_policy.import_package(ws.root,tmp))
                finally:tmp.unlink(missing_ok=True)
            if p == "/api/import":
                if not 0 < n <= 8 * 1024**3:
                    raise ValueError("Select a video smaller than 8 GB.")
                q = urllib.parse.parse_qs(u.query)
                kind = q["kind"][0]
                name = q["name"][0].replace("\\", "/").split("/")[-1][:180]
                permitted=('.png','.jpg','.jpeg') if kind=='graphic' else ('.wav','.mp3','.m4a','.flac','.ogg') if kind=='music' else (
                    ".mp4",
                    ".mov",
                    ".m4v",
                    ".mkv",
                    ".webm",
                )
                if kind not in ('host','reference','music','graphic') or Path(name).suffix.lower() not in permitted:
                    raise ValueError("Use MP4, MOV, M4V, MKV or WebM.")
                tmp = ws.root / "work" / (ident() + ".upload")
                try:
                    with tmp.open("wb") as f:
                        left = n
                        while left:
                            block = self.rfile.read(min(1024 * 1024, left))
                            if not block:
                                raise ValueError("Upload was interrupted.")
                            f.write(block)
                            left -= len(block)
                    return self.result({"id": ws.import_asset(tmp, name, kind,q.get('parent_source',[None])[0],q.get('collection',[''])[0],q.get('role',[None])[0],q.get('owners',[''])[0].split(',') if q.get('owners',[''])[0] else [])}, 201)
                finally:
                    tmp.unlink(missing_ok=True)
            if not 0 <= n <= 2 * 1024**2:
                raise ValueError("Request is too large.")
            b = json.loads(self.rfile.read(n) or "{}")
            self._turn_request=b
            if p == "/api/update":
                ws.update(b["ids"], b["changes"])
            elif p=='/api/feedback':
                import revisions
                return self.result(revisions.submit(ws,b))
            elif p=='/api/conversations/begin':
                import editing_conversations
                return self.result(editing_conversations.begin(ws,b))
            elif p=='/api/conversations/complete':
                import editing_conversations
                return self.result(editing_conversations.complete(ws,b['turn']))
            elif p=='/api/style-locks':
                import revisions
                return self.result(revisions.lock_style(ws,b['job'],b['fields'],b['revision']))
            elif p=='/api/style-transfer':
                import revisions
                return self.result(revisions.transfer_style(ws,b['source'],b['targets']))
            elif p=='/api/hook-response':
                import hook_review
                return self.result(hook_review.answer(ws,b))
            elif p=='/api/hook-payoff':
                import hook_review
                return self.result(hook_review.payoff(ws,b))
            elif p=='/api/generative-scene':
                return self.result({'id':ws.generative.create_scene(b['run'],b['video'],b['job'],b['passage'],b['at'],b['title'])})
            elif p=='/api/generative-passages':
                import storyboard
                job=ws.data['jobs'][b['id']];asset=ws.data['assets'][b['id']];parts,timing=storyboard.passages(job['settings']['script'],asset['duration'],Path(asset['path']))
                return self.result({'passages':parts,'timing':timing})
            elif p=='/api/generative-submit':
                return self.result({'id':ws.generative.submit(b['run'],b['prompt'],b.get('seed',3407))})
            elif p=='/api/generative-check':
                return self.result(ws.generative.check(b['id']))
            elif p == '/api/artifacts/generate':
                return self.result({'ids':ws.artifacts.generate(b['ids'],b.get('evidence'),bool(b.get('spoken_confirmed',False)),b.get('design'),b.get('animation_mode'),b.get('animation_style'))})
            elif p == '/api/benchmarks/create':
                import video_benchmark
                return self.result(video_benchmark.from_workspace(ws,b['ids'],b.get('references',[]),b.get('quiz_by_job')))
            elif p == '/api/benchmarks/review':
                import video_benchmark
                return self.result(video_benchmark.save_review(ws,b['id'],b['review']))
            elif p == '/api/creator/first-cut':
                return self.result(ws.first_cut(b['ids'],b.get('niche'),b.get('story_format')))
            elif p == '/api/creator/setup':
                ws.speech_setup.start();return self.result(ws.speech_setup.snapshot())
            elif p == '/api/creator/openings':
                import openings
                with ws.archive_lock:return self.result(openings.render(ws,b['id']))
            elif p == '/api/creator/opening-choice':
                with ws.lock:
                    audition=ws.data.get('opening_auditions',{})[b['audition']];job=ws.data['jobs'][audition['job']];ws.artifacts._check_job(job)
                    if job['revision']!=audition['receipt']['revision']:raise ValueError('Audition belongs to a previous revision; render the current opening again')
                    if b['mode'] not in ('host_first','proof_first'):raise ValueError('Choose host-first or proof-first')
                    ws.update([job['id']],dict(opening_mode=b['mode']))
            elif p == '/api/creator/brief':
                with ws.lock:
                    job=ws.data['jobs'][b['id']];ws.artifacts._check_job(job)
                    if job['revision']!=b['revision'] or not job.get('creator'):raise ValueError('Reopen the current first cut before changing its brief')
                    if not isinstance(b.get('text'),str) or len(b['text'])>12000:raise ValueError('Use a brief of up to12000characters')
                    job['creator']['brief_text']=b['text'];job.update(revision=job['revision']+1,status='Draft');ws.save()
            elif p == '/api/creator/trim':
                import math
                with ws.lock:
                    job=ws.data['jobs'][b['id']];ws.artifacts._check_job(job);length=ws.data['assets'][b['id']]['duration']
                    if job['revision']!=b['revision'] or not job.get('creator'):raise ValueError('Reopen the current first cut')
                    start,end=b['start'],b['end']
                    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (start,end)) or not 0<=start<end<=length+.034:raise ValueError('Keep an in-range interval')
                    for word in job.get('transcript',{}).get('words',[]):
                        if word['start']+.02<start<word['end']+.06 or word['start']-.06<end<word['end']-.02:raise ValueError('This cut may clip a word. Move it into the adjacent pause.')
                    job['creator']['keep']=[[round(start*30)/30,round(end*30)/30]];job['creator']['manual_cut_locked']=True
                    job.update(revision=job['revision']+1,status='Draft');ws.save()
            elif p == '/api/creator/asset-label':
                with ws.lock:
                    asset=ws.data['assets'][b['id']]
                    if asset['kind']!='reference' or not isinstance(b.get('description'),str) or len(b['description'])>1000:raise ValueError('Add a short label for the supplied footage')
                    owners=b.get('owners',[])
                    if not isinstance(owners,list) or any(k not in ws.data['jobs'] for k in owners):raise ValueError('Choose existing recordings for this footage')
                    asset['description']=b['description'];asset['owner_jobs']=owners
                    ws.save()
            elif p == '/api/transcribe':
                import speech,copy
                with ws.lock:
                    job=ws.data['jobs'][b['id']];ws.artifacts._check_job(job);host=copy.deepcopy(ws.data['assets'][b['id']])
                transcript=speech.load_or_transcribe(ws.root,host)
                with ws.lock:
                    ws.data['jobs'][b['id']]['transcript']=transcript;ws.save()
                return self.result(transcript)
            elif p == '/api/artifacts/edit':
                ws.artifacts.edit(b['id'],b.get('changes',{}),b['version'])
            elif p == '/api/artifacts/insert':
                ws.artifacts.insert(b['id'],bool(b['enabled']))
            elif p == '/api/animations/save':
                import animation_library
                return self.result({'id':animation_library.save(ws,b['id'])})
            elif p == '/api/animations/excerpt':
                import animation_library
                return self.result({'id':animation_library.excerpt(ws,b['asset'],b['start'],b['end'],b['title'],b.get('crop'),b.get('permission',''))})
            elif p == '/api/animations/reuse':
                ws.artifacts.reuse(b['id'],b['library'],b['version'])
            elif p == '/api/animations/import':
                import animation_library
                return self.result({'id':animation_library.import_illustration(ws,b['id'])})
            elif p == '/api/animations/review':
                import animation_library
                animation_library.review(ws,b['id'],b.get('sha256'),b.get('reviewer'),b.get('evidence'),b.get('clear'),b.get('layout_clear'),b.get('defects',''))
            elif p == '/api/artifacts/toggle':
                ws.artifacts.toggle(b['id'],bool(b['enabled']))
            elif p == '/api/training-intake':
                import learning
                with ws.lock:
                    asset=ws.data['assets'][b['id']]
                    if asset['kind']!='reference':raise ValueError('Only a supplied reference can enter this training intake.')
                    asset['training']=learning.intake(asset,b['metadata']);ws.save()
            elif p == '/api/training-label':
                import learning
                with ws.lock:
                    asset=ws.data['assets'][b['asset']];asset['training']=learning.annotate(asset,b['label']);ws.save()
            elif p == '/api/training-export':
                import learning
                with ws.lock:assets=__import__('copy').deepcopy(ws.data['assets'])
                folder=ws.root/'datasets'/ident();report=learning.export(assets,folder)
                return self.result(dict(folder=str(folder),report=report))
            elif p == '/api/training-report':
                import learning
                with ws.lock:assets=__import__('copy').deepcopy(ws.data['assets'])
                return self.result(learning.dataset(assets))
            elif p == '/api/correction-review':
                if not str(b.get('reviewer','')).strip():raise ValueError('Name the editor who confirmed this correction.')
                with ws.lock:
                    correction=next(c for c in ws.data.get('corrections',[]) if c['id']==b['id'])
                    correction.setdefault('review_history',[]).append(dict(reviewer=b['reviewer'],reason=b.get('reason') or None,confirmed=bool(b.get('confirmed')),time=__import__('time').time()))
                    correction.update(editor_confirmed=bool(b.get('confirmed')),reason=b.get('reason') or None,reviewer=b['reviewer']);ws.save()
            elif p == '/api/source-info':
                with ws.lock:
                    asset=__import__('copy').deepcopy(ws.data['assets'][b['id']]);job=__import__('copy').deepcopy(ws.data['jobs'][b['id']]);exports=[e['id'] for e in ws.data['exports'] if e['job']==job['id']]
                return self.result(dict(id=asset['id'],original_name=asset['name'],local_copy=asset['path'],sha256=__import__('engine.media',fromlist=['sha']).sha(asset['path']),label=job.get('label',asset['name']),collection=job.get('collection',''),archived=job.get('archived',False),exports=exports))
            elif p == '/api/source-organize':
                with ws.lock:
                    job=ws.data['jobs'][b['id']]
                    if job['status'] in ACTIVE:raise ValueError('Wait for this recording’s render before organizing it.')
                    label=str(b.get('label',job.get('label',''))).strip();collection=str(b.get('collection',job.get('collection',''))).strip()
                    if len(label)>100 or len(collection)>80:raise ValueError('Use a shorter display name or project name.')
                    job.update(label=label,collection=collection,archived=bool(b.get('archived',job.get('archived',False))))
                    ws.save()
            elif p == '/api/reveal':
                if os.name!='nt':raise ValueError('Reveal in Explorer is available on Windows.')
                if b['kind']=='source':path=Path(ws.data['assets'][b['id']]['path'])
                elif b['kind']=='export':path=Path(ws.export(b['id'])['folder'])/'edit.mp4'
                elif b['kind']=='animation':path=Path(ws.data['animation_library'][b['id']]['folder'])/'preview.mp4'
                else:raise ValueError('Choose a source recording or an export.')
                if not path.is_file():raise ValueError('The selected local file is missing.')
                __import__('subprocess').Popen(['explorer.exe','/select,',str(path)])
            elif p == '/api/scripts':
                return self.result(ws.assign_scripts(b['ids'],b['scripts']))
            elif p == '/api/phrases':
                return self.result(ws.phrase_matches(b['id'],b['phrase']))
            elif p == '/api/assign-script':
                ws.resolve_script(b['script_id'],b['job_id'])
            elif p == '/api/analyze-reference':
                return self.result(ws.analyze_reference(b['id'],bool(b.get('full')),b.get('metadata')))
            elif p == '/api/reference-observation':
                ws.correct_observation(b['id'],b['index'],b['observation'],float(b['start']),float(b['end']),b['reviewer'])
            elif p == '/api/preview-cues':
                return self.result(ws.preview_cues(b['id']))
            elif p == "/api/queue":
                return self.result(ws.queue(b["ids"],b.get('request_id')))
            elif p == "/api/cancel":
                ws.queued_cancel(b["ids"])
            elif p == "/api/match":
                return self.result({"matches": ws.match(b["ids"])})
            elif p == "/api/review":
                return self.result(ws.review(b) or {'ok':True})
            elif p == "/api/setup":
                ws.install()
            elif p == "/api/check":
                from workspace import configure_tools

                ws.tools = configure_tools(ws.root)
            elif p == "/api/quit":
                if any(j["status"] in ACTIVE for j in ws.data["jobs"].values()) or ws.artifacts.generating:
                    raise ValueError("Let the active batch finish before quitting.")
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                return self.result({"error": "Not found"}, 404)
            self.result({"ok": True})
        except PermissionError as e:
            self.result({'error':str(e)},403)
        except __import__('revisions').Conflict as e:
            self.result({'error':str(e)},409)
        except (ValueError, TypeError, KeyError, StopIteration, IndexError) as e:
            self.result({"error": str(e) or "Invalid request"}, 400)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            logging.exception("Local request failed")
            self.result({"error": str(e)}, 500)
        finally:
            if getattr(self,'_public_turn',None) and hasattr(self,'_before_turn'):
                import editing_conversations
                editing_conversations.trace(ws,self._public_turn,u.path,getattr(self,'_turn_request',{'uploaded_bytes':locals().get('n',0)}),getattr(self,'_response_code',500),self._before_turn)


def run():
    pa = argparse.ArgumentParser()
    pa.add_argument("--data")
    pa.add_argument("--no-browser", action="store_true")
    pa.add_argument("--port", type=int, default=0)
    args = pa.parse_args()
    root = Path(
        args.data
        or os.environ.get("CUTROOM_DATA")
        or ((HERE.parent/'output/cutroom-workspace') if HERE.parent.drive.upper()=='D:' else (Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "Cutroom"))
    )
    root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=root / "cutroom.log", level=logging.WARNING)
    # Hold an OS lock for the entire session, including unfinished batch writes.
    lock = (root / "session.lock").open("a+b")
    lock.seek(0, 2)
    if lock.tell() == 0:
        lock.write(b"0")
        lock.flush()
    lock.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        if not args.no_browser and (root / "session.url").exists():
            webbrowser.open((root / "session.url").read_text().strip())
        return
    ws = Workspace(root)
    server = LocalServer(("127.0.0.1", args.port), Handler)
    server.ws = ws
    server.secret = secrets.token_urlsafe(30)
    server.host = "127.0.0.1:" + str(server.server_port)
    url = "http://" + server.host
    (root / "session.url").write_text(url, encoding="utf8")
    if sys.stdout:
        print(url, flush=True)
    if not args.no_browser:
        threading.Timer(0.22, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()
        ws.pool.shutdown()
        lock.close()


if __name__ == "__main__":
    run()
