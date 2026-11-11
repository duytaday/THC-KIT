"""Pinned local encoder setup: no system install or writes outside the workspace."""
import shutil,subprocess,urllib.request,zipfile
from pathlib import Path
from engine import media

URL='https://github.com/GyanD/codexffmpeg/releases/download/8.1.2/ffmpeg-8.1.2-essentials_build.zip'
SHA256='db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec'


def install(root,progress):
    dest=Path(root)/'tools/ffmpeg-8.1.2';dest.mkdir(parents=True,exist_ok=True);archive=dest/'download.zip'
    if not archive.exists() or media.sha(archive)!=SHA256:
        temporary=dest/'download.partial';done=0
        with urllib.request.urlopen(URL,timeout=60) as response,temporary.open('wb') as file:
            total=int(response.headers.get('Content-Length',0))
            while block:=response.read(1024*1024):
                file.write(block);done+=len(block);progress(f'Downloading FFmpeg locally: {done//1048576}MB'+(f' / {total//1048576}MB' if total else ''))
        if media.sha(temporary)!=SHA256:raise ValueError('FFmpeg download checksum differs from the pinned build. Existing tools were preserved.')
        temporary.replace(archive)
    progress('Checking local FFmpeg and FFprobe…');binary=dest/'bin';binary.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for name in ('ffmpeg.exe','ffprobe.exe'):
            member=next(n for n in z.namelist() if n.endswith('/bin/'+name));target=binary/name
            if not target.exists():
                with z.open(member) as source,target.open('xb') as file:shutil.copyfileobj(source,file)
        for name in ('LICENSE','README.txt'):
            members=[n for n in z.namelist() if n.rsplit('/',1)[-1]==name]
            if members:(dest/name).write_bytes(z.read(members[0]))
    versions={}
    for name in ('ffmpeg','ffprobe'):
        process=subprocess.run([str(binary/(name+'.exe')),'-version'],capture_output=True,text=True,timeout=20,**media.launch_options())
        if process.returncode:raise ValueError('Local '+name+' cannot start. See '+str(dest))
        versions[name]=process.stdout.splitlines()[0]
    for flag,required in (('-encoders','libx264'),('-filters','ass')):
        process=subprocess.run([str(binary/'ffmpeg.exe'),'-hide_banner',flag],capture_output=True,text=True,timeout=20,**media.launch_options())
        if process.returncode or required not in process.stdout:raise ValueError('Downloaded FFmpeg lacks the required '+required+' feature')
    media.write_json(dest/'install-receipt.json',dict(url=URL,archive_sha256=SHA256,versions=versions,files={n:media.sha(binary/n) for n in ('ffmpeg.exe','ffprobe.exe')},
        destination=str(dest),system_install=False,source_and_terms='https://www.gyan.dev/ffmpeg/builds/; see LICENSE in this folder'))
