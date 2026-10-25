"""Installed Core startup -> public discovery -> final share; controlled IO only.

Actual plugin/CLI/hooks/registry/SDK completion admission and encrypted kernel.
HTTP/model/source/URL-safety answers are synthetic, not real quality acceptance.
"""
import argparse
import asyncio
from argparse import Namespace
from contextlib import redirect_stdout
import io
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import threading
from unittest.mock import patch

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
home=a.output/'profile';home.mkdir(mode=0o700)
os.environ['HERMES_HOME']=str(home)
package=Path(__file__).resolve().parents[1];repo=package.parents[1]
sys.path[:0]=[str(a.core.resolve(strict=True)),str(package/'hooks')]
config=dict(model=dict(default='configured-primary',provider='custom:owner'),
    custom_providers=[dict(name='owner',model='configured-primary',base_url='https://provider.invalid/v1',
                          key_env='OWNER_MAIN_KEY',api_mode='chat_completions')],
    agent=dict(reasoning_effort=False),plugins=dict(enabled=['hermes-alive'],entries={'hermes-alive':dict(settings={})}))
(home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
(home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_OWNER_KEY\n',encoding='utf-8')
shutil.copytree(repo,home/'plugins/hermes-alive',ignore=shutil.ignore_patterns('.git','__pycache__'))


async def main():
    import httpx
    from hermes_cli.plugins import get_plugin_manager
    from hermes_cli.config import load_config_readonly
    from tui_gateway.launch_profile_policy import launch_profile_runtime_scope
    from gateway.hooks import HookRegistry
    from hermes_constants import get_hermes_home
    from tools.registry import registry
    from alive_kernel import ExperienceJournal
    url='https://example.invalid/conservation';primary='https://example.invalid/original-protocol';reads=[];requests=[]
    def source_handler(name):
        def handle(args,**kw):
            assert Path(get_hermes_home()).resolve()==home.resolve()
            reads.append(dict(name=name,args=args))
            if name=='web_search':
                assert args==dict(query='public museum methods',limit=3)
                return json.dumps(dict(success=True,data=dict(web=[dict(url=url,title='Conservation method',
                    description='A synthetic public notice describes non-invasive observation.')])) )
            assert args in (dict(urls=[url],char_limit=6000),dict(urls=[primary],char_limit=6000))
            target=args['urls'][0]
            return json.dumps(dict(results=[dict(url=target,title='Conservation method',
                content=('DEEP_READ_EVIDENCE: The museum describes non-invasive observation before intervention. '
                    +'Navigation. '*180+'[Original protocol]('+primary+')' if target==url else
                    'PRIMARY_READ_EVIDENCE: Original protocol describes observing before intervention. '
                    '[Other citation](https://example.invalid/not-authorized-third-hop)'))]))
        return handle
    for name in ('web_search','web_extract'):
        registry.register(name=name,toolset='web',schema=dict(name=name,description='Synthetic controlled source',parameters=dict(type='object')),
            handler=source_handler(name),override=True,scope=str(home))
    def http_response(request):
        def excerpt(e):return e.get('summary_excerpt') or ''.join(p['text'] for p in e.get('summary_passages',[]))
        if not request.url.path.endswith('/chat/completions'):
            return httpx.Response(503,request=request,json={'error':{'message':'synthetic metadata unavailable'}})
        assert request.url.host=='provider.invalid'
        assert request.headers['authorization']=='Bearer SYNTHETIC_OWNER_KEY'
        body=json.loads(request.content);assert not body.get('tools')
        raw=next(m['content'] for m in body['messages'] if m['role']=='user')
        try:data=json.loads(raw)
        except ValueError:data=json.loads(raw.split('\n',1)[1])
        if isinstance(data,list):
            stage='select';value=dict(candidate_id=next(c['candidate_id'] for c in data if c['candidate_id'].startswith('opportunity-candidate:')),rationale='Synthetic contribution')
        elif data.get('method')=='cited-public-followup-v2':
            stage='followup';assert 'user_context' not in data
            assert primary in data['sources'][0]['excerpt']
            value=dict(read_targets=[dict(source_ref=data['sources'][0]['source_ref'],citation_ref=next(
                c['citation_ref'] for c in data['sources'][0]['citations'] if c['url']==primary))],
                reason='Read the actual cited original protocol before interpreting commentary.')
        elif 'sources' in data:
            stage='reading';value=dict(source_refs=[data['sources'][0]['source_ref']],question='INTERNAL_RESEARCH: What changed?',
                value_hypothesis='A possible interesting conservation discovery, not an owner request.')
        elif 'opportunities' in data:
            stage='generate';assert data['tentative_discovery_tasks']
            assert any('PRIMARY_READ_EVIDENCE' in excerpt(e) for e in data['opportunities'])
            e=next(e for e in data['opportunities'] if 'DEEP_READ_EVIDENCE' in excerpt(e))
            value=dict(candidates=[dict(agenda_item_id=e['agenda_item_id'],kind='share',topic='conservation',
                communication_plan=dict(version=3,recipient_goal='INTERNAL_GOAL',speech_act='share',contents=[],behavior_constraints=[]),
                dimensions={n:dict(value=.1 if n in ('risk','urgency','interruption_cost') else .9,reason='Synthetic judgment')
                    for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')})])
            assert 'reading_assessments' in body['messages'][0]['content']
            value['reading_assessments']=[dict(item_id=data['tentative_discovery_tasks'][0]['item_id'],status='partial',
                findings=[dict(observation_event_id=e['observation_event_id'],passage_id=e['summary_passages'][0]['passage_id'],
                    interpretation='The notice reports observation, not independent validation.')],
                open_questions=['What independently verifies this method?'])]
        elif 'expression_binding' in data:
            stage='final';assert data['expression_binding']['assessment_mode']=='discovery-source-and-value-v3'
            assert 'communication_plan' not in data['candidate']
            value=dict(verdict='supported',unsupported_claims=[],uncertainties=[],reason='Synthetic finding, not satisfaction.')
        elif 'meaning' in data and 'candidate' in data:
            assert 'source_context' not in data
            assert 'only the explicitly required meaning boundaries' in body['messages'][0]['content']
            assert 'PRIMARY_READ_EVIDENCE' not in raw and 'DEEP_READ_EVIDENCE' not in raw
            stage='semantic';value=dict(atom_reviews=[dict(atom_id=x['atom_id'],preserved=True,risks=[]) for x in data['meaning']['atoms']],
                added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True)
        elif 'meaning' in data:
            stage='author';assert data['expression_context']['method']=='discovery-source-authoring-v3'
            assert 'PRIMARY_READ_EVIDENCE' in raw and 'DEEP_READ_EVIDENCE' in raw
            assert 'INTERNAL_GOAL' not in raw
            assessment=data['expression_context']['reading_assessment']
            assert assessment['entries'][0]['status']=='partial' and 'INTERNAL_RESEARCH' in assessment['entries'][0]['question']
            assert not assessment['source_truth_proven'] and not assessment['agenda_completion_proven']
            value='The museum describes observing before intervention: [conservation method]('+url+').'
        else:raise AssertionError('Unexpected model stage '+str(list(data)))
        requests.append(dict(stage=stage,model=body['model']))
        result=dict(id='synthetic-discovery',object='chat.completion',created=0,model=body['model'],
            choices=[dict(index=0,message=dict(role='assistant',content=value if isinstance(value,str) else json.dumps(value)),finish_reason='stop')],
            usage=dict(prompt_tokens=50,completion_tokens=30,total_tokens=80))
        return httpx.Response(200,request=request,json=result)
    async def send(client,request,*args,**kw):return http_response(request)
    with patch.object(httpx.AsyncClient,'send',send),patch.object(httpx.Client,'send',lambda client,request,*args,**kw:http_response(request)):
        with launch_profile_runtime_scope(home):
            manager=get_plugin_manager();manager.discover_and_load()
            module=manager._plugins['hermes-alive'].module
            args=Namespace(alive_action='kernel-setup',subject=None,user_id='synthetic-discovery-user',confirm_model_calls=True,
                public_query=['public museum methods'],confirm_public_reads=False,confirm_cited_reads=True,
                max_cycles=1,interval_seconds=0,model=None)
            before=(home/'config.yaml').read_bytes()
            with redirect_stdout(io.StringIO()):assert module.alive_command(args)==2
            assert (home/'config.yaml').read_bytes()==before and not reads and not requests
            args.confirm_public_reads=True
            with redirect_stdout(io.StringIO()):assert module.alive_command(args)==0
            settings=module._gateway_host_binding.context.get_config('kernel_shadow')
            assert settings['public_discovery']['queries']==['public museum methods']
            assert settings['public_discovery']['follow_citations'] is True
            with redirect_stdout(io.StringIO()):assert module.alive_command(Namespace(alive_action='install-runtime',engine='kernel-shadow'))==0
            # Controlled URL answers only. Production uses Core's real URL/DNS
            # checks; this network-none fixture is not URL-security qualification.
            bridge=importlib.import_module(module.__name__+'.tool_receipt_bridge')
            assembly=bridge._kernel_module('core_shadow_assembly')
            tools_class=importlib.import_module(assembly.__package__+'.core_discovery_tools').CoreDiscoveryTools
            context_class=importlib.import_module(assembly.__package__+'.core_context_read').CoreContextRead
            context_reads=[]
            original_invoke=context_class.invoke
            async def observed_invoke(self,operation,*,read_binding):
                def observed_operation():
                    assert threading.current_thread() is not threading.main_thread()
                    assert Path(get_hermes_home()).resolve()==home.resolve()
                    context_reads.append(str(get_hermes_home()))
                    return operation()
                return await original_invoke(self,observed_operation,read_binding=read_binding)
            async def allowed(self,target):return target in (url,primary)
            with patch.object(tools_class,'allow_url',allowed),patch.object(context_class,'invoke',observed_invoke):
                hooks=HookRegistry();hooks.discover_and_load()
                assert (await hooks.emit_collect('gateway:startup',{}))[0]['status']=='started'
                binding=module._gateway_host_binding
                result=await binding.task
                assert result['completed_cycles']==1 and result['exit_reason']=='budget',result
            root=home/'plugin-data/hermes-alive/runtime/kernel'
            journal=ExperienceJournal(root/'experience.sqlite3')
            assert len(journal.read(event_type='discovery.reading_choice_completed'))==2
            assert len(journal.read(event_type='message.model_candidate'))==1
            assert len(journal.read(event_type='autonomous.host.closed'))==1
            assert not journal.read(event_type='action.attempted')
            assert [r['stage'] for r in requests]==['reading','followup','generate','select','author','semantic','final'],requests
            assert [r['name'] for r in reads]==['web_search','web_extract','web_extract']
            assert reads[-1]['args']['urls']==[primary]
            assert not binding.native.pending
            assert context_reads,'installed cognition never used Core-owned context reads'
            context_capability=binding.native.context_reads
            assert manager.unload('hermes-alive') is True
            await asyncio.sleep(0)
            assert context_capability._closed and not context_capability.pending
            before=journal.path.read_bytes()
            with redirect_stdout(io.StringIO()):
                assert module.alive_command(Namespace(alive_action='uninstall-runtime'))==0
                assert module.alive_command(Namespace(alive_action='install-runtime',engine=None))==0
            assert journal.path.read_bytes()==before
            retained=load_config_readonly()['plugins']['entries']['hermes-alive']['settings']['kernel_shadow']
            assert retained==settings
    report=dict(installed_startup_to_final_expression=True,separate_public_consent_required=True,
        core_profile_context_thread_reads=len(context_reads),unload_retires_context_reads=True,
        reinstall_preserves_public_consent_and_history=True,
        controlled_registry_dispatch=reads,controlled_model_stages=requests,physical_sends=0,
        actual_model_inference=False,url_safety_answers_synthetic=True,quality_rounds=0)
    (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('HERMES_ALIVE_CORE_DISCOVERY_CYCLE_OK '+json.dumps(report))
asyncio.run(main())
