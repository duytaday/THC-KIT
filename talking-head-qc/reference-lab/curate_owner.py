"""Selected-frame reference cards + explicitly UNAPPROVED training proposals."""
import argparse
import copy
import html
import json
from pathlib import Path
from video_kit import read,write,scan

# Each observation below was inspected in the actual corpus002 contact sheets.
OBS={
1:[('host','Presenter with sparse word caption','NO_EFFECT'),('screen','Floating phone prompt over presenter','screen-reveal'),('cta','Presenter with Headshot keyword CTA above head','NO_EFFECT')],
2:[('labels','Tier list graphic below presenter','tool-label'),('labels','More tool icons placed into comparison grid','tool-label'),('labels','Dense completed tier list beside speaking presenter','NO_EFFECT')],
3:[('screen','Phone prompt UI over presenter','screen-reveal'),('proof','Large generated-photo example over presenter','proof-hold'),('cta','Presenter and Tricks CTA','NO_EFFECT')],
4:[('screen','Blender page inset over presenter','screen-reveal'),('screen','Sandcastles actual page inset over presenter','screen-reveal'),('cta','Presenter and Connect CTA','NO_EFFECT')],
5:[('proof','Skiing result footage above presenter cutout','proof-hold'),('screen','Image-input video tool page and thumbnails','screen-reveal'),('proof','Full-frame interior result example','proof-hold')],
6:[('labels','Handwrittennotes name above presenter','tool-label'),('proof','Handwritten-notes page fills focal region','proof-hold'),('cta','Presenter and Study CTA','NO_EFFECT')],
7:[('host','Presenter asks which tool for cinematic B-roll','NO_EFFECT'),('labels','Large tilted/blurred tool icon beside presenter','tool-label'),('cta','Presenter and Stack CTA plus follow button','NO_EFFECT')],
9:[('screen','Profile report inset over presenter','screen-reveal'),('screen','Prompt-entry page with empty response area','screen-reveal'),('cta','Presenter and Profile CTA','NO_EFFECT')],
11:[('labels','Bad/good/great cards above presenter','tool-label'),('labels','Next tool category keeps comparison anchors','tool-label'),('host','Presenter with existing comparison graphics','NO_EFFECT')],
12:[('screen','Actual search result for Lovable','screen-reveal'),('screen','Lovable input page fills picture','screen-reveal'),('cta','Presenter and Build CTA','NO_EFFECT')],
14:[('screen','PDF attachment and input context menu inset','screen-reveal'),('proof','Illustrated study-page result overlay','proof-hold'),('cta','Presenter and Study CTA','NO_EFFECT')],
17:[('screen','Room image request UI over presenter','screen-reveal'),('screen','Next prompt in room-image workflow','screen-reveal'),('cta','Presenter and Tricks CTA','NO_EFFECT')],
18:[('screen','Actual ChatGPT search result','screen-reveal'),('proof','Loaded discount-code table inset','proof-hold'),('cta','Presenter and Discount CTA','NO_EFFECT')],
19:[('screen','Photo input and processing state','screen-reveal'),('proof','Large output portrait example','proof-hold'),('cta','Presenter and Tricks CTA','NO_EFFECT')],
20:[('host','Presenter with one short word caption','NO_EFFECT'),('labels','Tool name and icon below presenter face','tool-label'),('cta','Presenter with simple Follow CTA','NO_EFFECT')],
21:[('proof','Editorial page and emphasized word card inset','proof-hold'),('proof','Client-services document example inset','proof-hold'),('screen','Messaging-sticker result window inset','screen-reveal')],
23:[('labels','Bodyguard label above presenter','tool-label'),('screen','Input image and flip command inset','screen-reveal'),('proof','Report with a line highlighted in red','proof-hold')],
24:[('proof','Four room before/after example panels','proof-hold'),('screen','Room-photo input and prompt in real UI','screen-reveal'),('cta','Presenter and Room CTA','NO_EFFECT')],
25:[('host','Presenter with watermark claim headline; claim not fact-checked','NO_EFFECT'),('proof','Document-text example inset','proof-hold'),('cta','Presenter and Watermark CTA','NO_EFFECT')]
}


