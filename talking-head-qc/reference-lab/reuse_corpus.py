"""Reuse ASR only for exact media SHA matches, never for merely similar videos."""
import argparse
import shutil
from pathlib import Path
from video_kit import read

p=argparse.ArgumentParser();p.add_argument('previous',type=Path);p.add_argument('current',type=Path);a=p.parse_args()
prior=read(a.previous/'intake.json');current=read(a.current/'intake.json');lookup={x['sha256']:x for x in prior['assets']}
count=0
for asset in current['assets']:
    old=lookup.get(asset['sha256'])
    if old and (a.previous/old['id']/'asr.json').exists():
        for name in ('asr.json','transcript.md'):
            dest=a.current/asset['id']/name
            if not dest.exists():shutil.copy2(a.previous/old['id']/name,dest)
        count+=1
print('Exact-hash ASR reuse:',count)
