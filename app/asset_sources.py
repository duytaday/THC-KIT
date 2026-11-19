"""Public source discovery. Provider statements are provenance, not legal approval."""
import hashlib,html,re,urllib.parse

CATEGORIES={
 'ai_coding':['computer keyboard','programming','computer screen','robot','artificial intelligence'],
 'office':['office','desk','laptop','document','printer'],
 'teamwork':['teamwork','collaboration','meeting','brainstorming','workshop'],
 'ecommerce':['online shopping','warehouse','barcode','cashier','delivery package'],
 'learning':['classroom','student','studying','library books','writing notes'],
 'studio_devices':['camera equipment','microphone','filming','recording studio','headphones'],
 'city_life':['city street','pedestrian','public transport','cycling','cafe'],
 'nature':['forest','ocean waves','river','mountain','waterfall'],
 'abstract_data':['computer animation','data visualization','fractal','geometric animation','simulation'],
 'gestures_reactions':['hand gesture','smiling','clapping','waving','laughing']}
for category,terms in {
 'ai_coding':['"typing on laptop"','"stock footage" computer','"source code"'],
 'office':['"working at a desk"','"stock footage" office','"coworking"'],
 'teamwork':['"group discussion"','"people working together"','"coworkers"'],
 'ecommerce':['"packing boxes"','"shopping cart"','"stock footage" warehouse'],
 'learning':['"reading a book"','"writing notes"','"stock footage" student'],
 'studio_devices':['"video camera"','"audio mixer"','"filming equipment"'],
 'city_life':['"urban traffic"','"stock footage" city','"pedestrian crossing"'],
 'nature':['"ocean surf"','"forest walk"','"stock footage" nature'],
 'abstract_data':['"motion background"','"abstract animation"','"data animation"'],
 'gestures_reactions':['"thumbs up"','"hand clapping"','"facial expression"']}.items():
    CATEGORIES[category]=list(dict.fromkeys(CATEGORIES[category]+terms))
EXCLUDE=re.compile(r'\b(lecture|keynote|conference|interview|webinar|podcast|music video|trailer|porn|sex|sexual|execution|surgery)\b',re.I)

def plain(value):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>',' ',str(value)))).strip()

def validate_queries(value):
    if not isinstance(value,dict) or not value or set(value)-set(CATEGORIES):raise ValueError('Queries must map known library categories to search terms')
    if any(not isinstance(terms,list) or not terms or any(not isinstance(q,str) or not q.strip() or len(q)>200 for q in terms) for terms in value.values()):raise ValueError('Each category needs a nonempty list of1–200 character search terms')
    if sum(map(len,value.values()))>200:raise ValueError('Use at most200 terms per bounded discovery file')
    return {category:list(dict.fromkeys(q.strip() for q in terms)) for category,terms in value.items()}

def family_key(creator,title,date=''):
    title=re.sub(r'\.(mp4|webm|ogv|ogg|mov|mpe?g|avi)$','',title,flags=re.I).casefold()
    title=re.sub(r'[-_ ](?:lab|por|landscape|portrait|\d{3,4}p|hd|4k|vp9|av1|h264|h265)$','',title)
    title=re.sub(r'\b(?:16[-:]9|9[-:]16)\b','',title)
    title=re.sub(r'\b(?:vert|wide)\b(?=\s+(?:mp4|webm|mov)\b)','',title)
    return hashlib.sha256((str(creator)+'|'+title+'|'+date).encode()).hexdigest()

