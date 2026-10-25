#!/usr/bin/env python3
"""Composed isolated cycles; synthetic models are wiring, not utility proof."""
import argparse
import asyncio
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import AutonomyPolicyProjection,ExperienceJournal,PolicyContext,Sensitivity
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
from alive_kernel.transport_publisher_bridge import QualifiedReceiptPublisher
from alive_kernel_testkit import install_terminal_route
from run_alive_kernel_expression_runtime import scenario
from run_transport_publisher_bridge import adapter_for


async def test(root,enhance,core):
    journal,parameters,_ = await scenario(root/'kernel','share',return_ready=True)
    runtime = AutonomousCycleRuntime(journal)
    owner = 'user:test'
    policies = AutonomyPolicyProjection(journal)
    assert policies.apply(policies.append_update(subject=owner,actor=owner,expected_revision=0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='enable')).outcome=='recorded'
    route = {'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None}
    route_id = install_terminal_route(journal,subject=owner,content_vault=runtime.preparation.vault,route_document=route)
    delegation = ActionDelegationStore(journal).grant(subject=owner,actor=owner,
        policy_event_id=policies.current(owner).event_id,route_binding_id=route_id,action_kinds=('share',),
        maximum_sensitivity=Sensitivity.PRIVATE,expires_at=datetime.now(timezone.utc)+timedelta(hours=1),
        operation_id='delegation',allow_natural_expression=True)
    home = root/'profile'
    home.mkdir()
    os.environ['HERMES_HOME'] = str(home)
    sys.path.insert(0,str(enhance))
    from hermes_wechat_enhance.v021_bubble_footer import patch_adapter
    spec = importlib.util.spec_from_file_location('cycle_fixtures',enhance/'scripts/test-v021-bubble-footer.py')
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    adapter = adapter_for(fixtures,core)
    assert patch_adapter(adapter)
    publisher = QualifiedReceiptPublisher(adapter,hashlib.sha256((enhance/'hermes_wechat_enhance/v021_bubble_footer.py').read_bytes()).hexdigest(),'synthetic',home,True)
    expression = {key:value for key,value in parameters.items() if key not in ('subject','operation_id','policy_context')}
    authorization = {'authorization_operation_id':'authorize-cycle','route_binding_id':route_id,
                     'delegation_event_id':delegation.event.event_id}
    send = dict(publisher=publisher,clearance=Sensitivity.PRIVATE,profile_id='synthetic',hermes_home=home,
        resolve_target=lambda p,t:(t,None,None),extract_media=lambda text:([],text),observe_profile_home=lambda:home)
    def resolve(record): return publisher,route
    args = dict(subject=owner,operation_id='cycle-one',expression_parameters=expression,resolve_binding=resolve,
        execute=True,authorization_parameters=authorization,send_parameters=send,worker_id='cycle-worker')
    adapter.fail_next = True
    first = await runtime.cycle(**args)
    assert first.disposition=='submitted' and not first.external_delivery_proven and not adapter.sent
    assert journal.read(event_type='transport.publisher.observed')
    async def forbidden(**kwargs): raise AssertionError('completed cycle repeated model spend')
    replay_args = {**args,'expression_parameters':{**expression,'call':forbidden}}
    reopened = AutonomousCycleRuntime(ExperienceJournal(journal.path))
    replay = await reopened.cycle(**replay_args)
    assert replay.disposition=='attempt_unavailable' and not adapter.sent
    assert len(journal.read(event_type='dispatch.started'))==1
    before = len(journal.read(event_type='action.attempt'))
    shadow = await reopened.cycle(subject=owner,operation_id='shadow-one',expression_parameters=expression,resolve_binding=resolve)
    assert shadow.disposition=='shadow_selected' and shadow.prepared is None and shadow.submission is None
    assert len(journal.read(event_type='action.attempt'))==before
    async def silent(**kwargs):
        assert kwargs['task']=='alive_opportunity_candidates'
        return SimpleNamespace(model='synthetic/silence',choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'candidates':[]})))])
    silence = await reopened.cycle(subject=owner,operation_id='silence-one',
        expression_parameters={**expression,'call':silent},resolve_binding=resolve)
    assert silence.disposition=='silence' and len(journal.read(event_type='action.attempt'))==before
    host = AutonomousHostRuntime(reopened,subject=owner,configuration_id='synthetic-shadow')
    hosted = await host.run(build_parameters=lambda:{'expression_parameters':{**expression,'call':silent},
        'resolve_binding':resolve},stop=asyncio.Event(),max_cycles=2,interval_seconds=0)
    assert hosted['completed_cycles']==2 and hosted['exit_reason']=='budget'
    assert len(journal.read(event_type='autonomous.host.closed'))==2
    assert all(record.event.payload['disposition']=='silence' for record in journal.read(event_type='autonomous.host.closed'))
    assert len(journal.read(event_type='action.attempt'))==before
    current = policies.current(owner)
    assert policies.apply(policies.append_update(subject=owner,actor=owner,expected_revision=current.revision,
        enabled=False,context=PolicyContext(can_interrupt=False),operation_id='pause')).outcome=='recorded'
    paused = await reopened.cycle(subject=owner,operation_id='paused-one',
        expression_parameters={**expression,'call':forbidden},resolve_binding=resolve)
    assert paused.disposition=='paused' and paused.reconciliation['withdrawal_requests']==1
    assert adapter._hermes_transport_receipts_v1.count(adapter._account_id,'peer')==0
    assert not adapter.sent and len(journal.read(event_type='dispatch.started'))==1
    assert not journal.read(event_type='outcome.recorded')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--enhance-root',type=Path,required=True)
    parser.add_argument('--hermes-root',type=Path)
    args=parser.parse_args()
    if args.hermes_root: sys.path.insert(0,str(args.hermes_root.resolve()))
    with tempfile.TemporaryDirectory(prefix='alive-cycle-runtime-') as folder:
        asyncio.run(test(Path(folder),args.enhance_root.resolve(),args.hermes_root))
    print('HERMES_ALIVE_AUTONOMOUS_CYCLE_RUNTIME_OK')
