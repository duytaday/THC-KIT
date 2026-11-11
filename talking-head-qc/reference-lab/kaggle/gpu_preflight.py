import json
import platform
import time
from pathlib import Path
import torch

result={'runtime':'actual Kaggle private kernel','python':platform.python_version(),'torch':torch.__version__,'cuda_available':torch.cuda.is_available(),'torch_cuda':torch.version.cuda,'training_ran':False,'actual_model_training_steps':0,'data_uploaded':'hardware-test script only; no user footage or transcripts','gpus':[]}
for i in range(torch.cuda.device_count()):
    p=torch.cuda.get_device_properties(i);result['gpus'].append({'index':i,'name':p.name,'vram_bytes':p.total_memory})
if torch.cuda.is_available():
    start=time.monotonic();x=torch.randn(64,64,device='cuda',requires_grad=True);loss=(x@x).square().mean();loss.backward();torch.cuda.synchronize()
    result['hardware_fixture_forward_backward']={'success':True,'seconds':time.monotonic()-start,'loss':float(loss.detach().cpu()),'not_selector_training':True}
Path('/kaggle/working/gpu-preflight.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
