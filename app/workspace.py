import copy
import json
import math
import os
import shutil

import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from engine import edit, media, planner
from assignments import match_scripts

HERE = Path(__file__).resolve().parent
ACTIVE = {"Queued", "Rendering"}
DEFAULT = dict(
    script="",
    style="clean",
    fit="contain",
    caption_position="bottom",
    style_ref="",
    insert_sound="none",
    inserts=[],
    motion_profile='baseline',motion_intensity=.5,events=[],
    music_mode='off',music_track='calm',music_gain_db=-20,music_asset='',
    planner_mode='built_in',
    niche='',story_format='auto',
    brand_logo='',brand_from=0.,brand_to=0.,
    opening_mode='current',
)


def ident():
    return uuid.uuid4().hex


def clock():
    return time.time()


def atomic(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")
    os.replace(temp, path)


def configure_tools(root):
    candidates = [root/'tools/ffmpeg-8.1.2/bin',root / "bin",HERE / "bin", HERE.parent / "bin"]
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet"
        candidates.extend(
            [
                local / "Links",
                *sorted((local / "Packages").glob("Gyan.FFmpeg*/*/bin"), reverse=True),
            ]
        )
    for p in reversed(candidates):
        if p.is_dir() and str(p) not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        for d in ["assets", "exports", "work"]:
            (self.root / d).mkdir(exist_ok=True)
        self.archive_lock = threading.Lock()
        self.doc = self.root / "workspace.json"
        self.lock = threading.RLock()
        self.data = (
            json.loads(self.doc.read_text(encoding="utf8"))
            if self.doc.exists()
            else {"assets": {}, "jobs": {}, "exports": []}
        )
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cutroom")
        self.setup = ""
        self.installing = False
        for j in self.data["jobs"].values():
            j["settings"] = {**copy.deepcopy(DEFAULT), **j["settings"]}
            for insert in j['settings']['inserts']:insert.setdefault('id',ident())
            if j["status"] in ACTIVE:
                j.update(status="Interrupted", stage="Render stopped. Queue this clip again.")
        self.save()
        self.tools = configure_tools(self.root)
        from artifact_store import ArtifactStore
        self.artifacts=ArtifactStore(self)
        from generative import GenerativeStore
        self.generative=GenerativeStore(self)
        import asr_setup
        self.speech_setup=asr_setup.Setup(self.root)

    def save(self):
        atomic(self.doc, self.data)

    def snapshot(self):
        with self.lock:
            d = copy.deepcopy(self.data)
            d['scene_generating']=sorted(self.artifacts.generating)
            model_file=self.root/'models/animation-spec/candidate.json'
            d['animation_model']=({k:v for k,v in json.loads(model_file.read_text(encoding='utf-8')).items() if k!='folder'} if model_file.exists() else None)
            for v in d["assets"].values():
                v.pop("path", None)
            for e in d["exports"]:
                e.pop("folder", None)
            for artifact in d.get('artifacts',{}).values():
                artifact.pop('folder',None)
                for version in artifact.get('versions',[]):version.pop('folder',None)
            for item in d.get('animation_library',{}).values():item.pop('folder',None)
            for item in d.get('benchmarks',{}).values():item.pop('folder',None)
            for item in d.get('opening_auditions',{}).values():item.pop('folder',None)
            return {
                **d,
                "tools": self.tools,
                "setup": self.setup,
                "installing": self.installing,
                "platform": os.name,
                "workers": 2,
                "version":__import__('version').VERSION,
                "speech_setup":self.speech_setup.snapshot(),
                "data_folder": str(self.root),
                "capabilities": {'local_renderer':self.tools,'openbot':{'cli_found':bool(shutil.which('openbot')),'connected':False},'mausbot':{'cli_found':bool(shutil.which('mausbot')),'connected':False},'trained_presets':False},
            }

    def import_asset(self, path, name, kind, parent_source=None, collection='',source_role=None,owners=()):
        if source_role not in (None,'broll','style_reference'):raise ValueError('Choose B-roll or style reference')
        with self.lock:
            if parent_source and (kind!='host' or parent_source not in self.data['jobs']):raise ValueError('Choose an existing source recording for a new take.')
            parent=copy.deepcopy(self.data['jobs'].get(parent_source)) if parent_source else None
        self.tools = configure_tools(self.root)
        if not self.tools:
            raise ValueError("Install FFmpeg and FFprobe using the setup panel first.")
        streams = media.probe(path)
        if kind=='graphic':
            video=next((s for s in streams if s['codec_type']=='video'),None)
            if not video:raise ValueError('Choose a decodable PNG or JPEG image.')
            asset_id=ident();dest=self.root/'assets'/(asset_id+Path(name).suffix.lower());path.replace(dest);thumb=self.root/'assets'/(asset_id+'.jpg')
            media.ff('-i',dest,'-frames:v','1','-vf','scale=300:200:force_original_aspect_ratio=decrease,pad=300:200:(ow-iw)/2:(oh-ih)/2',thumb)
            with self.lock:self.data['assets'][asset_id]=dict(id=asset_id,kind='graphic',name=name,path=str(dest),duration=0,width=video['width'],height=video['height'],thumb=True,created=clock());self.save()
            return asset_id
        if kind=='music':
            audio=next((s for s in streams if s['codec_type']=='audio'),None)
            if not audio:raise ValueError('Choose a decodable audio track.')
            asset_id=ident();dest=self.root/'assets'/(asset_id+Path(name).suffix.lower());path.replace(dest)
            with self.lock:
                self.data['assets'][asset_id]=dict(id=asset_id,kind='music',name=name,path=str(dest),duration=media.duration(audio),width=0,height=0,thumb=False,created=clock(),permitted_use='Music explicitly assigned by local operator; clearance declaration recorded in UI')
                self.save()
            return asset_id
        video = next(
            (
                s
                for s in streams
                if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")
            ),
            None,
        )
        if video is None:
            raise ValueError("This file has no video track.")
        if kind == "host" and not any(s["codec_type"] == "audio" for s in streams):
            raise ValueError("A talking-head recording needs an audio track.")
        asset_id = ident()
        length = media.duration(video)
        source_dir=self.root/'assets'/'sources'/asset_id
        source_dir.mkdir(parents=True,exist_ok=True)
        fname=source_dir/(Path(name).stem[:70]+Path(name).suffix.lower())
        path.replace(fname)
        thumb = self.root / "assets" / (asset_id + ".jpg")
        try:
            media.ff(
                "-ss",
                str(min(length * 0.15, 0.7)),
                "-i",
                fname,
                "-frames:v",
                "1",
                "-vf",
                "scale=300:200:force_original_aspect_ratio=decrease,pad=300:200:(ow-iw)/2:(oh-ih)/2",
                "-threads",
                "1",
                thumb,
            )
        except (OSError, ValueError):
            pass
        out = {
            "id": asset_id,
            "kind": kind,
            "name": name,
            "duration": length,
            "width": video["width"],
            "height": video["height"],
            "path": str(fname),
            "source_sha256": media.sha(fname),
            "created": clock(),
            "thumb": thumb.exists(),
            "source_role":source_role,"owner_jobs":list(owners),
        }
        with self.lock:
            self.data["assets"][asset_id] = out
            if kind == "host":
                family=parent.get('source_family',parent['id']) if parent else asset_id
                take=max([j.get('take_number',1) for j in self.data['jobs'].values() if j.get('source_family',j['id'])==family]+[0])+1
                settings=copy.deepcopy(DEFAULT)
                if parent:
                    for k in DEFAULT:
                        if k not in ('script','inserts','events'):settings[k]=copy.deepcopy(parent['settings'].get(k,DEFAULT[k]))
                self.data["jobs"][asset_id] = {
                    "id": asset_id,
                    "settings": settings,
                    "source_family":family,"parent_source":parent_source,"take_number":take,
                    "collection":parent.get('collection','') if parent else str(collection)[:80],
                    "label":parent.get('label','') if parent else '',
                    "reference_script":parent['settings']['script'] if parent else '',
                    "status": "Draft",
                    "stage": "New take: attach and align this recording’s own script." if parent else '',
                    "revision": 0,
                    "latest": "",
                    "updated": clock(),
                }
            self.save()
        return asset_id

    def valid(self, j, opts):
        import creator
        if not isinstance(opts.get('niche',''),str) or len(opts.get('niche',''))>500:raise ValueError('Describe the niche in up to500characters')
        if opts.get('story_format','auto') not in ('auto',*creator.FORMATS):raise ValueError('Choose an editorial recipe')
        if opts.get('opening_mode','current') not in ('current','host_first','proof_first'):raise ValueError('Choose an available opening')
        if opts.get('brand_logo'):
            logo=self.data['assets'].get(opts['brand_logo'])
            if not logo or logo['kind']!='graphic':raise ValueError('Choose an imported logo image')
        for field in ('brand_from','brand_to'):
            if type(opts.get(field,0)) not in (float,int) or not math.isfinite(opts.get(field,0)) or opts.get(field,0)<0:raise ValueError('Logo times must be nonnegative seconds')
        if opts.get('brand_to',0) and opts['brand_to']<=opts.get('brand_from',0):raise ValueError('Logo end must follow its start')
        if opts.get('planner_mode','built_in') not in ('built_in','base','base_rag','fine_tuned'):raise ValueError('Choose an available decision planner.')
        if set(opts) - set(DEFAULT):
            raise ValueError("Unknown project setting.")
        if opts['motion_profile'] not in ('baseline','reference','calm','focus','reference_badges'):raise ValueError('Choose an available built-in motion profile.')
        if not isinstance(opts['motion_intensity'],(float,int)) or not math.isfinite(opts['motion_intensity']) or not 0<=opts['motion_intensity']<=1:raise ValueError('Motion intensity must be0–1.')
        if opts['music_mode'] not in ('off','auto','my_track'):raise ValueError('Choose Music Off, Choose automatically, or My track.')
        if opts['music_track'] not in ('calm','tutorial'):raise ValueError('Choose an available instrumental bed.')
        if not isinstance(opts['music_gain_db'],(int,float)) or not math.isfinite(opts['music_gain_db']) or not -60<=opts['music_gain_db']<=0:raise ValueError('Music gain must be−60–0dB.')
        if not isinstance(opts['events'],list) or len(opts['events'])>100:raise ValueError('Use up to100independent cues.')
        if opts["insert_sound"] not in ("none", "click", "slide", "chime"):
            raise ValueError("Choose an available cutaway sound.")
        if (
            opts["style"] not in ("clean", "focus")
            or opts["fit"] not in ("contain", "cover")
            or opts["caption_position"] not in ("top", "bottom")
        ):
            raise ValueError("Invalid visual settings.")
        if not isinstance(opts["script"], str) or len(opts["script"]) > 200000:
            raise ValueError("Use a script of up to 200,000 characters.")

        def ref(aid):
            a = self.data["assets"].get(aid)
            if not a or a["kind"] != "reference":
                raise ValueError("Choose an imported reference.")
            return a

        if opts["style_ref"]:
            ref(opts["style_ref"])
        if not isinstance(opts["inserts"], list) or len(opts["inserts"]) > 12:
            raise ValueError("Use up to 12 cutaways per video.")
        end = 0
        length = self.data["assets"][j["id"]]["duration"]
        for q in sorted(opts["inserts"], key=lambda x: x["at"]):
            from engine.layouts import options
            options(q)
            a = ref(q["asset"])
            if not all(
                isinstance(q.get(k), (float, int)) and math.isfinite(q[k])
                for k in ("at", "offset", "duration")
            ):
                raise ValueError("Cutaway times must be numbers.")
            cue = q.get("cue", "")
            if not isinstance(cue, str) or len(cue) > 240:
                raise ValueError("Use a short phrase for the spoken cue.")
            if (
                q["offset"] < 0
                or q["duration"] < 1 / 30
                or q["offset"] + q["duration"] > a["duration"] + 0.00001
            ):
                raise ValueError("The cutaway must fit its source footage.")
            if not cue.strip():
                if q["at"] < end-0.000001 or q["at"] + q["duration"] > length + 0.00001:
                    raise ValueError("Cutaways must fit the recording without overlapping.")
                end = q["at"] + q["duration"]

    def update(self, ids, changes):
        with self.lock:
            jobs = [self.data["jobs"][key] for key in dict.fromkeys(ids)]
            prepared = []
            for j in jobs:
                if j["status"] in ACTIVE:
                    raise ValueError("A queued or rendering clip is locked until it finishes.")
                opts = {**j["settings"], **copy.deepcopy(changes)}
                for insert in opts['inserts']:insert.setdefault('id',ident())
                self.valid(j, opts)
                prepared.append(opts)
            for j, opts in zip(jobs, prepared):
                if opts != j["settings"]:
                    if any(k in changes for k in ('events','inserts')):
                        self.data.setdefault('corrections',[]).append(dict(id=ident(),job=j['id'],source=self.data['assets'][j['id']]['path'],source_sha256=media.sha(self.data['assets'][j['id']]['path']),before={k:copy.deepcopy(j['settings'][k]) for k in changes},after=copy.deepcopy(changes),reason=None,editor_confirmed=False,created=clock(),alignment='stable source anchors; not a training label until reviewed'))
                    j.update(
                        settings=opts,
                        status="Draft",
                        stage="",
                        updated=clock(),
                        revision=j["revision"] + 1,
                    )
                    if 'script' in changes:j.pop('script_issue',None)
                    if 'script' in changes:self.artifacts.invalidate_script(j['id'],opts['script'])
            self.save()

    def assign_scripts(self,ids,scripts):
        with self.lock:
            assigned,unresolved=match_scripts(self.data['jobs'],self.data['assets'],ids,scripts)
            if any(self.data['jobs'][key]['status'] in ACTIVE for key in ids):raise ValueError('Wait for these recordings to finish rendering before importing scripts.')
            # All matches are resolved first; duplicates never win by import order.
            for key,script in assigned:self.update([key],{'script':script['text']})
            for item in unresolved:
                item['id']=ident()
                for key in item['candidates']:
                    if not self.data['jobs'][key]['settings']['script'].strip():self.data['jobs'][key].update(script_issue='Ambiguous script · assign manually',status='Needs input')
            self.data['script_inbox']=self.data.get('script_inbox',[])+unresolved
            self.save()
            return {'matched':len(assigned),'unresolved':unresolved}

    def resolve_script(self,script_id,job_id):
        with self.lock:
            entry=next(x for x in self.data.get('script_inbox',[]) if x['id']==script_id)
            self.update([job_id],{'script':entry['text']})
            self.data['script_inbox']=[x for x in self.data['script_inbox'] if x['id']!=script_id]
            self.save()

    def phrase_matches(self,key,phrase):
        with self.lock:
            job=copy.deepcopy(self.data['jobs'][key]);host=copy.deepcopy(self.data['assets'][key])
        groups,timing=planner.script_groups(job['settings']['script'],host['duration'],Path(host['path']))
        words=[w for g in groups for w in g];hits=planner.hits([planner.word_key(w[2]) for w in words],[planner.word_key(w) for w in phrase.split()])
        return {'timing':timing,'matches':[{'occurrence':n,'at':words[i][0],'context':' '.join(w[2] for w in words[max(0,i-4):i+len(phrase.split())+4])} for n,i in enumerate(hits)]}

    def analyze_reference(self,key,full=False,metadata=None):
        from engine.references import analyze
        with self.lock:asset=copy.deepcopy(self.data['assets'][key])
        if asset['kind']!='reference':raise ValueError('Choose reference footage to analyze.')
        result=analyze(asset['path'],asset['duration'],full)
        with self.lock:
            self.data['assets'][key]['analysis']=result
            if metadata:self.data['assets'][key]['provenance']={k:metadata.get(k) for k in ('creator','series','language','permitted_uses')}
            self.save()
        return result

    def correct_observation(self,key,index,observation,start,end,reviewer):
        with self.lock:
            asset=self.data['assets'][key]
            if not reviewer.strip() or not observation.strip() or not 0<=start<end<=asset['duration']:raise ValueError('Add reviewer, observation and an in-range source interval.')
            old=asset['analysis']['observations'][index]
            asset['analysis'].setdefault('review_history',[]).append(copy.deepcopy(old))
            old.update(observation=observation,source_range=[start,end],status='human_confirmed',reviewer=reviewer,confidence=1)
            self.save()

    def preview_cues(self,key,settings=None):
        with self.lock:
            job=self.data['jobs'][key];host=copy.deepcopy(self.data['assets'][key]);assets=copy.deepcopy(self.data['assets']);settings=copy.deepcopy(settings or job['settings'])
        plan,notes=planner.build(host,settings,assets)
        with self.lock:self.artifacts.apply(key,plan)
        import planner_policy
        notes['planner']=planner_policy.apply(self.root,host,settings,plan,assets)
        from engine.enhance import events_for
        return {'events':events_for(plan,[[0,host['duration'],0]]),'analysis':notes,'plan':plan}

    def queue(self, ids, request_id=None):
        with self.lock:
            if request_id and request_id in self.data.get('queue_requests',{}):return copy.deepcopy(self.data['queue_requests'][request_id])
            self.tools = configure_tools(self.root)
            if not self.tools:
                raise ValueError("FFmpeg and FFprobe must be installed before rendering.")
            jobs = [self.data["jobs"][key] for key in dict.fromkeys(ids)]
            pending = []
            skipped = []
            for j in jobs:
                if j["status"] in ACTIVE:
                    continue
                if j.get('archived'):
                    skipped.append(self.data['assets'][j['id']]['name']);continue
                try:
                    if not j["settings"]["script"].strip() and not j.get('creator_requested'):
                        raise ValueError("Add a script to render this recording.")
                    if j.get('script_issue'):raise ValueError(j['script_issue'])
                    self.valid(j, j["settings"])
                except ValueError as err:
                    j.update(status="Needs input", stage=str(err))
                    skipped.append(self.data["assets"][j["id"]]["name"])
                    continue
                pending.append(j)
            for j in pending:
                j.update(status="Queued", stage="Waiting for an encoder")
            result={"queued": len(pending), "skipped": skipped}
            if request_id:
                requests=self.data.setdefault('queue_requests',{});requests[request_id]=result
                while len(requests)>200:requests.pop(next(iter(requests)))
            self.save()
            for j in pending:
                self.pool.submit(self.run, j["id"])
            return result

    def stage(self, key, s):
        with self.lock:
            self.data["jobs"][key]["stage"] = s
            self.save()

    def run(self, key):
        started=time.monotonic()
        with self.lock:
            j = self.data["jobs"][key]
            if j["status"] != "Queued":
                return
            j.update(status="Rendering", stage="Analyzing speech")
            self.save()
            settings = copy.deepcopy(j["settings"])
            revision = j["revision"]
            assets = copy.deepcopy(self.data["assets"])
            host = assets[key]
            previous=next((copy.deepcopy(e) for e in reversed(self.data['exports']) if e['job']==key),None)
        eid = ident()
        temp = self.root / "work" / eid
        temp.mkdir()
        try:
            if host.get('source_sha256') and media.sha(host['path'])!=host['source_sha256']:raise ValueError('The original source file changed. Import it as a new take; prior timings were preserved.')
            creator_context=None
            if j.get('creator_requested'):
                import creator
                settings,creator_context=creator.prepare(self,key,settings,host,assets)
            elif j.get('creator'):
                import creator
                creator_context=creator.refresh(j['creator'],j.get('transcript'),settings,host,assets,key)
            refid=settings.get('style_ref')
            reused_ref=bool(refid and assets[refid].get('analysis'))
            if refid and media.sha(assets[refid]['path'])!=assets[refid].get('source_sha256'):raise ValueError('Style reference changed. Import the replacement; prior analysis and edits were preserved.')
            if refid and not reused_ref:
                self.stage(key,'Analyzing reference pacing locally')
                assets[refid]['analysis']=self.analyze_reference(refid)
            plan, notes = planner.build(host, settings, assets)
            if creator_context:
                import creator
                creator.apply(plan,creator_context,j.get('transcript'),settings['script'],host)
                creator_context=copy.deepcopy(plan['creator']);notes['creator']=creator_context
                with self.lock:j['creator']=copy.deepcopy(creator_context);self.save()
            with self.lock:self.artifacts.apply(key,plan)
            if creator_context:
                import openings
                openings.apply(plan,settings,assets)
            import planner_policy
            notes['planner']=planner_policy.apply(self.root,host,settings,plan,assets)
            media.write_json(temp/'planner-receipt.json',notes['planner'])
            fonts = temp / "fonts"
            fonts.mkdir()
            shutil.copy2(HERE / "fonts/DejaVuSans-Bold.ttf", fonts)
            import qc_bridge
            qc_bridge.prepare_export(temp,host,settings,plan)
            qc_bridge.preflight(temp)
            self.stage(key, "Encoding and checking playback")
            import revision_cache
            reused=bool(previous and revision_cache.reuse(previous['folder'],previous['sha256'],host['path'],plan,temp))
            # The post-render six-gate checker fully decodes the exact master.
            if not reused:edit.render(Path(host["path"]), plan, temp,verify_decode=False)
            self.stage(key,'Verifying exact master and render dependencies')
            qc_bridge.verify_dependencies(temp)
            if os.environ.get('CUTROOM_VERIFY_REPRODUCTION')=='1':qc_bridge.verify_reproduction(temp,host,plan,edit.render)
            report = json.loads((temp / "edit-review.json").read_text(encoding="utf8"))
            report.update(notes)
            report["review_required"] = [
                "Listen to the full narration",
                "Check caption timing and visual proof on a phone",
            ]
            media.write_json(temp / "edit-review.json", report)
            asset_by_path = {a["path"]: a for a in assets.values()}
            for cue in plan["proof"]:
                source_path=cue.pop('file');a=asset_by_path.get(source_path)
                if a is None and cue.get('artifact_id'):
                    scene=self.data['artifacts'][cue['artifact_id']];a={'id':scene['id'],'name':scene['plan']['title']+' · original artifact'}
                if a is None:raise ValueError('A planned source asset is no longer available: '+source_path)
                cue.update(asset_id=a["id"], source_name=a["name"])
            ref_ids = {q["asset"] for q in settings["inserts"]}
            if settings.get("style_ref"):
                ref_ids.add(settings["style_ref"])
            if settings.get('brand_logo'):ref_ids.add(settings['brand_logo'])
            sources = {aid: assets[aid]["name"] for aid in sorted(ref_ids)}
            media.write_json(
                temp / "project.json",
                {
                    "job": key,
                    "source": host["name"],
                    "revision": revision,
                    "settings": settings,
                    "references": sources,
                    "plan": plan,
                    "analysis": notes,
                },
            )
            folder = self.root / "exports" / eid
            temp.rename(folder)
            if (folder/'repeatability.json').exists():
                repeated=json.loads((folder/'repeatability.json').read_text(encoding='utf-8'));repeated['rerender_path']=str(folder/'reopened/edit.mp4');media.write_json(folder/'repeatability.json',repeated)
            self.stage(key,'Running six-gate QC')
            kit_report=qc_bridge.check(folder)
            report['verified']['full_decode']=any(c.get('id')=='full_decode' and c.get('status')=='PASS' for c in kit_report.get('gates',{}).get('F',{}).get('checks',[]))
            report['kit_qc']={k:kit_report.get(k) for k in ('status','gates','issues','pending','measurements')}
            media.write_json(folder/'edit-review.json',report)
            with self.lock:
                report['performance']=dict(elapsed_seconds=round(time.monotonic()-started,3),clip_seconds=host['duration'],
                    reused_transcript=bool(creator_context and creator_context.get('reused_transcript')),
                    reused_encoded_tail=reused,
                    reused_reference_analysis=reused_ref,disk_bytes=sum(f.stat().st_size for f in folder.rglob('*') if f.is_file()),
                    automatic_second_render=False if os.environ.get('CUTROOM_VERIFY_REPRODUCTION')!='1' else True)
                media.write_json(folder/'edit-review.json',report)
                self.data["exports"].append(
                    {
                        "id": eid,
                        "job": key,
                        "name": host["name"],
                        "revision": revision,
                        "folder": str(folder),
                        "created": clock(),
                        "duration": report["verified"]["video_s"],
                        "timing": notes["timing"],
                        "sha256": report["verified"]["sha256"],
                        "verdict": kit_report['status'],
                        "technical": report,
                    }
                )
                j.update(status='Failed' if kit_report['status']=='BLOCKED' else 'Needs revision' if kit_report['status']=='REVISE' else "For review", stage='QC needs attention: '+kit_report.get('error','Confirmed defect') if kit_report['status'] in ('BLOCKED','REVISE') else 'Technical checks passed · editorial review needed', latest=eid)
                j['planner_receipt']=notes['planner']
                if notes['planner'].get('fallback'):j['stage']='Planner fallback: '+notes['planner']['fallback']+' · editorial review needed'
                self.save()
        except Exception as e:
            if temp.exists():
                failed_root=self.root/'failed';failed_root.mkdir(exist_ok=True);failed=failed_root/eid
                temp.resolve().relative_to((self.root/'work').resolve());failed.resolve().relative_to(failed_root.resolve())
                temp.rename(failed)
            with self.lock:
                j.update(status="Failed", stage=str(e)[-1200:] or type(e).__name__)
                self.save()
        finally:
            if temp.exists():
                shutil.rmtree(temp, ignore_errors=True)

    def first_cut(self,ids,niche=None,story_format=None):
        with self.lock:
            jobs=[self.data['jobs'][key] for key in dict.fromkeys(ids)]
            if not jobs:raise ValueError('Add and select a recording first')
            missing=[];ready=[];prepared=[]
            for j in jobs:
                if j['status'] in ACTIVE:continue
                updated=copy.deepcopy(j['settings'])
                if niche is not None:updated['niche']=niche
                if story_format is not None:updated['story_format']=story_format
                self.valid(j,updated)
                prepared.append((j,updated))
            for j,updated in prepared:
                if self.speech_setup.snapshot()['status']!='READY' and not updated['script'].strip():
                    j.update(status='Needs input',stage='Set up local captions or attach this recording’s TXT/SRT');missing.append(j['id']);continue
                if updated!=j['settings']:j.update(settings=updated,revision=j['revision']+1,status='Draft')
                if not j.get('creator'):
                    j['creator_requested']=True
                    j['creator_preserve_script']=any(e['job']==j['id'] for e in self.data['exports']) or any(r['job']==j['id'] and (r.get('inserted') or r.get('locked')) for r in self.data.get('artifacts',{}).values())
                ready.append(j['id'])
            self.save()
        result=self.queue(ready) if ready else dict(queued=0,skipped=[])
        if missing:result.update(setup_required=True,speech_setup=self.speech_setup.snapshot(),needs_script_or_setup=missing)
        return result

    def match(self, ids):
        count = 0
        for key in dict.fromkeys(ids):
            with self.lock:
                j = self.data["jobs"][key]
                if (
                    j["status"] in ACTIVE
                    or j["settings"]["inserts"]
                    or not j["settings"]["script"].strip()
                ):
                    continue
                settings = copy.deepcopy(j["settings"])
                revision = j["revision"]
                assets = copy.deepcopy(self.data["assets"])
            matches = planner.match_references(assets[key], settings, assets)
            if matches:
                with self.lock:
                    if j["revision"] != revision or j["status"] in ACTIVE:
                        continue
                    self.update([key], {"inserts": matches})
                    count += len(matches)
        return count

    def review(self, body):
        with self.lock:
            entry = next(x for x in self.data["exports"] if x["id"] == body["id"])
            folder = Path(entry["folder"])
            report = json.loads((folder / "edit-review.json").read_text(encoding="utf8"))
            digest = report["verified"]["sha256"]
            if body.get("sha256") != digest or media.sha(folder / "edit.mp4") != digest:
                raise ValueError("This master has changed. Reopen the correct export.")
            verdict = body.get("verdict")
            note = str(body.get("note", "")).strip()[:2000]
            if verdict not in ("READY", "REVISE"):
                raise ValueError("Choose a review result.")
            checks = body.get("checks", {})
            required = ("watched", "content", "captions", "audio")
            if verdict == "READY" and not all(checks.get(k) is True for k in required):
                raise ValueError("Complete all four viewing and listening checks before approving.")
            if verdict=='READY':
                current=self.data['jobs'][entry['job']]
                if current['revision']!=entry['revision']:raise ValueError('The project changed after this export. Render the current revision before release; the prior cut is preserved.')
                import qc_bridge
                result=qc_bridge.approve(folder,body)
                report['kit_qc']={k:result.get(k) for k in ('status','gates','issues','pending','measurements')}
            if verdict == "REVISE" and not note:
                raise ValueError("Describe the defect with a timecode.")
            if verdict=='REVISE' and not __import__('re').search(r'\b\d{1,2}:[0-5]\d\b',note):raise ValueError('Include a timecode such as00:12 and a concrete correction.')
            record = {
                "verdict": verdict,
                "sha256": digest,
                "time": clock(),
                "reviewer": body.get('reviewer','Local operator'),
                "checks": {k: checks.get(k) is True for k in required},
                "note": note,
            }
            report.setdefault("reviews", []).append(record)
            report["verdict"] = verdict
            atomic(folder / "edit-review.json", report)
            entry.update(verdict=verdict, sha256=digest)
            j = self.data["jobs"][entry["job"]]
            if (
                j["latest"] == entry["id"]
                and j["revision"] == entry["revision"]
                and j["status"] not in ACTIVE
            ):
                j.update(
                    status="Approved" if verdict == "READY" else "Needs revision",
                    stage=note or "Final master reviewed",
                )
            self.save()

    def queued_cancel(self, ids):
        with self.lock:
            for key in ids:
                j = self.data["jobs"][key]
                if j["status"] == "Queued":
                    j.update(status="Draft", stage="Removed from queue")
            self.save()

    def export(self, eid):
        with self.lock:
            return copy.deepcopy(next(e for e in self.data["exports"] if e["id"] == eid))

    def install(self):
        if os.name != "nt":
            raise ValueError("Install FFmpeg and FFprobe with the package manager for this system.")
        with self.lock:
            if self.installing:
                return
            self.installing = True
            self.setup = "Downloading pinned FFmpeg8.1.2 (~104MB) into this workspace…"

        def action():
            try:
                import encoder_setup
                encoder_setup.install(self.root,lambda message:setattr(self,'setup',message))
                self.tools = configure_tools(self.root)
                self.setup = (
                    "FFmpeg is ready."
                    if self.tools
                    else "Installation did not finish. See START_HERE.md for manual local setup."
                )
            except Exception as exc:
                self.setup = str(exc)
            finally:
                self.installing = False

        threading.Thread(target=action, daemon=True).start()
