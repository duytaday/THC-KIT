"""Bind installed upstream instructions to the kit's Windows/local-media workflow."""
import argparse,hashlib,json
from pathlib import Path


def configure(home,editing_root):
    groups={'hyperframes':['hyperframes','hyperframes-cli','hyperframes-registry','media-use'],
        'editing':['behind-the-person','explainer','orbit-reel','picture-stack','ranking-list','scene-switch','shape-shift','split-screen','storytelling','trial-reels','visual-notes']}
    for group,names in groups.items():
        for name in names:
            folder=Path(home)/name;file=folder/'SKILL.md';original=folder/'UPSTREAM-SKILL.md'
            if not original.exists():original.write_bytes(file.read_bytes())
            text=original.read_text(encoding='utf-8');split=text.index('---',3)+3
            override='''

## Talking Head Cutroom / Windows adapter

For this user's local talking-head kit, use its `.agents/skills/talking-head-edit`
entrypoint and six-gate final QC. The supplied recorded presenter and voice are
authoritative. Keep prior cuts and manual locks. Source/script timings belong to
the current episode; reference animations and synthetic UI are illustrations,
never proof that the current episode's product action succeeded.

On Windows do not run brew, setup.sh, Unix venv commands or overwrite exports.
Read this skill's INSTALLATION.json for its pinned source. In the kit, dot-source
talking-head-qc/tools/use_d_storage.ps1. Use local faster-whisper for Vietnamese;
do not send recordings to Groq, replace the voice, or clone a presenter for this
workflow. Use the actual brief's dimensions, branding and safe areas. Prefer
existing local licensed media and code; cloud/Pro services are optional and
require a task that actually calls for them. Keep their cost/result claims honest.

'''
            if group=='editing':override+='''For the six original workflows run the kit's Windows bridge:
`python -X utf8 app/editing_styles.py STYLE spec.json --upstream UPSTREAM_ROOT --out NEW_VERSION_FOLDER`.
UPSTREAM_ROOT is in INSTALLATION.json. It preserves the real source voice,
uses local ASR, a full Vietnamese font and the compatible HyperFrames0.8.52
renderer. Never run the unadapted build.py from this installed folder: its shared
kit path assumes the upstream repository layout. Photographic styles retain
their template builder; supply your own cleared images/footage and inspect its
media overrides. Installation is not evidence that every cutout/template passed
runtime or editorial QC. Finish through the kit's master QC, not a contact sheet.

'''
            else:override+='''New standalone HTML animations use HyperFrames0.9.33, pinned with these
skills. The existing talking-head-editor bridge keeps its compatible0.8.52
runtime. Use `python app/hyperframes_bridge.py PROJECT --out NEW.mp4` for the
new local renderer after its checks. Save editable HTML/assets and the receipt.
Do not activate paid reverse/re-shot/avatar or style-template features as part
of local reference analysis. User-owned reference excerpts may be archived as
explicit illustration assets; do not treat baked text or people as editable.

'''
            file.write_text(text[:split]+override+text[split:],encoding='utf-8')
            metadata=dict(source='https://github.com/heygen-com/hyperframes' if group=='hyperframes' else 'https://github.com/artemnovitckii/claude-editing-skills',ref='v0.9.33' if group=='hyperframes' else 'beff6b868a8c1bdfad8661bd8a298497e75568a3',upstream_skill_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),upstream_root=str(Path(editing_root).resolve()) if group=='editing' else None,adapter='Talking Head Cutroom Windows/local-ASR/QC override',all_workflows_runtime_verified=False)
            (folder/'INSTALLATION.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    return sum(map(len,groups.values()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--skill-home',type=Path,required=True);p.add_argument('--editing-root',type=Path,required=True);a=p.parse_args();print('Configured',configure(a.skill_home,a.editing_root),'skills')
