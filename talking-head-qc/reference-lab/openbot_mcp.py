"""Connection status only. No undocumented MCP/API calls or fake bot responses."""
import json
import shutil
from pathlib import Path


def status():
    home=Path.home()
    return {'editor_host':'Codex desktop on Windows, not verified as OpenBot',
      'openbot':{'cli':shutil.which('openbot'),'data_directory_exists':(home/'.openbot').exists(),'connected':False},
      'mausbot':{'cli':shutil.which('mausbot'),'data_directory_exists':(home/'.openmausbot').exists(),'connected':False},
      'shared_folder_protocol':'qc_exchange.py; not live until a real bot returns a hash-bound result',
      'capabilities':{'current_agent_audio_input':False,'current_agent_selected_frame_vision':True,'maus_windows_host_desktop':'not certified by inspected upstream README; VM is a separate desktop'},
      'api_calls':0,'next':'Install/configure the intended desktop runtime and give its reviewer read-only access to review packages. Submit reviewer-task.md using an actually supported interface.'}


if __name__=='__main__':print(json.dumps(status(),ensure_ascii=False,indent=2))
