"""Redacted request identities. Shared bytes never imply a model cache hit."""
import hashlib
import json
from pathlib import Path
import motion_learning
import motion_specs
from engine import media

VERSION='request-observability-v1'


def sha(value):
    payload=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def describe(context,examples,version,identity=None,options=None):
    messages=motion_learning.messages(context,examples,version)
    encoded=json.dumps(messages,ensure_ascii=False,separators=(',',':')).encode()
    prefix=json.dumps(messages[:-1],ensure_ascii=False,separators=(',',':')).encode()
    identity=identity or {};options=options or {}
    return dict(version=VERSION,prompt_version=version,messages_sha256=sha(encoded),message_bytes=len(encoded),
                stable_message_prefix_sha256=sha(prefix),prefix_message_bytes=len(prefix),
                semantic_request_sha256=sha(dict(messages=messages,identity=identity,options=options)),
                builder_sha256=media.sha(Path(motion_learning.__file__)),observer_sha256=media.sha(Path(__file__)),schema_sha256=media.sha(Path(motion_specs.__file__)),
                retrieved_ids=[e.get('id') for e in examples],model_identity=identity,generation_options=options,
                tokenizer_input_tokens=None,token_ids_sha256=None,tokenized_prompt_sha256=None,
                prefill_seconds=None,time_to_first_token_seconds=None,generation_seconds=None,
                cache=dict(media_reuse=None,exact_result_reused=False,exact_result_lookup_performed=False,
                           model_prefix_reuse='NOT_IMPLEMENTED · fresh worker, no cross-request KV handoff',
                           provider_called=False,cache_read_tokens=None,cache_write_tokens=None),
                scope='Request identity only. No raw prompt or episode text in this receipt.')


def tokenized(receipt,prompt,token_ids):
    return {**receipt,'tokenizer_input_tokens':len(token_ids),'token_ids_sha256':sha(token_ids),
            'tokenized_prompt_sha256':sha(prompt.encode())}


def common_prefix(a,b):
    return next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))


def collect(root):
    """Read only sending-boundary receipts in this replay's own workspace."""
    rows=[]
    for file in sorted((Path(root)/'model-runs').glob('*/request-observability.json')):
        try:
            content=file.read_bytes();value=json.loads(content)
            rows.append(dict(run=file.parent.name,receipt_sha256=sha(content),receipt=value))
        except (OSError,ValueError):
            rows.append(dict(run=file.parent.name,status='INCOMPLETE_RECEIPT · inspect the same run before retrying'))
    return rows
