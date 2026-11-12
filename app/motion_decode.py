"""Optional full-spec JSON decoding, bound to current-source literals and anchors.

This only filters syntax/source-invariant choices. Geometry, readable holds,
coverage, motion and editorial quality still use the unchanged native validator
and exact-master review. No template/rules output is substituted.
"""
import hashlib,json,unicodedata
import motion_specs

VERSION='source_json_v1'
DEPENDENCY='0.11.3'


def obj(properties,required):return dict(type='object',properties=properties,required=required,additionalProperties=False)
def enum(values):return dict(enum=list(values))
def array(items,lo=0,hi=12):return dict(type='array',items=items,minItems=lo,maxItems=hi)
def number(lo,hi):return dict(type='number',minimum=lo,maximum=hi)


def schema(context):
    # Build only from source facts. Targets/RAG examples never supply these enums.
    anchors=context['anchors'];texts=list(dict.fromkeys(motion_specs.clean_text(t) for t in context.get('texts',[])))
    box=array(number(0,1),4,4);branches=[]
    for anchor in anchors:
        later=[a['id'] for a in anchors if a['frame']>anchor['frame']]
        key=obj(dict(frame=enum(range(61)),x=number(-1,1),y=number(-1,1),scale=number(.7,1.15),opacity=number(0,1),rotation=number(-45,45),ease=enum(('linear','smoothstep','ease_out'))),['frame','x','y','scale','opacity','ease'])
        base=dict(id=dict(type='string',pattern='[a-z][a-z0-9_-]{0,30}'),rect=box,anchor=enum([anchor['id']]),keyframes=array(key,2,8),
                  lead_frames=enum(range(min(30,anchor['frame'])+1)),exit_frames=enum(range(31)),hold_frames=enum(range(12,181)),theme=enum(('brand','paper','charcoal')))
        if texts:
            change=obj(dict(anchor=enum(later),text=enum(texts),emphasis_line=enum(range(3)),rect=box),['anchor','text']) if later else None
            branches.append(obj(dict(base,component=enum(c for c in motion_specs.COMPONENTS if c not in ('11','12','13')),text=enum(texts),font_size=number(38,92),
                emphasis_line=enum(range(3)),changes=array(change or {},0,8 if later else 0)),['id','component','text','rect','anchor','keyframes']))
        if anchor.get('roi') and context.get('proof') and anchor['kind'] in ('control','contact','result'):
            component={'control':'11','contact':'12','result':'13'}[anchor['kind']]
            # Source markers cannot anticipate or leave their actual target.
            stationary=obj(dict(frame=enum(range(61)),x=enum([0]),y=enum([0]),scale=enum([1]),opacity=number(0,1),rotation=enum([0]),ease=enum(('linear','smoothstep','ease_out'))),['frame','x','y','scale','opacity','ease'])
            branches.append(obj(dict(base,component=enum([component]),keyframes=array(stationary,2,8),lead_frames=enum([0])),['id','component','rect','anchor','keyframes']))
    sounds=[]
    for a in anchors:
        ids=['slide','chapter','tap']
        if context.get('proof') and a['kind']=='contact':ids.append('click')
        if context.get('proof') and a['kind']=='result':ids.append('chime')
        sounds.append(obj(dict(anchor=enum([a['id']]),id=enum(ids),gain_db=number(-60,-6)),['anchor','id']))
    evidence=['code','reconstruction','presenter']
    if (context.get('proof') or {}).get('data_class')=='real_screen':evidence.append('real_screen')
    required=context.get('layout_requirement')
    if required is not None and required not in ('host','shoulder','full','demo'):raise ValueError('Unknown declared layout requirement')
    types=['intro'] if required=='full' and context.get('request')=='intro' else motion_specs.SCENE_TYPES
    return obj(dict(v=enum([1]),scene_type=enum(types),layout=enum([required] if required else ('host','shoulder','full','demo')),
        objects=array(dict(anyOf=branches) if branches else {},0,12 if branches else 0),sfx=array(dict(anyOf=sounds)),
        evidence=enum(evidence),missing=array(dict(type='string',minLength=1,maxLength=300)),rationale=dict(type='string',maxLength=600)),
        ['v','scene_type','layout','objects','evidence'])


def parser(context):
    import importlib.metadata
    if importlib.metadata.version('lm-format-enforcer')!=DEPENDENCY:raise ValueError('Use pinned lm-format-enforcer'+DEPENDENCY+' in the optional animation runtime')
    from lmformatenforcer import JsonSchemaParser,CharacterLevelParserConfig
    from lmformatenforcer.characterlevelparser import CharacterLevelParser,UnionParser
    from lmformatenforcer.jsonschemaparser import ListParsingState
    configuration=CharacterLevelParserConfig()
    # Keep Vietnamese free-form notes expressible; visible text uses exact enums.
    extra=''.join(chr(c) for c in range(0x1ea0,0x1efa))+'ăâđêôơưĂÂĐÊÔƠƯ'
    extra+=''.join(context.get('texts',[]))+context.get('quote','')
    configuration.alphabet=''.join(dict.fromkeys(configuration.alphabet+unicodedata.normalize('NFC',extra)))
    def empty_lists(p):
        # 0.11.3 pushes a possible first item even when maxItems=0. Remove only
        # that impossible item parser, preserving literal [] and whitespace.
        # Version-gated compatibility shim; never edits the installed package.
        if isinstance(p,UnionParser):
            options=[];seen=set()
            for child in p.parsers:
                child=empty_lists(child);key=None
                if isinstance(child,JsonSchemaParser) and child.object_stack:
                    top=child.object_stack[-1]
                    if isinstance(top,ListParsingState) and top.max_items==0 and top.seen_list_opener and not top.seen_list_closer:
                        # The library forked the same empty-list prefix once per
                        # possible item type. These identical prefixes must merge
                        # before another empty list multiplies them exponentially.
                        key=(tuple(map(id,child.object_stack)),child.last_parsed_string,child.last_non_whitespace_character,child.num_consecutive_whitespaces)
                if key is not None and key in seen:continue
                if key is not None:seen.add(key)
                options.append(child)
            return options[0] if len(options)==1 else UnionParser(options)
        if isinstance(p,JsonSchemaParser):
            for i,state in enumerate(p.object_stack):
                if isinstance(state,ListParsingState) and state.max_items==0 and state.seen_list_opener and not state.seen_list_closer:
                    clean=JsonSchemaParser(p.context,p.config,p.object_stack[:i+1],p.num_consecutive_whitespaces)
                    clean.last_parsed_string=p.last_parsed_string;clean.last_non_whitespace_character=p.last_non_whitespace_character
                    return clean
        return p
    class EmptyArrayGuard(CharacterLevelParser):
        def __init__(self,inner):super().__init__(configuration);self.inner=empty_lists(inner)
        def add_character(self,char):return EmptyArrayGuard(self.inner.add_character(char))
        def get_allowed_characters(self):return self.inner.get_allowed_characters()
        def can_end(self):return self.inner.can_end()
        def shortcut_key(self):return self.inner.shortcut_key()
        def cache_key(self):return self.inner.cache_key()
    return EmptyArrayGuard(JsonSchemaParser(schema(context),config=configuration))


def fingerprint(context):return hashlib.sha256(json.dumps(schema(context),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
