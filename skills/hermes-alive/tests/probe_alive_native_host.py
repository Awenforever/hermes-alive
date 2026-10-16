"""Actual retained Hermes constructor/prompt, synthetic profile, zero provider IO."""
import argparse
import asyncio
from datetime import datetime, timezone
import faulthandler
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
import httpx
from types import SimpleNamespace

faulthandler.enable()
faulthandler.dump_traceback_later(90,exit=True)
os.umask(0o077)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core',type=Path,required=True)
parser.add_argument('--kernel-package',type=Path,default=Path(__file__).resolve().parents[1])
args=parser.parse_args()
sys.path[:0]=[str(args.core),str(args.kernel_package/'hooks'),str(args.kernel_package/'tests')]
root=Path(tempfile.mkdtemp(prefix='alive-native-boundary-'))
profile=root/'profile'; profile.mkdir(mode=0o700)
home=root/'home'; home.mkdir(mode=0o700)
project=root/'project'; project.mkdir(mode=0o700)
os.environ['HERMES_HOME']=str(profile)
os.environ['HOME']=str(home)
os.environ['XDG_CONFIG_HOME']=str(home/'config')
os.environ['XDG_CACHE_HOME']=str(home/'cache')
os.environ['OPENAI_API_KEY']='synthetic-not-a-real-key'
os.environ['HERMES_SKIP_UPDATE_CHECK']='1'
os.chdir(project)
(profile/'config.yaml').write_text(json.dumps(dict(model=dict(default='synthetic-model',streaming=False),
    memory=dict(memory_enabled=False,user_profile_enabled=False),
    compression=dict(enabled=False),agent=dict(max_iterations=1))),encoding='utf-8')
(profile/'SOUL.md').write_text('SYNTHETIC_SOUL_BOUNDARY_153: Be a concise, candid assistant. Never pretend to be human.',encoding='utf-8')
(profile/'memories').mkdir()
(profile/'memories'/'MEMORY.md').write_text('FORBIDDEN_PRIVATE_MEMORY_153',encoding='utf-8')
(profile/'memories'/'USER.md').write_text('FORBIDDEN_PRIVATE_USER_153',encoding='utf-8')
(project/'AGENTS.md').write_text('FORBIDDEN_PROJECT_INSTRUCTIONS_153',encoding='utf-8')

attempts=[]
def audit(event,args):
    if event in ('socket.connect','socket.getaddrinfo'):
        attempts.append(dict(event=event,stack=[dict(file=Path(f.filename).name,function=f.name,line=f.lineno)
            for f in traceback.extract_stack(limit=10)[:-1]]))
        raise RuntimeError('native boundary probe forbids network')
sys.addaudithook(audit)

requests=[]; provider_requests=[]; provider_response_models=[]
def fake_http(client,request,*args,**kwargs):
    entry=dict(host=request.url.host,path=request.url.path,method=request.method)
    requests.append(entry)
    if request.url.host=='provider.invalid' and request.url.path=='/v1/chat/completions':
        if len(provider_requests)>=4: raise RuntimeError('synthetic provider call bound')
        body=json.loads(request.content)
        assert not body.get('stream') and not body.get('tools')
        provider_requests.append(body)
        provider_response_models.append('synthetic-returned-model')
        content='SYNTHETIC_PROPOSAL_153: no message was sent.'
        for message in body['messages']:
            if message['role']=='user' and isinstance(message['content'],str):
                try: evidence=json.loads(message['content'])
                except ValueError: continue
                if isinstance(evidence,dict) and 'opportunities' in evidence:
                    content=json.dumps(dict(candidates=[],abstentions=[dict(
                        agenda_item_id=e['agenda_item_id'],reason='synthetic deliberate silence')
                        for e in evidence['opportunities']]))
        return httpx.Response(200,request=request,json=dict(id='synthetic-completion-153',object='chat.completion',
            created=0,model='synthetic-returned-model',choices=[dict(index=0,finish_reason='stop',
            message=dict(role='assistant',content=content))],
            usage=dict(prompt_tokens=100,completion_tokens=15,total_tokens=115)))
    # Exercise explicit metadata unavailability, not an arbitrary successful body.
    return httpx.Response(503,request=request,json=dict(error=dict(message='synthetic offline metadata')))
httpx.Client.send=fake_http
async def fake_async_http(client,request,*args,**kwargs):
    return fake_http(client,request,*args,**kwargs)
httpx.AsyncClient.send=fake_async_http

from run_agent import AIAgent
agent=AIAgent(base_url='https://provider.invalid/v1',api_key='synthetic-not-a-real-key',
    provider='custom',model='synthetic-model',api_mode='chat_completions',
    enabled_toolsets=[],disabled_toolsets=[],max_iterations=1,run_budget_seconds=10,
    max_tokens=256,quiet_mode=True,save_trajectories=False,skip_context_files=True,
    load_soul_identity=True,skip_memory=True,skip_background_review=True,
    ephemeral_system_prompt='SYNTHETIC_ALIVE_TASK_153: Propose, never send.',
    session_id='alive-native-boundary-153',cwd=str(project))
