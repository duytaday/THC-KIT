"""Apply the kit's narrow Windows/Codex overrides to an installed upstream skill."""
import argparse
import hashlib
import json
from pathlib import Path

COMMIT='9382aa31bd66a5c6b6a06a761b748cc513149647'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skill',type=Path,default=Path.home()/'.agents/skills/talking-head-editor')
    a=p.parse_args();skill=a.skill
    entry=skill/'SKILL.md';original=entry.read_text(encoding='utf-8')
    backup=skill/'UPSTREAM-SKILL.md'
    if not backup.exists():backup.write_text(original,encoding='utf-8')
    marker='## Codex / Windows integration override'
    if marker not in original:
        notice='''## Codex / Windows integration override

Read `WINDOWS-KIT.md` before setup or editing on Windows. These local overrides
take precedence over conflicting upstream defaults below: preserve versioned
cuts, choose the best complete take, protect meaningful breaths and qualifiers,
use multilingual faster-whisper rather than the English-only transcriber, and
route final delivery through the project talking-head-edit QC and human review.
Never overwrite an earlier cut or synthesize UI as proof of a real demonstration.

'''
        entry.write_text(original.replace('# Talking-head editor\n','# Talking-head editor\n\n'+notice,1),encoding='utf-8')
    (skill/'WINDOWS-KIT.md').write_text('''# Windows / Codex adapter

This installed skill retains its upstream motion kit, examples and references.
INSTALLATION.json records kit_checkout. Use that working checkout when the
active footage folder lacks the integration adapters.
For this project, start with `.agents/skills/talking-head-edit/SKILL.md` and
`talking-head-qc/integrations/talking-head-editor.md` in the active checkout.

- Do not run setup.sh on Windows. Reuse the established Python 3.12 environment,
  multilingual faster-whisper CUDA, FFmpeg and NVIDIA NVENC. DeepFilterNet,
  OpenAI Whisper, OpenCV and upstream automatic voice/framing are optional and
  have not been installed or validated by this integration.
- Export faster-whisper word timings with the project bridge's `words` command.
  Use source timings for take selection; regenerate from the final audio for
  captions. Do not mix source seconds and edited seconds.
- Use `init-motion` and `render-motion` from the project bridge instead of
  cp, render.sh or snap.sh. It builds the actual upstream graphics, supports
  Vietnamese wt() matching and UTF-8, averages subframes and verifies frame count.
- Set PYTHONUTF8=1 when running upstream Python directly on Windows. compose.py
  has the local --encoder h264_nvenc option; its default remains libx264.
- Select the best complete natural take, not automatically the last take.
  The 0.09-second pause and 40–60% graphics figures are not project requirements.
  Preserve an intentional breath, a qualifier, and time needed to read a result.
- Real product demonstrations use Computer Use and Recordly with the action and
  actual result. Graphic cursor animation is explanatory artwork, not evidence
  that a real command, click or generation succeeded.
- For vertical footage use a brief-specific layout. Do not force a horizontal
  right-half panel, automatic face zoom, or hide captions during all full shots.
- Create output/<job>/vNNN; preserve prior cuts, source media and linked projects.
  Deliver edit.mp4, captions.srt, brief.md, delivery.json and timeline.json.
- Upstream qa.py is a diagnostic. Its exit 0 does not mean editorial approval.
  Run verify_edit.py, inspect/listen to the exact export, and leave approved_by
  for the final human. Use NEEDS_REVIEW whenever listening/viewing is unavailable.
''',encoding='utf-8')
    compose=skill/'scripts/compose.py';code=compose.read_text(encoding='utf-8')
    if "ap.add_argument('--encoder'" not in code:
        old="ap.add_argument('--no-captions', action='store_true');"
        if code.count(old)!=1:raise RuntimeError('Unsupported upstream compose arguments')
        code=code.replace(old,"ap.add_argument('--encoder', choices=['libx264','h264_nvenc'], default='libx264'); "+old,1)
        old="'-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-tune', 'film',"
        if code.count(old)!=1:raise RuntimeError('Unsupported upstream compose encoder')
        code=code.replace(old,"*(['-c:v', 'h264_nvenc', '-preset', 'p5', '-cq', a.crf] if a.encoder == 'h264_nvenc' else ['-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-tune', 'film']),",1)
        compose.write_text(code,encoding='utf-8')
    result=dict(repo='https://github.com/griffinwooldridge/talking-head-editor',tested_commit=COMMIT,upstream_skill_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),local_adapter='talking-head-qc/tools/talking_head_editor.py',overrides=['Windows motion rendering','UTF-8/Vietnamese word matching','optional NVENC compose','project versioning and QC precedence'])
    result['kit_checkout']=str(Path(__file__).resolve().parents[2])
    (skill/'INSTALLATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
