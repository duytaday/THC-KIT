"""Explicit source associations. Supplied footage remains editorially unverified."""
import copy,unicodedata
from engine import media


def key(value):return unicodedata.normalize('NFC',value).strip().casefold()


def assignment(item,asset):
    result={}
    for field,limit in (('demonstrates',140),('visual_claim',400)):
        value=item.get(field,'')
        if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 for c in value):raise ValueError(f'{field} needs plain text of up to {limit} characters')
        if value.strip():result[field]=unicodedata.normalize('NFC',value.strip())
    if result.get('visual_claim') and not result.get('demonstrates'):raise ValueError('Name the demonstration subject before describing its visible proof')
    if result and (asset.get('media_is_reusable_proof') is False or asset.get('data_class') not in (None,'real_screen')):raise ValueError('An illustration can be a cutaway, but cannot be assigned as real demonstration proof')
    return result


def candidates(proof,subject):
    return [q for q in proof if key(q.get('demonstrates',''))==key(subject)
        and q.get('artifact_type')!='introduction' and q.get('artifact_kind') not in ('process','list','generated_video','reference_excerpt')
        and q.get('media_is_reusable_proof') is not False and q.get('data_class') in (None,'real_screen')]


def followups(requirements,proof):
    result=[]
    for requirement in requirements:
        sources=[]
        for q in candidates(proof,requirement['subject']):
            sources.append(dict(id=q.get('id'),source=q['file'],source_sha256=media.sha(q['file']),
                source_range=[q['source_start'],q['source_start']+q['end']-q['start']],timeline_source_range=[q['start'],q['end']],
                claimed_visible=q.get('visual_claim',''),spoken_cue=q.get('cue',''),observed_anchors=copy.deepcopy(q.get('anchors',{}))))
        result.append(dict(**copy.deepcopy(requirement),status='PROVIDED_UNVERIFIED' if sources else 'UNASSIGNED',
            association='explicit_source_assignment',sources=sources,editorial_verified=False))
    return result


def frozen_followups(profile):
    if 'proof_followups' in profile:return copy.deepcopy(profile['proof_followups'])
    # Legacy files can only describe their frozen profile, not today's workspace.
    groups={}
    for d in profile.get('demonstrations',[]):
        if d.get('repo_name'):groups.setdefault(d['repo_name'],[]).append(d)
    return [dict(subject=subject,claim='Review this repository’s promised behavior against the frozen brief.',
        status='UNASSIGNED' if all(not r.get('source_asset') and r.get('source_sha256') in (None,'0'*64) for r in rows) else 'LEGACY_UNVERIFIED',association='legacy_profile_only',sources=copy.deepcopy(rows),editorial_verified=False)
        for subject,rows in groups.items()]
