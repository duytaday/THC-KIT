"""Point the installed MoneyPrinter skill at the user-selected local fork/kit."""
import argparse
import json
from pathlib import Path
import re

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skill',type=Path,default=Path.home()/'.agents/skills/moneyprinterturbo-video')
    args=p.parse_args();entry=args.skill/'SKILL.md'
    text=entry.read_text(encoding='utf-8');backup=args.skill/'UPSTREAM-SKILL.md'
    if not backup.exists():backup.write_text(text,encoding='utf-8')
    # Codex skill metadata does not accept Claude's compatibility field. The
    # runtime requirements remain documented in the body and project reference.
    text=re.sub(r'(?m)^compatibility:.*\n','',text,count=1)
    marker='## Talking-head kit override'
    if marker not in text:
        notice='''## Talking-head kit override

For this project read `talking-head-qc/integrations/moneyprinterturbo.md` in the
active talking-head checkout before running the upstream helper. Use the user's
duytaday/MoneyPrinterTurbo fork at ~/Projects/MoneyPrinterTurbo, managed by uv
with Python 3.12. Do not silently clone the official upstream over this fork.
Installation/integration alone does not request a new generated video.

Default video language here is Vietnamese, not Chinese. Preserve supplied real
presenter audio; do not substitute TTS. For prepared local media use the kit's
moneyprinter.py adapter. The existing talking-head-edit skill controls speech
cuts, actual Computer Use/Recordly demonstrations, version history and QC.
Keep publishing off unless separately requested. Request only missing provider
credentials for an actual cloud generation request. No paid confirmations are
implied by setup. A nonempty generated file is not release approval: inspect and
listen to the exact master, run kit QC and await final human sign-off. Report
NEEDS_REVIEW when evidence is missing. These overrides take precedence over the
conflicting defaults and delivery-only checks below.

'''
        text=text.replace('# MoneyPrinterTurbo Video Generation\n','# MoneyPrinterTurbo Video Generation\n\n'+notice,1)
    locator='Use kit_checkout in INSTALLATION.json if the active footage folder lacks the kit adapters.'
    if locator not in text:text=text.replace(marker,marker+'\n\n'+locator,1)
    entry.write_text(text,encoding='utf-8')
    data=dict(repo='https://github.com/duytaday/MoneyPrinterTurbo',commit='53c4ca3d85100eeb8660ec3d5e5f7c90bcc7849a',integration='talking-head-qc/integrations/moneyprinterturbo.md')
    data['kit_checkout']=str(Path(__file__).resolve().parents[2])
    (args.skill/'INSTALLATION.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(data,indent=2))

if __name__=='__main__':main()