def commons(client,query,category,offset=0,limit=50):
    args=dict(action='query',generator='search',gsrsearch='filetype:video '+query,gsrnamespace=6,gsrlimit=limit,gsroffset=offset,prop='videoinfo',viprop='url|size|mime|derivatives|extmetadata',format='json',formatversion=2)
    data=client.json('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(args))
    if 'error' in data:raise ValueError('Commons API: '+str(data['error'].get('code')))
    records=[];rejected={}
    for page in sorted(data.get('query',{}).get('pages',[]),key=lambda p:p.get('index',0)):
        info=next(iter(page.get('videoinfo',[])),{});meta=info.get('extmetadata',{})
        field=lambda k:plain(meta.get(k,{}).get('value',''))
        title=field('ObjectName') or page['title'][5:];caption=field('ImageDescription')
        reason=None;duration=float(info.get('duration',0));width=int(info.get('width',0));height=int(info.get('height',0))
        if EXCLUDE.search(title):reason='off_topic_longform'
        elif not 3<=duration<=120:reason='duration_outside_short_source_policy'
        elif min(width,height)<480:reason='source_below_480p'
        elif info.get('size',0)>180*1024*1024:reason='source_exceeds_180MiB'
        elif not str(info.get('mime','')).startswith('video/'):reason='not_video'
        if reason:rejected[reason]=rejected.get(reason,0)+1;continue
        # Use the actual source, not transcoded variants as additional assets.
        url=info['url'];parsed=urllib.parse.urlsplit(url)
        url=urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,parsed.path,'',''))
        creator=field('Artist') or None
        title_key=re.sub(r'\.(mp4|webm|ogv|ogg|mov|mpe?g|avi)$','',title,flags=re.I).casefold()
        title_key=re.sub(r'\b(\d{3,4}p|hd|4k|vp9|av1|h264|h265)\b','',title_key)
        family=family_key(creator,title,field('DateTimeOriginal'))
        records.append(dict(provider='wikimedia_commons',provider_id=str(page['pageid']),source_kind='third_party',source_url=info['descriptionurl'],download_url=url,creator=creator,source_title=title,caption=caption[:1600],category=category,tags=[query,*field('Categories').split('|')[:12]],source_family_id='commons:'+family,parent_asset_ids=[],discovery_query=query,provider_dimensions=[width,height],provider_duration=duration,provider_size=info.get('size'),license=dict(name=field('LicenseShortName') or None,url=field('LicenseUrl') or None,attribution_required=field('AttributionRequired'),usage_terms=field('UsageTerms'),restrictions=field('Restrictions'),training_rights='not_determined'),ai_generated='declared' if re.search(r'\bAI.generated|generative AI\b',title+' '+caption+' '+field('Categories'),re.I) else 'not_declared',proof_kind='illustration'))
    return records,data.get('continue',{}).get('gsroffset'),rejected

def archive(client,query,category,offset=0,limit=20):
    """One original per public item; encodings in the same item never inflate quota."""
    import asset_quality
    from asset_http import RetryLater
    args=dict(q='mediatype:movies AND subject:"stock footage" AND ('+query+')',output='json',rows=limit,page=offset//limit+1,**{'fl[]':['identifier','title']})
    data=client.json('https://archive.org/advancedsearch.php?'+urllib.parse.urlencode(args,doseq=True))
    response=data.get('response',{});docs=response.get('docs',[]);records=[];rejected={}
    def reject(reason):rejected[reason]=rejected.get(reason,0)+1
    def text(value):return plain(' '.join(map(str,value)) if isinstance(value,list) else value or '')
    for page in docs:
        key=page.get('identifier');title=text(page.get('title'))
        if not key or EXCLUDE.search(title) or not asset_quality.assess(dict(source_title=title,category=category))['accepted']:
            reject('title_does_not_establish_requested_scene');continue
        try:info=client.json('https://archive.org/metadata/'+urllib.parse.quote(key,safe=''))
        except RetryLater:raise
        except (ValueError,RuntimeError):reject('metadata_unavailable');continue
        meta=info.get('metadata',{});license_url=text(meta.get('licenseurl'))
        if info.get('is_dark') or meta.get('access-restricted-item') in (True,'true','1'):
            reject('restricted_item_not_public');continue
        if re.search(r'/by-(?:nc|nd)',license_url,re.I):reject('declared_noncommercial_or_no_derivatives');continue
        choices=[]
        for file in info.get('files',[]):
            if file.get('source')!='original' or file.get('private') or not file.get('name','').lower().endswith(('.mp4','.webm','.ogv')):continue
            try:w,h,size,duration=int(file['width']),int(file['height']),int(file['size']),float(file['length'])
            except (KeyError,ValueError,TypeError):continue
            if min(w,h)>=480 and 0<size<=180*1024*1024 and 3<=duration<=120:choices.append((min(w,h)<1080,size,file))
        if not choices:reject('no_bounded_short_original_video');continue
        file=min(choices,key=lambda c:c[:2])[2];title=text(meta.get('title')) or title
        records.append(dict(provider='internet_archive',provider_id=key,source_kind='third_party',source_url='https://archive.org/details/'+urllib.parse.quote(key,safe=''),download_url='https://archive.org/download/'+urllib.parse.quote(key,safe='')+'/'+urllib.parse.quote(file['name'],safe=''),creator=text(meta.get('creator')) or None,source_title=title,caption=text(meta.get('description'))[:1600],category=category,tags=[query,category],source_family_id='internet_archive:'+key,parent_asset_ids=[],discovery_query=query,provider_dimensions=[int(file['width']),int(file['height'])],provider_duration=float(file['length']),provider_size=int(file['size']),license=dict(name='Publisher-declared license' if license_url else 'Not supplied',url=license_url or None,training_rights='not_determined',basis='Public item metadata is provenance, not inferred training authorization'),ai_generated='declared' if re.search(r'\bAI.generated|generative AI\b',title+' '+text(meta.get('subject'))+' '+text(meta.get('description')),re.I) else 'not_declared',proof_kind='illustration',provider_original_filename=file['name'],source_variants_counted=1))
    next_offset=offset+limit if docs and offset+limit<response.get('numFound',0) else None
    return records,next_offset,rejected