print(json.dumps(dict(tools=len(agent.tools),valid_tools=sorted(agent.valid_tool_names),
    memory_store=agent._memory_store is not None,memory_manager=agent._memory_manager is not None,
    background_review_skipped=agent.skip_background_review,
    prompt_signature=str(inspect.signature(agent._build_system_prompt)),
    conversation_signature=str(inspect.signature(agent.run_conversation)),network_attempts=len(attempts))),flush=True)
assert not agent.tools and not agent.valid_tool_names
assert agent._memory_store is None and agent._memory_manager is None
prompt=agent._build_system_prompt()
assert isinstance(prompt,str)
checks=dict(soul='SYNTHETIC_SOUL_BOUNDARY_153' in prompt,task='SYNTHETIC_ALIVE_TASK_153' in prompt,
    private_memory='FORBIDDEN_PRIVATE_MEMORY_153' in prompt,
    private_user='FORBIDDEN_PRIVATE_USER_153' in prompt,
    project_instructions='FORBIDDEN_PROJECT_INSTRUCTIONS_153' in prompt)
print(json.dumps(dict(prompt_chars=len(prompt),prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
    checks=checks,network_attempts=attempts)),flush=True)
assert checks['soul'] and not checks['task'] and not any(checks[k] for k in ('private_memory','private_user','project_instructions'))
result=agent.run_conversation('SYNTHETIC_CURRENT_CONTEXT_153: Draft a proposal only, do not perform actions.')
print(json.dumps(dict(result_keys=sorted(result),provider_calls=len(provider_requests),
    network_attempts=len(attempts),request_routes=requests)),flush=True)
assert len(provider_requests)==1
wire=json.dumps(provider_requests[0],ensure_ascii=False)
assert 'SYNTHETIC_SOUL_BOUNDARY_153' in wire and 'SYNTHETIC_ALIVE_TASK_153' in wire
assert 'SYNTHETIC_CURRENT_CONTEXT_153' in wire
assert not any(s in wire for s in ('FORBIDDEN_PRIVATE_MEMORY_153','FORBIDDEN_PRIVATE_USER_153','FORBIDDEN_PROJECT_INSTRUCTIONS_153'))
assert result.get('final_response')=='SYNTHETIC_PROPOSAL_153: no message was sent.'
assert not attempts
agent.close()
print('HERMES_ALIVE_NATIVE_CONSTRUCTOR_PROMPT_BOUNDARY_OK',flush=True)

# Canonical Alive sources -> actual Core agent -> wire -> shadow disposition.
# All records/grants/receipts below are synthetic testkit material, not external
# evidence or a live authenticated user's feedback.
from probe_alive_live_feedback import prepare_case
from alive_kernel import (AutonomyPolicyProjection,DiscoveryCandidate,DiscoveryOpportunityIngestor,
    EventEnvelope,PolicyContext,Sensitivity,MemoryProjection,MemoryProposal,MemoryKind,MemoryAuthority)
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.agenda import AgendaProjection,AgendaProposal,AgendaAuthority,AgendaItemKind

feedback_marker='SYNTHETIC_RETAINED_CORRECTION_153'
interpreter,owner,outcome=prepare_case(root/'kernel',dict(id='native153',
    sent='Synthetic prior reading tip.',reply=feedback_marker+': Today I am busy; this is not a permanent dislike.'))
journal=interpreter.journal
memories=MemoryProjection(journal)
own_memory_marker='SYNTHETIC_EXPLICIT_INTEREST_153'
own_memory=None
for memory_owner,value in ((owner,own_memory_marker),('user:foreign-native153','FORBIDDEN_FOREIGN_MEMORY_153')):
    memory_source=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor=memory_owner,subject=memory_owner,payload={'synthetic':True}))
    proposal=MemoryProposal(kind=MemoryKind.PREFERENCE,subject=memory_owner,predicate='profile.reading',value=value,
        authority=MemoryAuthority.USER_EXPLICIT,source_event_ids=(memory_source.event.event_id,),confidence=1)
    memories.append_proposal(proposal,actor=memory_owner)
    if memory_owner==owner: own_memory=proposal.proposal_id
source=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
    actor=owner,subject=owner,payload={'synthetic':True}))
agenda=AgendaProjection(journal)
agenda.apply(agenda.append_proposal(AgendaProposal(kind=AgendaItemKind.COMMITMENT,subject=owner,
    details=dict(task='SYNTHETIC_ACTIVE_COMMITMENT_153',constraint='remind only'),
    authority=AgendaAuthority.USER_EXPLICIT,source_event_ids=(source.event.event_id,),confidence=1),actor=owner))
DiscoveryOpportunityIngestor(journal,content_vault=interpreter.vault).ingest(DiscoveryCandidate(
    source='synthetic',title='SYNTHETIC_DISCOVERY_153',summary='A preliminary public reading observation.',
    url='https://example.invalid/native153',observed_at=datetime.now(timezone.utc)),subject=owner)
policies=AutonomyPolicyProjection(journal)
policies.project_new()
current=policies.current(owner)
assert policies.apply(policies.append_update(subject=owner,actor=owner,
    expected_revision=current.revision if current else 0,enabled=True,
    context=PolicyContext(can_interrupt=True),operation_id='native153-enable')).outcome=='recorded'
