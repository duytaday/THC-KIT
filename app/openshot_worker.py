"""Run with the separate Python/Qt/libOpenShot installation, never in the editor process."""
import json,os,sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
handles=[]
if os.environ.get('CUTROOM_OPENSHOT_DLL_DIR') and hasattr(os,'add_dll_directory'):
    handles.append(os.add_dll_directory(os.environ['CUTROOM_OPENSHOT_DLL_DIR']))
try:
    import openshot
    from PyQt5.QtWidgets import QApplication
    app=QApplication.instance() or QApplication([])
    if '--probe' in sys.argv:
        print(json.dumps(dict(engine='libopenshot',status='AVAILABLE',version=getattr(openshot,'OPENSHOT_VERSION_FULL_STRING','unknown'))));sys.exit(0)
    from pathlib import Path
    d=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'));output=Path(sys.argv[2])
    if output.exists():raise ValueError('Output already exists')
    timeline=openshot.Timeline(d['width'],d['height'],openshot.Fraction(30,1),48000,2,openshot.LAYOUT_STEREO)
    timeline.Open();clips=[]
    for item in d['clips']:
        c=openshot.Clip(item['file']);c.Open();c.Start(item['source_in']);c.End(item['source_out']);c.Position(item['timeline_in']);c.Layer(1);timeline.AddClip(c);clips.append(c)
    writer=openshot.FFmpegWriter(str(output))
    writer.SetVideoOptions(True,'libx264',openshot.Fraction(30,1),d['width'],d['height'],openshot.Fraction(1,1),False,False,4000000)
    writer.SetAudioOptions(True,'aac',48000,2,3,192000);writer.Open()
    frames=round(max(c['timeline_in']+c['source_out']-c['source_in'] for c in d['clips'])*30)
    for frame in range(1,frames+1):writer.WriteFrame(timeline.GetFrame(frame))
    writer.Close();timeline.Close()
    print(json.dumps(dict(frames=frames,editorial_review='NEEDS_REVIEW')))
except Exception as e:
    print(json.dumps(dict(engine='libopenshot',status='SETUP_REQUIRED' if '--probe' in sys.argv else 'FAILED',reason=str(e)[:800])))
    sys.exit(1)
