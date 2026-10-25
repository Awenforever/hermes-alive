"""Persisted setup -> real Core plugin/hook/model API, with controlled HTTP."""
import argparse
import asyncio
import copy
from argparse import Namespace
from contextlib import redirect_stdout
import io
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
home=a.output/'profile';home.mkdir(mode=0o700)
os.environ['HERMES_HOME']=str(home)
package=Path(__file__).resolve().parents[1];repo=package.parents[1]
sys.path[:0]=[str(a.core.resolve(strict=True)),str(package/'hooks')]
setup=dict(enabled=True,consent='model_calls_no_delivery',subject='user:synthetic-auto',max_cycles=2,interval_seconds=0,model=None)
config=dict(model=dict(default='configured-primary',provider='custom:owner'),
    custom_providers=[dict(name='owner',model='configured-primary',base_url='https://provider.invalid/v1',
        key_env='OWNER_MAIN_KEY',api_mode='chat_completions'),
        dict(name='backup',model='configured-backup',base_url='https://backup.invalid/v1',key_env='BACKUP_KEY',api_mode='chat_completions')],
    fallback_providers=[dict(provider='custom:backup',model='configured-backup',key_env='BACKUP_KEY')],
    agent=dict(reasoning_effort=False),plugins=dict(enabled=['hermes-alive'],entries={
        'hermes-alive':dict(settings={})}))
