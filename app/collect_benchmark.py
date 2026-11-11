"""Collect immutable UI exports, cue metadata and a loudness-matched blind audition."""
import argparse,csv,json,random,shutil,subprocess
from pathlib import Path
from engine import media
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
run=json.loads((a.run/'results.json').read_text(encoding='utf-8'));ws=json.loads((a.workspace/'workspace.json').read_text(encoding='utf-8'));a.out.mkdir(parents=True,exist_ok=False);records=[]
for item in run['exports']:
    e=next(x for x in ws['exports'] if x['id']==item['export']['id']);source=Path(e['folder']);dest=a.out/item['name'];shutil.copytree(source,dest)
    qc=json.loads((dest/'qc.json').read_text(encoding='utf-8'));sheet=json.loads((dest/'cue-sheet.json').read_text(encoding='utf-8'));offsets={c['id']:c for c in qc['measurements']['cue_offsets']}
    for cue in sheet['cues']:
        cue['decoded_timing_evidence']=offsets.get(cue['id'],{'status':'N/A: intentionally silent'})
        cue['protected_speech']='Entire original presenter sentence; specifically CTA / bấm vào đây nè at~00:06.05–00:07.55. Full intelligibility remains unverified.'
    media.write_json(dest/'review-cue-sheet.json',sheet)
    with (dest/'cue-sheet.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['cue','source_seconds','master_frame','master_seconds','sound','route','expected_offset_frames','observed_offset_frames','final_mix','reference','listening'])
        for cue in sheet['cues']:
            measured=offsets.get(cue['id'],{});writer.writerow([cue['id'],cue['source_anchor']['source_pts'],cue['master_frame'],cue['master_seconds'],cue['sound'].get('id'),cue['route'],cue.get('expected_offset_frames'),measured.get('offset_frames'),measured.get('final_mix_crosscheck'),json.dumps(cue.get('reference_evidence'),ensure_ascii=False),cue['listening']])
    records.append(dict(name=item['name'],export_id=e['id'],revision=e['revision'],master=str((dest/'edit.mp4').resolve()),sha256=media.sha(dest/'edit.mp4'),status=qc['status'],measurements=qc['measurements'],codec='h264',audio_sample_rate=48000,source_ids=item['source_ids']))
    print(item['name'],qc['status'],qc['measurements']['integrated_lufs'],qc['measurements']['true_peak_dbtp'],flush=True)
comparison=a.out/'blind-comparison';comparison.mkdir();selected=records[:3];random.Random(20261111).shuffle(selected);mapping=[]
target=min(r['measurements']['integrated_lufs'] for r in selected)-.1
for i,r in enumerate(selected,1):
    output=comparison/f'Preview-{i}.mp4';gain=target-r['measurements']['integrated_lufs']
    media.ff('-i',r['master'],'-map','0:v:0','-map','0:a:0','-c:v','copy','-af',f'volume={gain}dB','-c:a','aac','-ar','48000','-b:a','192k','-movflags','+faststart',output)
    measured=media.loudness(output);mapping.append(dict(label=f'Preview {i}',name=r['name'],source_master_sha256=r['sha256'],sha256=media.sha(output),integrated_lufs=measured['input_i'],true_peak_dbtp=measured['input_tp']))
media.write_json(comparison/'mapping.private.json',mapping)
media.write_json(comparison/'review-results.json',dict(reviewers=0,preferences={},ties=0,disagreement=None,status='NEEDS_REVIEW',critical_phrase='CTA / bấm vào đây nè',questions=['Bạn vừa thấy bấm nút nào?','Kết quả sau khi bấm là gì?','Hãy chép lại cụm từ quanh cue bận nhất.','Nghe được accent nào? Nhạc có làm mất tập trung không?'],target_lufs=target,actual_lufs=[r['integrated_lufs'] for r in mapping]))
(comparison/'index.html').write_text('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Blind review</title><style>body{font:16px system-ui;background:#f7f6f0;color:#182721;max-width:1000px;margin:30px auto;padding:20px}main{display:flex;gap:20px;flex-wrap:wrap}video{width:270px;max-width:100%}label{display:block}</style><h1>So sánh ở tốc độ thật</h1><p>Cùng nguồn và mức nghe. Chưa có reviewer nghe toàn bộ; chưa chọn bản thắng.</p><main>'+''.join(f'<section><h2>Preview {i}</h2><video controls src="Preview-{i}.mp4"></video></section>' for i in range(1,4))+'</main><p>Ghi timecode và lý do: độ rõ thao tác, motion tự nhiên, lời nói dễ nghe; có thể chọn hòa.</p>',encoding='utf-8')
media.write_json(a.out/'masters.json',dict(masters=records,blind_comparison='blind-comparison/index.html',release='NEEDS_REVIEW',no_audio_capable_reviewer=True))
