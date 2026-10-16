"""Private host/worker envelopes; checksums bind context, not model truth/consent."""
from dataclasses import asdict
import hashlib
import json
import math
import re


class NativeWorkerError(ValueError):
    pass


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/\-]{0,127}',value):
        raise NativeWorkerError('invalid worker identity')
    return value


def request_digest(document):
    return hashlib.sha256(canonical(document)).hexdigest()


def validate_request(document):
    expected={'version','operation_id','request_id','subject','task','context_digest','messages',
        'runtime','identity','temperature','max_tokens','budget_seconds'}
    if not isinstance(document,dict) or set(document)!=expected or type(document['version']) is not int or document['version']!=1:
        raise NativeWorkerError('unsupported native worker envelope')
    for key in ('operation_id','request_id','subject','task'): identifier(document[key])
    messages=document['messages']
    if (not isinstance(messages,list) or len(messages)!=2
            or any(not isinstance(m,dict) or set(m)!={'role','content'} for m in messages)
            or [m['role'] for m in messages]!=['system','user']
            or any(not isinstance(m['content'],str) or not 0<len(m['content'])<=64000 for m in messages)
            or document['context_digest']!=request_digest(messages)
            or not isinstance(document['identity'],str) or len(document['identity'])>16000
            or type(document['temperature']) not in (int,float) or not math.isfinite(document['temperature'])
            or not 0<=document['temperature']<=2 or type(document['max_tokens']) is not int
            or not 1<=document['max_tokens']<=8192 or type(document['budget_seconds']) not in (int,float)
            or not math.isfinite(document['budget_seconds']) or not 1<=document['budget_seconds']<=240):
        raise NativeWorkerError('invalid native worker context or budget')
    runtime=document['runtime']
    if isinstance(runtime,dict) and set(runtime)=={'host_snapshot'}:
        from .native_host_snapshot import validate_host_snapshot
        validate_host_snapshot(runtime['host_snapshot'])
        if len(canonical(document))>131072: raise NativeWorkerError('native worker input exceeds bound')
        return document
    allowed={'model','provider','base_url','api_key','api_mode','requested_provider','fallback_model',
        'request_overrides','reasoning_config','service_tier'}
    from .native_client_policy import ROUTING_FIELDS, validate_client_policy
    allowed |= ROUTING_FIELDS | {'client_policy'}
    if (not isinstance(runtime,dict) or set(runtime)-allowed
            or not all(isinstance(runtime.get(k),str) and runtime[k].strip() for k in ('model','provider','base_url','api_key','api_mode'))
            or runtime['api_mode'] not in ('chat_completions','anthropic_messages','codex_responses')):
        raise NativeWorkerError('native worker needs an admitted API route from Hermes')
    validate_text_overrides(runtime.get('request_overrides'))
    fallback=runtime.get('fallback_model')
    if fallback is not None:
        entries=[fallback] if isinstance(fallback,dict) else fallback
        if (not isinstance(entries,list) or len(entries)>8 or any(not isinstance(entry,dict)
                or not all(isinstance(entry.get(k),str) and entry[k].strip() for k in ('provider','model','api_key'))
                for entry in entries)):
            raise NativeWorkerError('fallback API capabilities must already be resolved by Hermes')
        for entry in entries:
            validate_text_overrides(entry.get('request_overrides'))
            if 'extra_body' in entry: validate_text_overrides({'extra_body':entry['extra_body']})
    validate_client_policy(runtime)
    # Whole finite JSON snapshot, not a live mutable config/client or callable key.
    if len(canonical(document))>131072: raise NativeWorkerError('native worker input exceeds bound')
    return document


def validate_text_overrides(value):
    overrides={} if value is None else value
    reserved={'model','messages','input','instructions','tools','tool_choice','functions','function_call',
        'stream','max_tokens','max_completion_tokens','max_output_tokens'}
    extra=overrides.get('extra_body',{}) if isinstance(overrides,dict) else None
    if not isinstance(overrides,dict) or reserved.intersection(overrides) or not isinstance(extra,dict) or reserved.intersection(extra):
        raise NativeWorkerError('route overrides exceed worker text-only boundary')


def completion_document(request,evidence,text):
    return dict(version=1,status='completed',operation_id=request['operation_id'],request_id=request['request_id'],
        subject=request['subject'],request_digest=request_digest(request),context_digest=request['context_digest'],
        text=text,evidence=asdict(evidence),authority_granted=False,semantic_quality_qualified=False)


def validate_completion(document,request):
    expected={'version','status','operation_id','request_id','subject','request_digest','context_digest',
        'text','evidence','authority_granted','semantic_quality_qualified'}
    if (not isinstance(document,dict) or set(document)!=expected or type(document['version']) is not int or document['version']!=1
            or document['status']!='completed' or document['request_digest']!=request_digest(request)
            or any(document[k]!=request[k] for k in ('operation_id','request_id','subject','context_digest'))
            or document['authority_granted'] is not False or document['semantic_quality_qualified'] is not False):
        raise NativeWorkerError('worker result belongs to another or failed request')
    from .native_completion import NativeCompletionEvidence
    try: evidence=NativeCompletionEvidence(**document['evidence'])
    except (TypeError,KeyError): raise NativeWorkerError('worker completion evidence malformed') from None
    text=document['text']
    if (not isinstance(text,str) or not 0<len(text)<=32000 or evidence.subject!=request['subject']
            or evidence.source_contract!='hermes.native.post_api_request.v2' or evidence.authority_granted is not False
            or type(evidence.request_attempt) is not int or not 1<=evidence.request_attempt<=16
            or type(evidence.api_started_at) not in (int,float) or not math.isfinite(evidence.api_started_at)
            or type(evidence.content_chars) is not int or evidence.content_chars!=len(text)
            or evidence.content_sha256!=hashlib.sha256(text.encode()).hexdigest()
            or any(not isinstance(v,str) or not v.strip() or len(v)>256 or not v.isprintable()
                for v in (evidence.session_id,evidence.task_id,evidence.turn_id,evidence.api_request_id))
            or any(not isinstance(v,str) or not v.strip() or len(v)>256 or not v.isprintable()
                for v in (evidence.response_model,evidence.provider,evidence.route_model,evidence.requested_model))):
        raise NativeWorkerError('worker final content differs from scoped completion')
    return text,evidence
