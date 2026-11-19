"""Conservative source relevance; search match alone never establishes suitability."""
import re,time

BAD_TITLE=re.compile(r'how[ -]to|tutorial|keyboard shortcuts|\blesson\b|phrase of the week|ken.?burns|restor.{0,15}\bai\b|\bai.{0,15}restor|recap|\bswns\b|\bcctv\b|\btrailer\b|\bspeech\b|\bkeynote\b|\binterview\b|conference|\bwebinar\b|\blecture\b|warehouse camera',re.I)
MILITARY=re.compile(r'\b(army|navy|military|battalion|brigade|soldiers?|marines|weapon|missile|combat|crucible|def-tech|armed|tank|attack|shelling|bombing)\b',re.I)
PATTERNS={
 'ai_coding':r'keyboard|typing|programming|\bcoding\b|source code|robot|neural network|data cent[er]',
 'office':r'\boffice\b|\bdesk\b|paperwork|photocop|printer|spreadsheet|stationery|workspace|typing|typewriter',
 'teamwork':r'teamwork|collaborat|brainstorm|co.?workers|colleagues|business meeting|team meeting|group discussion|workshop',
 'ecommerce':r'warehouse|barcode|checkout|shopping|cashier|fulfil|parcel|packag|shipping|supermarket|retail|e.?commerce|delivery',
 'learning':r'student|classroom|studying|reading|writing|notebook|\bbooks?\b|\blibrary\b',
 'studio_devices':r'microphone|\bcamera\b|tripod|filming|sound mixer|headphones|recording studio',
 'city_life':r'street|\bcity\b|pedestrian|\btram\b|\btrain\b|cycling|cafe|traffic|urban|crosswalk|\bbus\b|skyscraper',
 'nature':r'forest|ocean|waves|river|mountain|falls|waterfall|beach|lake|sunset|cloud|rain|snow|tree|landscape|icicle',
 'abstract_data':r'animation|data|visualization|visualisation|fractal|geometric|simulation|abstract|particles|timelapse',
 'gestures_reactions':r'hand.?wave|hand.?gesture|smil|clapp|laugh|applau|thumbs.up|waving.hand'}

def assess(record):
    title=record['source_title'];caption=record.get('caption','')
    if re.search(r'\b(porn|sex|sexual|protests?|blockades?)\b|student movement',title,re.I):return dict(accepted=False,reason='adult_or_political_event_outside_requested_generic_broll')
    if re.search(r'\b(president|prime minister|senator|campaign rally|oval office|biden|trump|snowden|hit.and.run|traffic collision|caught on camera)\b',title,re.I):return dict(accepted=False,reason='political_news_or_surveillance_not_generic_business_stock')
    if BAD_TITLE.search(title):return dict(accepted=False,reason='tutorial_news_slideshow_or_longform_not_generic_broll')
    if MILITARY.search(title+' '+caption[:500]):return dict(accepted=False,reason='military_or_weapons_outside_requested_business_topics')
    if record['category']=='studio_devices' and re.search(r'martian|mars|telescope|supercam|spacecraft',title,re.I):return dict(accepted=False,reason='scientific_capture_not_studio_equipment')
    if record['category']=='gestures_reactions' and re.search(r'\bflag\b|equation|function|sign.language',title,re.I):return dict(accepted=False,reason='not_generic_viewer_reaction')
    if record['category']=='gestures_reactions' and re.search(r'spacecraft|nhs|plasma|\bwaveform\b',title,re.I):return dict(accepted=False,reason='keyword_is_not_a_visible_human_gesture')
    if record['category']=='ecommerce' and re.search(r'\bfire\b|smoke|rally|disaster|collision',title,re.I):return dict(accepted=False,reason='incident_or_event_not_commerce_workflow')
    if record['category']=='teamwork' and re.search(r'\bworkshop\b',title,re.I) and not re.search(r'collaborat|group.discussion|team.work',title,re.I):return dict(accepted=False,reason='workshop_title_does_not_establish_collaboration')
    if re.search(PATTERNS[record['category']],title,re.I):return dict(accepted=True,reason='Explicit topic in source title; batch pixels still need inspection',confidence=.7)
    # A long page can mention everything. Do not treat stray body keywords as proof.
    return dict(accepted=False,reason='source_title_does_not_establish_requested_topic')

def apply(record):
    result=assess(record);record['relevance']=dict(result,basis='metadata_topic_filter_v2',human_approved=False)
    if not result['accepted']:
        record['states']['edit_ready']=False
        if not record['states']['downloaded']:record['stage']='topic_rejected'
    return record

def review(store,document,evidence_file):
    """Agent batch visual review is explicit and never becomes a human label."""
    from engine import media
    from pathlib import Path
    from asset_sources import CATEGORIES
    if document.get('format')!='thc-asset-review-v1' or document.get('reviewer_kind')!='agent':raise ValueError('This automated intake records agent reviews only')
    evidence=Path(evidence_file).resolve(strict=True)
    if media.sha(evidence)!=document['evidence_sha256']:raise ValueError('Review evidence changed')
    updated=[];prepared=[];replayed=0
    for decision in document['items']:
        r=store.get(decision['asset_id'])
        if not r or not r['states']['verified'] or r['sha256']!=decision['source_sha256'] or media.sha(r['local_path'])!=r['sha256']:raise ValueError('Review source changed or not verified')
        if type(decision.get('accepted')) is not bool or len(decision.get('notes',''))<20:raise ValueError('Record a concrete observed reason')
        category=decision.get('category',r['category'])
        if category not in CATEGORIES:raise ValueError('Unknown category')
        prior=r.get('visual_review',{})
        if prior.get('evidence_sha256')==document['evidence_sha256'] and prior.get('accepted')==decision['accepted'] and prior.get('notes')==decision['notes'] and prior.get('reviewer')==document['reviewer'] and r['category']==category:
            replayed+=1;continue
        r['category']=category;r['states']['edit_ready']=decision['accepted'];r['states']['human_approved']=False
        r['relevance']=dict(accepted=decision['accepted'],reason=decision['notes'],basis='agent_decoded_frame_review',human_approved=False)
        observation=dict(reviewer=document['reviewer'],kind='agent_frame_inspection',evidence=str(evidence),evidence_sha256=document['evidence_sha256'],accepted=decision['accepted'],notes=decision['notes'],scope=document['scope'],human_approved=False,time=time.time())
        r.setdefault('visual_review_history',[]).append(observation);r['visual_review']=observation
        if decision['accepted']:r['quality_flags']=list(dict.fromkeys(r['quality_flags']+['sampled_visual_review_not_full_master_review']))
        store.inherit_split(r);prepared.append((r,r['updated_at']))
    with store.lock:
        store.db.execute('BEGIN IMMEDIATE')
        try:
            for r,revision in prepared:
                if store.get(r['asset_id'])['updated_at']!=revision:raise ValueError('Asset changed during review; reload the batch before applying')
                store.put(r,False);updated.append(r['asset_id'])
            store.db.commit()
        except BaseException:store.db.rollback();raise
    return dict(reviewed=len(updated),replayed=replayed,human_approved=False,training_started=False,stats=store.export())