def main():
    p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('--inventory',type=Path,required=True);a=p.parse_args()
    intake=read(a.corpus/'intake.json');m=read(a.inventory/'references.json')
    right=copy.deepcopy(intake['rights'][0])
    for scope in ('view','index','train_commercial'):
        right['grants'][scope]['purpose']='Private local reference analysis and private Kaggle decision-model experiments per explicit user request; no raw video upload implied'
    right['cloud_training_destination']='Kaggle private; user explicitly requested2026-11-10'
    m['rights']=[r for r in m['rights'] if r['id']!=right['id']]+[right]
    by_id={x['id']:x for x in intake['assets']};source_assets=[]
    exclude={8:'Screen/image montage; no explanatory presenter confirmed',13:'Screen/image montage; no explanatory presenter confirmed',16:'Rain/garden footage; outside technology talking-head scope',22:'Screen-only software demonstration; supplemental style only',10:'Lower-resolution duplicate of owner-ref-004',15:'Exact duplicate of owner-ref-014'}
    for source in intake['assets']:
        asset=copy.deepcopy(source);n=int(asset['id'][-3:]);asset.update(role='style',presenter_verified=n in OBS,content_verified=n in OBS,family_reviewed=True,creator_id='unknown_creator',creator_identity_verified=False,lang='en' if read(a.corpus/asset['id']/'asr.json')['segments'] else None)
        if n==10:asset['family_id']=by_id['owner-ref-004']['family_id']
        if n==15:asset['family_id']=by_id['owner-ref-014']['family_id']
        asset['exclusion_reason']=exclude.get(n)
        source_assets.append(asset)
    # Fresh immutable corpus generation, never overwrite a manually edited index.
    a.inventory.mkdir(parents=True,exist_ok=True)
    if any(x['id'].startswith('owner-ref-') for x in m['assets']):raise ValueError('Owner corpus already imported; create/review a new corpus revision')
    m['assets']+=source_assets;drafts=[]
    choices=['screen-reveal','tool-label','proof-hold','NO_EFFECT','REVIEW']
    for n,observations in OBS.items():
        asset=next(x for x in source_assets if x['id']==f'owner-ref-{n:03}')
        asr=read(a.corpus/asset['id']/'asr.json')
        for k,(kind,visible,choice) in enumerate(observations):
            frame_index=(0,1,3)[k];t=asset['frame_times_seconds'][frame_index];start=max(0,round((t-.5)*1000));end=min(asset['duration_ms'],round((t+.5)*1000))
            nearby=[s for s in asr['segments'] if s['start']<=t+.5 and s['end']>=t-.5]
            cue=' '.join(s['text'].strip() for s in nearby)
            key=f"{asset['id']}-frame-{frame_index}"
            card={'id':key,'segment_id':key,'asset_id':asset['id'],'family_id':asset['family_id'],'asset_sha256':asset['sha256'],'rights_id':asset['rights_id'],'t_in_ms':start,'t_out_ms':end,'lang':'en','format':'9:16','spoken_intent':cue+' | intent tags: '+('giữ mặt không thêm hiệu ứng CTA' if choice=='NO_EFFECT' else 'tên công cụ nhãn cạnh vai người nói' if choice=='tool-label' else 'màn hình thao tác kết quả thật đọc được'),'visible_before':'Temporal transition before this selected frame not yet certified','visible_during':visible,'visible_after':'Temporal transition after this selected frame not yet certified','motion_parameters':{'status':'proposal, not measured reference easing','enter_ms':220,'hold_ms':1200,'exit_ms':180,'avoid':['face','captions','proof']},'editorial_reason':f'Selected frame at{t:.3f}s shows: {visible}. Candidate {choice}; speech and adjacent transition need review.','reviewer':'Codex visual selected-frame annotation','annotation_approved':True,'motion_type':'label' if choice=='tool-label' else 'hold' if choice=='NO_EFFECT' else 'proof' if choice=='proof-hold' else 'transition','recipe_id':choice,'observation_kind':'selected_frame_only','evidence_frame':str(a.corpus/asset['id']/f'frame-{frame_index}.png')}
            m['segments'].append(card)
            draft={'decision_id':key,'asset_id':asset['id'],'family_id':asset['family_id'],'episode_id':asset['family_id'],'creator_id':'unknown_creator','asset_sha256':asset['sha256'],'source_range_ms':[start,end],'cue':cue,'visible_before':card['visible_before'],'visible_after':visible,'choices':choices,'chosen':choice,'rejected':[x for x in choices if x!=choice],'reason':card['editorial_reason'],'reviewer':'UNREVIEWED_PROPOSAL','evidence_id':key,'rights_id':asset['rights_id'],'data_class':'production','human_approved':False,'requires_result':choice=='proof-hold','result_visible':choice=='proof-hold','keep_presenter':choice=='NO_EFFECT','shortlist':[],'temporal_context_approved':False}
            drafts.append(draft)
    write(a.inventory/'references.json',m);write(a.corpus/'curation.json',{'source_files':len(source_assets),'canonical_families':len({x['family_id'] for x in source_assets}),'talking_head_families':len(OBS),'excluded_or_duplicate':exclude,'draft_decisions':len(drafts),'human_approved_decisions':0,'engagement_verified':0,'note':'Owner attestation supports train scope; selected frames are research cards, not temporal training approval.'})
    (a.corpus/'draft-decisions.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in drafts)+'\n',encoding='utf-8')
    cards=[]
    for r in drafts:
        asset=next(x for x in source_assets if x['id']==r['asset_id']);frame=int(r['decision_id'][-1]);img=f"{asset['id']}/frame-{frame}.png";src=Path(asset['path']).as_uri();t=r['source_range_ms'][0]/1000
        cards.append(f'<article><h3>{html.escape(r["decision_id"])}</h3><img src="{img}" width="180"><p>{html.escape(r["cue"])}</p><p>{html.escape(r["visible_after"])}</p><video controls preload="none" src="{html.escape(src)}#t={max(0,t-4):.2f},{t+5:.2f}" width="240"></video><p>Đề xuất: <b>{r["chosen"]}</b>. Chưa duyệt ngữ cảnh trước/sau và lời nói.</p></article>')
    (a.corpus/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Reference decisions — review required</title><style>body{background:#101820;color:#fff;font:16px Arial;max-width:1100px;margin:30px auto}main{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}article{background:#202e37;padding:18px}video{max-width:100%}</style><h1>57 đề xuất — chưa dùng để train</h1><p>Xem cả cụm câu và diễn biến quanh frame. Chỉ chuyển nhãn sang approved sau khi editor xác nhận thời gian, lựa chọn và lý do; không coi ảnh này là bằng chứng đã nghe. Dùng draft-decisions.jsonl để ghi sửa. Bản huấn luyện phải có temporal_context_approved=true và human_approved=true, không duyệt hàng loạt chỉ từ thumbnail.</p><main>'+''.join(cards)+'</main>',encoding='utf-8')
    print(json.dumps(scan(a.inventory),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
