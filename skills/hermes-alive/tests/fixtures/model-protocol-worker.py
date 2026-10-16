"""Test-only protocol worker. Not a model/Core/fallback-quality simulation."""
import hashlib
import json
import sys
import time

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
request=json.loads(sys.stdin.buffer.read())
if request['task']=='sleep': time.sleep(30)
if request['task']=='fail':
    sys.stderr.write(request['runtime']['api_key'])
    raise SystemExit(2)
text=json.dumps(dict(model=request['runtime']['model'],has_identity=bool(request['identity']),
    fallback_count=len(request['runtime'].get('fallback_model') or [])))
evidence=dict(subject=request['subject'],session_id='synthetic-session',task_id='synthetic-task',turn_id='synthetic-turn',
    api_request_id='synthetic-request',requested_model=request['runtime']['model'],response_model='provider-reported-label',
    route_model=request['runtime']['model'],provider=request['runtime']['provider'],
    content_sha256=hashlib.sha256(text.encode()).hexdigest(),content_chars=len(text),
    source_contract='hermes.native.post_api_request.v2',request_attempt=1,api_started_at=1.0,authority_granted=False)
document=dict(version=1,status='completed',operation_id=request['operation_id'],request_id=request['request_id'],
    subject=request['subject'],request_digest=hashlib.sha256(canonical(request)).hexdigest(),
    context_digest=request['context_digest'],text=text,evidence=evidence,authority_granted=False,semantic_quality_qualified=False)
if request['task']=='wrong_context': document['context_digest']='wrong'
if request['task']=='mixed_text': document['text']='another generation'
if request['task']=='wrong_request': document['request_id']='foreign-request'
if request['task']=='authority': document['authority_granted']=True
if request['task']=='old_evidence': document['evidence']['source_contract']='hermes.native.post_api_request.v1'
if request['task']=='not_json':
    print('not a protocol'); raise SystemExit(0)
print(json.dumps(document,separators=(',',':')))