def save():
    (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
save();(home/'.env').write_text('OWNER_MAIN_KEY=PRIVATE_MAIN_KEY\nBACKUP_KEY=PRIVATE_BACKUP_KEY\n',encoding='utf-8')
shutil.copytree(repo,home/'plugins/hermes-alive',ignore=shutil.ignore_patterns('.git','__pycache__'))

async def main():
    import httpx
    from hermes_cli.plugins import get_plugin_manager
    from tui_gateway.launch_profile_policy import launch_profile_runtime_scope
    from gateway.hooks import HookRegistry
    from gateway.run import _profile_runtime_scope
    from hermes_constants import get_hermes_home
    from alive_kernel import ExperienceJournal,DiscoveryCandidate,DiscoveryOpportunityIngestor,AutonomyPolicyProjection,PolicyContext
    from alive_kernel.content_vault import ContentVault
    from alive_kernel.native_core_scope import core_profile_cycle_scope
    from alive_kernel.native_worker_protocol import NativeWorkerError
    from alive_kernel.privacy import LocalIdentityProtector
    requests=[];deny_primary=[0];held=asyncio.Event();release=asyncio.Event()
    def response(request):
        if not request.url.path.endswith('/chat/completions'):
            return httpx.Response(503,request=request,json={'error':{'message':'synthetic metadata unavailable'}})
        body=json.loads(request.content);model=body['model']
        secondary=Path(get_hermes_home()).resolve()!=home.resolve()
        assert request.url.host in (('secondary.invalid',) if secondary else ('provider.invalid','backup.invalid'))
        expected=('PRIVATE_SECONDARY_KEY' if secondary else
                  'PRIVATE_MAIN_KEY' if request.url.host=='provider.invalid' else 'PRIVATE_BACKUP_KEY')
        assert request.headers['authorization']=='Bearer '+expected
        assert not body.get('tools') and not body.get('stream')
        requests.append(dict(model=model,endpoint=request.url.host))
        if deny_primary[0] and request.url.host=='provider.invalid':
            return httpx.Response(deny_primary[0],request=request,json={'error':{'message':'synthetic denied','type':'permission_error'}})
        user=next(item['content'] for item in body['messages'] if item['role']=='user')
        try:data=json.loads(user)
        except ValueError:data={}
        content=json.dumps(dict(candidates=[],abstentions=[dict(agenda_item_id=item['agenda_item_id'],
            reason='Synthetic deliberate silence, not utility proof.') for item in data.get('opportunities',[])]))
        choice=dict(index=0,message=dict(role='assistant',content=content),finish_reason='stop')
        if model=='length-model':choice['finish_reason']='length'
        if model=='filter-model':choice['finish_reason']='content_filter'
        if model=='missing-finish-model':choice.pop('finish_reason')
        doc=dict(id='synthetic-auto',object='chat.completion',created=0,model=model,choices=[choice],
            usage=dict(prompt_tokens=50,completion_tokens=20,total_tokens=70))
        if model=='synthesized-stop-model':
            doc.update(choices=None,output_text=content)
        return httpx.Response(200,request=request,json=doc)
    original_async=httpx.AsyncClient.send;original_sync=httpx.Client.send
    async def send(client,request,*args,**kwargs):
        if request.url.path.endswith('/chat/completions') and json.loads(request.content)['model']=='hold-model':
            held.set();await release.wait()
        return response(request)
    httpx.AsyncClient.send=send
    httpx.Client.send=lambda client,request,*args,**kwargs:response(request)
    try:
        root=home/'plugin-data/hermes-alive/runtime/kernel'
        setup['subject']=LocalIdentityProtector(root/'identity.key').pseudonym('user','synthetic-authorized-user')
        journal=ExperienceJournal(root/'experience.sqlite3')
        vault=ContentVault(root/'content-vault',backup_root=root/'content-backups')
        DiscoveryOpportunityIngestor(journal,content_vault=vault).ingest(DiscoveryCandidate(source='synthetic',
            title='Synthetic public source',summary='A synthetic public fact, no private chat.',
            url='https://example.invalid/auto',observed_at=datetime.now(timezone.utc)),subject=setup['subject'])
        with launch_profile_runtime_scope(home):
            manager=get_plugin_manager();manager.discover_and_load()
            module=manager._plugins['hermes-alive'].module
            args=Namespace(alive_action='kernel-setup',subject=None,user_id='synthetic-authorized-user',confirm_model_calls=False,
                max_cycles=2,interval_seconds=0,model=None)
            with redirect_stdout(io.StringIO()):assert module.alive_command(args)==2
            assert 'kernel_shadow' not in json.loads((home/'config.yaml').read_text())['plugins']['entries']['hermes-alive']['settings']
            args.confirm_model_calls=True
            with redirect_stdout(io.StringIO()):assert module.alive_command(args)==0
            stored=module._gateway_host_binding.context.get_config('kernel_shadow')
            assert stored['subject']==setup['subject'] and 'synthetic-authorized-user' not in json.dumps(stored)
            config['plugins']['entries']['hermes-alive']['settings']['kernel_shadow']=setup
            with redirect_stdout(io.StringIO()):
                assert module.alive_command(Namespace(alive_action='install-runtime',engine='kernel-shadow'))==0
                assert module.alive_command(Namespace(alive_action='install-runtime',engine=None))==0
            manifest=home/'plugin-data/hermes-alive/runtime/install/manifest.json'
            assert json.loads(manifest.read_text())['engine']=='kernel-shadow'
            registry=HookRegistry();registry.discover_and_load()
            assert (await registry.emit_collect('gateway:startup',{}))[0]['status']=='started'
            binding=module._gateway_host_binding
            assert binding.arguments['build_parameters']()['expression_parameters']['model_timeout_seconds']==600
            from agent.auxiliary_task_config import _get_auxiliary_task_config
            assert _get_auxiliary_task_config('hermes_alive_kernel')['timeout']==180
            assert (await binding.task)['completed_cycles']==2
            assert len(requests)==1 and requests[0]['model']=='configured-primary'
            assert manager.unload('hermes-alive') is True
            await asyncio.sleep(0)
            before=journal.path.read_bytes()
            with redirect_stdout(io.StringIO()):
                assert module.alive_command(Namespace(alive_action='uninstall-runtime'))==0
                assert module.alive_command(Namespace(alive_action='install-runtime',engine=None))==0
            assert journal.path.read_bytes()==before
            assert json.loads(manifest.read_text())['engine']=='kernel-shadow'
            manager.discover_and_load(force=True)
            module2=manager._plugins['hermes-alive'].module
            assert module2 is not module
            assert (await registry.emit_collect('gateway:startup',{}))[0]['status']=='started'
            assert (await module2._gateway_host_binding.task)['completed_cycles']==2
            assert len(requests)==1  # Persistent reconsideration survives module reload.
            ctx=module2._gateway_host_binding.context
            from importlib import import_module
            # The runtime factory uses the content-addressed kernel namespace.
            namespace=type(module2._gateway_host_binding.native).__module__.rsplit('.',1)[0]
            Caller=import_module(namespace+'.core_plugin_model_call').CorePluginModelCaller
            caller=Caller(ctx,read_binding=lambda:'synthetic-current-binding')
            params=dict(task='synthetic-protocol',messages=[dict(role='user',content='{}')],temperature=.1,max_tokens=128)
            async with core_profile_cycle_scope(home):
                try:await caller(model='length-model',**params)
                except PermissionError:pass
                else:raise AssertionError('Core override gate bypassed')
                assert len(requests)==1
            config['plugins']['entries']['hermes-alive']['llm']={'allow_model_override':True};save()
            async with core_profile_cycle_scope(home):
                for model in ('length-model','filter-model','missing-finish-model','synthesized-stop-model'):
                    try:await caller(model=model,**params)
                    except NativeWorkerError:pass
                    except ValueError as error:
                        # Namespace-local NativeWorkerError is a ValueError too.
                        assert type(error).__name__=='NativeWorkerError'
                    else:raise AssertionError('unqualified completion accepted: '+model)
                live=Caller(ctx,read_binding=lambda:'synthetic-current-binding',
                    refresh_task=module2._gateway_host_binding.native._caller.refresh_task)
                active=asyncio.create_task(live(model='hold-model',**params))
                try:
                    await asyncio.wait_for(held.wait(),timeout=15)
                    config['plugins']['entries']['hermes-alive']['settings']['kernel_shadow']['enabled']=False;save()
                    release.set()
                    try:await active
                    except ValueError as error:assert type(error).__name__=='NativeWorkerError'
                    else:raise AssertionError('result accepted after shadow consent revoked')
                    assert not live.pending
                    try:await live(model=None,**params)
                    except ValueError:pass
                    else:raise AssertionError('new request spent after shadow consent revoked')
                finally:
                    if not active.done():active.cancel()
                    await asyncio.gather(active,return_exceptions=True)
                config['plugins']['entries']['hermes-alive']['settings']['kernel_shadow']['enabled']=True;save()
                deny_primary[0]=403
                from agent.auxiliary_task_config import _get_auxiliary_task_config
                from hermes_cli.plugins import get_plugin_auxiliary_tasks
                effective=_get_auxiliary_task_config(caller.task_key)
                diagnostic=dict(task=caller.task_key,effective=effective,
                    registrations=get_plugin_auxiliary_tasks(),requests=requests)
                (a.output/'synthetic-fallback-diagnostic.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf-8')
                route={}
                try:await caller(model=None,route_info=route,**params)
                except Exception as error:
                    assert getattr(error,'status_code',None)==403
                else:raise AssertionError('Core unexpectedly changed its generic403 policy')
                assert requests[-1]['endpoint']=='provider.invalid'
                deny_primary[0]=401
                result=await caller(model=None,route_info=route,**params)
                assert result.model=='configured-backup' and route['model']=='configured-backup'
            assert manager.unload('hermes-alive') is True
            await asyncio.sleep(0)
        # Same task/provider/model labels in another profile must not reuse the
        # launch account's cached endpoint, credentials or consent.
        beta=home/'profiles/beta';beta.mkdir(parents=True)
        beta_config=copy.deepcopy(config)
        beta_config['custom_providers']=[{**config['custom_providers'][0],'base_url':'https://secondary.invalid/v1'}]
        beta_config['fallback_providers']=[]
        beta_setup=beta_config['plugins']['entries']['hermes-alive']['settings']['kernel_shadow']
        beta_setup.update(subject='user:synthetic-secondary',max_cycles=1)
        (beta/'config.yaml').write_text(json.dumps(beta_config),encoding='utf-8')
        (beta/'.env').write_text('OWNER_MAIN_KEY=PRIVATE_SECONDARY_KEY\n',encoding='utf-8')
        shutil.copytree(repo,beta/'plugins/hermes-alive',ignore=shutil.ignore_patterns('.git','__pycache__'))
        beta_root=beta/'plugin-data/hermes-alive/runtime/kernel'
        beta_journal=ExperienceJournal(beta_root/'experience.sqlite3')
        beta_vault=ContentVault(beta_root/'content-vault',backup_root=beta_root/'content-backups')
        DiscoveryOpportunityIngestor(beta_journal,content_vault=beta_vault).ingest(DiscoveryCandidate(source='synthetic',
            title='Another synthetic public source',summary='Synthetic independent account scope.',
            url='https://example.invalid/beta',observed_at=datetime.now(timezone.utc)),subject=beta_setup['subject'])
        before_beta=len(requests)
        with _profile_runtime_scope(beta):
            beta_manager=get_plugin_manager();beta_manager.discover_and_load()
            beta_module=beta_manager._plugins['hermes-alive'].module
            with redirect_stdout(io.StringIO()):
                assert beta_module.alive_command(Namespace(alive_action='install-runtime',engine='kernel-shadow'))==0
            beta_hooks=HookRegistry();beta_hooks.discover_and_load()
            assert (await beta_hooks.emit_collect('gateway:startup',{}))[0]['status']=='started'
            assert (await beta_module._gateway_host_binding.task)['completed_cycles']==1
            assert len(requests)==before_beta+1 and requests[-1]['endpoint']=='secondary.invalid'
            assert beta_manager.unload('hermes-alive') is True
            await asyncio.sleep(0)
        report=dict(config_driven_host_assembly=True,reload_without_manual_attachment=True,
            core_model_auth_401_fallback=True,generic403_fallback_qualified=False,
            default_override_denied=True,incomplete_and_synthesized_stop_rejected=True,
            actual_model_inference=False,physical_sends=0,explicit_installer_selection_proven=True,
            unconfirmed_setup_no_write=True,uninstall_reinstall_preserves_state=True,
            owner_identity_pseudonymized=True,
            inflight_revocation_rejected=True,
            distinct_profile_credentials_and_endpoint=True,
            all_api_modes_qualified=False,controlled_requests=requests)
        (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('HERMES_ALIVE_CORE_AUTO_ASSEMBLY_OK '+json.dumps(report))
    finally:
        httpx.AsyncClient.send=original_async;httpx.Client.send=original_sync
asyncio.run(main())