before={name:len(journal.read(event_type=name)) for name in (
    'action.attempted','dispatch.started','memory.proposed','preference.observed')}
native_calls=[]
async def native_call(**kwargs):
    assert kwargs['task']=='alive_opportunity_candidates'
    native_calls.append(kwargs['task'])
    # Never share the foreground session, history, tools or memory manager.
    child=AIAgent(base_url='https://provider.invalid/v1',api_key='synthetic-not-a-real-key',
        provider='custom',model='synthetic-model',api_mode='chat_completions',
        enabled_toolsets=[],disabled_toolsets=[],max_iterations=1,run_budget_seconds=10,max_tokens=512,
        quiet_mode=True,save_trajectories=False,skip_context_files=True,load_soul_identity=True,
        skip_memory=True,skip_background_review=True,cwd=str(project),
        session_id='alive-native-shadow-'+str(len(native_calls)),
        ephemeral_system_prompt=kwargs['messages'][0]['content'])
    try:
        assert not child.tools and child._memory_manager is None and child._memory_store is None
        result=child.run_conversation(kwargs['messages'][1]['content'],conversation_history=[])
        print(json.dumps(dict(native_result={key:result.get(key) for key in (
            'completed','failed','model','served_model','turn_exit_reason','final_response')})),flush=True)
        assert result['completed'] and not result['failed']
        # In this stock Core the turn result reports the configured route and
        # served_model means a proxy header/fallback, not the JSON response model.
        # This diagnostic knows the fake provider body at the HTTP boundary; a
        # production adapter must obtain scoped response evidence, never guess.
        assert result['served_model'] is None and result['model']=='synthetic-model'
        return SimpleNamespace(model=provider_response_models[-1],choices=[SimpleNamespace(
            message=SimpleNamespace(content=result['final_response']))])
    except Exception as error:
        print('NATIVE_CALLBACK_ERROR='+type(error).__name__+':'+str(error),flush=True)
        raise
    finally: child.close()

async def shadow():
    runtime=AutonomousCycleRuntime(journal,content_vault=interpreter.vault)
    params=dict(subject=owner,expression_parameters=dict(call=native_call,
        resolve_domain=lambda provider,model:'synthetic-family'),resolve_binding=lambda record:None)
    result=await runtime.cycle(operation_id='native-shadow-first',**params)
    assert result.disposition=='silence' and len(native_calls)==1
    first_wire=json.dumps(provider_requests[-1],ensure_ascii=False)
    assert all(text in first_wire for text in (feedback_marker,'SYNTHETIC_ACTIVE_COMMITMENT_153',
        'SYNTHETIC_DISCOVERY_153','SYNTHETIC_SOUL_BOUNDARY_153','literal_attributed_feedback_not_profile_update',own_memory_marker))
    assert 'FORBIDDEN_FOREIGN_MEMORY_153' not in first_wire
    # Reopen a completed exact operation without another provider call.
    restarted=AutonomousCycleRuntime(journal,content_vault=interpreter.vault)
    assert (await restarted.cycle(operation_id='native-shadow-first',**params)).disposition=='silence'
    assert len(native_calls)==1
    # Consent withdrawal changes the next current view. A fresh native session
    # must not silently restore old feedback via its conversation history.
    journal.append(EventEnvelope(event_type='consolidation.consent_changed',source='hermes.command.memory',
        actor=owner,subject=owner,sensitivity=Sensitivity.PRIVATE,payload={'enabled':False}))
    memories.forget_item(own_memory,actor=owner,request_id='native153-forget')
    assert (await restarted.cycle(operation_id='native-shadow-after-withdrawal',**params)).disposition=='silence'
    assert len(native_calls)==2
    second_wire=json.dumps(provider_requests[-1],ensure_ascii=False)
    assert feedback_marker not in second_wire and own_memory_marker not in second_wire
    assert 'FORBIDDEN_FOREIGN_MEMORY_153' not in second_wire
    assert 'SYNTHETIC_ACTIVE_COMMITMENT_153' in second_wire and 'SYNTHETIC_DISCOVERY_153' in second_wire
    assert before=={name:len(journal.read(event_type=name)) for name in before}
    assert not attempts and len(provider_requests)==3
asyncio.run(shadow())
native_copies=[]
for path in profile.rglob('*'):
    if path.is_file() and any(marker.encode() in path.read_bytes() for marker in (feedback_marker,own_memory_marker)):
        native_copies.append(str(path.relative_to(profile)))
print(json.dumps(dict(native_shadow_calls=len(native_calls),fake_provider_calls=len(provider_requests),
    actual_model_calls=0,sends=0,network_attempts=len(attempts),
    native_profile_retained_feedback_paths=native_copies,
    profile_scope='temporary synthetic; not a production forgetting guarantee')),flush=True)
print('HERMES_ALIVE_NATIVE_SHADOW_SOURCE_BOUNDARY_OK',flush=True)
faulthandler.cancel_dump_traceback_later()
