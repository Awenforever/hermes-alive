#!/usr/bin/env python3
"""Real journal/authorization/outbox/cycle, synthetic models and transport only."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument('--core', type=Path)
args = parser.parse_args()
if args.core:
    sys.path.insert(0, str(args.core.resolve()))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import AutonomyPolicyProjection, EventEnvelope, ExperienceJournal, PolicyContext, ReceiptLevel, Sensitivity
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.dispatch_outbox import DispatchOutboxError
from alive_kernel.event_store import EventConflictError
from run_alive_kernel_expression_runtime import scenario


if args.core:
    from gateway.config import Platform, PlatformConfig
    from gateway.platforms.base import BasePlatformAdapter, SendResult
    class AdapterBase(BasePlatformAdapter):
        def __init__(self):
            super().__init__(PlatformConfig(), Platform.TELEGRAM)
            self._running = True
        async def connect(self, *, is_reconnect=False):
            self._running = True
            return True
        async def disconnect(self):
            self._running = False
        async def get_chat_info(self, chat_id):
            return {'name':'synthetic','type':'dm'}
else:
    class AdapterBase:
        def __init__(self):
            self.is_connected = True
            self.platform = SimpleNamespace(value='telegram')
    SendResult = SimpleNamespace


async def test(root, mode):
    journal, parameters, expressed = await scenario(root/'kernel', 'share', return_ready=True)
    runtime = AutonomousCycleRuntime(journal)
    owner = 'user:test'
    policies = AutonomyPolicyProjection(journal)
    policies.apply(policies.append_update(subject=owner,actor=owner,expected_revision=0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='enable'))
    route = {'platform':'telegram','profile':'synthetic','chat_id':'123','thread_id':'7'}
    host = runtime.preparation.authorizer.host
    snapshot = host.observe_snapshot(snapshot_id='core-standard-send',hermes_version='0.22.5',
        plugin_api_version=1,capabilities={'hermes.channel.send':{
            'interface':'core.adapter.send','available':True,'public_api':True,
            'receipt_level':ReceiptLevel.REQUEST_ACCEPTED.value}})
    binding_id = 'user-selected-channel'
    authority = journal.append(EventEnvelope(event_type='conversation.inbound',source='test.synthetic',
        actor=owner,subject=owner,payload={'authorizes_route_binding_id':binding_id,
            'authorizes_host_snapshot_event_id':snapshot.event_id,
            'authorizes_receipt_requirement':ReceiptLevel.REQUEST_ACCEPTED.value}))
    host.bind_route(binding_id=binding_id,subject=owner,capability='hermes.channel.send',
        snapshot_event_id=snapshot.event_id,route=route,authority_event_id=authority.event.event_id,
        receipt_requirement=ReceiptLevel.REQUEST_ACCEPTED)
    delegation = ActionDelegationStore(journal).grant(subject=owner,actor=owner,
        policy_event_id=policies.current(owner).event_id,route_binding_id=binding_id,
        action_kinds=('share',),maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=datetime.now(timezone.utc)+timedelta(hours=1),operation_id='delegate',
        allow_natural_expression=True,minimum_interval_seconds=0 if mode=='success' else 3600)
    home = root/'profile'; home.mkdir()
    received = []
    logical_offset = [timedelta(0)]
    clock = lambda: datetime.now(timezone.utc)+logical_offset[0]
    returned = (SendResult(success=False, message_id=None, error='PRIVATE_ERROR_SENTINEL') if mode=='false'
        else SimpleNamespace(success=1, message_id=None, raw_response='PRIVATE_ERROR_SENTINEL') if mode=='unknown'
        else SendResult(success=True,message_id='PRIVATE_OPAQUE_ID_SENTINEL'))
    class Adapter(AdapterBase):
        async def send(self, chat_id, content, reply_to=None, metadata=None):
            received.append((chat_id,content,dict(metadata)))
            if mode=='cancel': raise asyncio.CancelledError()
            if mode=='exception': raise TimeoutError('possible external effect')
            if mode=='long':
                logical_offset[0] += timedelta(seconds=60)
                runtime.outbox.reconcile(now=clock(),recovering=True)
            return returned
    adapter = Adapter()
    profile_changed = [False]
    def resolve_channel(requested):
        assert dict(requested) == route
        try: requested['chat_id']='foreign'
        except TypeError: pass
        else: raise AssertionError('host resolver received a mutable execution route')
        if mode=='missing': return None, {}
        if mode=='disconnected':
            if args.core: adapter._running = False
            else: adapter.is_connected = False
        if mode=='revoked': host.revoke_route(binding_id)
        if mode=='wrong-platform': adapter.platform = SimpleNamespace(value='feishu')
        if mode=='wrong-profile': profile_changed[0] = True
        metadata = {'thread_id':'7','slack_team_id':'synthetic-workspace',
                    'hermes_profile':'synthetic-host-scope','future_host_field':'retained'}
        if mode=='wrong-thread': metadata['thread_id'] = 'other-thread'
        if mode=='forged-model': metadata['model_name'] = 'wrong-model'
        return adapter, metadata
    if mode=='write-failure':
        from alive_kernel.dispatch_outbox import DispatchOutbox
        original_record = DispatchOutbox.record_adapter_observation
        def fail_record(*_,**__): raise OSError('synthetic journal failure after effect')
        DispatchOutbox.record_adapter_observation = fail_record
    expression = {k:v for k,v in parameters.items() if k not in ('subject','operation_id','policy_context')}
    cycle_args = dict(subject=owner,operation_id='one',expression_parameters=expression,
        resolve_binding=lambda _: (_ for _ in ()).throw(AssertionError('no Enhance binding expected')),
        execute=True,channel_execution='standard',worker_id='standard-worker',
        authorization_parameters={'authorization_operation_id':'authorize','route_binding_id':binding_id,
            'delegation_event_id':delegation.event.event_id},
        send_parameters=dict(resolve_channel=resolve_channel,clearance=Sensitivity.PRIVATE,
            profile_id='synthetic',hermes_home=home,resolve_target=lambda p,t:('123','7',None),
            extract_media=lambda text:([],text),observe_profile_home=lambda:root if profile_changed[0] else home,
            clock=clock))
    successful = mode in ('success','false','unknown','long')
    try:
        result = await runtime.cycle(**cycle_args)
    except (ValueError,TimeoutError,OSError,asyncio.CancelledError):
        assert not successful, mode
    else:
        assert successful and result.disposition=='submitted' and not result.external_delivery_proven
        assert result.submission.adapter_result is returned
        observation = result.submission.observation
        assert observation.event.event_type == 'transport.adapter.observed'
        assert observation.event.payload['report_kind'] == {
            'false':'error_reported','unknown':'unknown'}.get(mode,'success_reported')
        assert not observation.event.payload['external_delivery_proven']
        assert not observation.event.payload['canonical_quote_target_proven']
        assert runtime.outbox.record_adapter_observation(result.submission.execution,
            result=returned,now=clock()).event.event_id == observation.event.event_id
        try:
            runtime.outbox.record_adapter_observation(replace(result.submission.execution,
                route={**route,'chat_id':'foreign'}),result=returned,now=clock())
        except DispatchOutboxError: pass
        else: raise AssertionError('adapter report accepted a foreign launch route')
        try:
            runtime.outbox.acknowledge(result.submission.execution.lease,
                result_event_id=observation.event.event_id,now=clock())
        except DispatchOutboxError: pass
        else: raise AssertionError('normal adapter return became terminal delivery')
        try:
            runtime.outbox.record_adapter_observation(result.submission.execution,
                result=SimpleNamespace(success=not (mode!='false'),message_id='other'),now=clock())
        except EventConflictError: pass
        else: raise AssertionError('normal return evidence overwritten')
    finally:
        if mode=='write-failure': DispatchOutbox.record_adapter_observation = original_record
    should_send = mode in ('success','false','unknown','long','cancel','exception','write-failure')
    assert len(received) == int(should_send), (mode,received)
    if received:
        chat,body,metadata = received[0]
        assert chat=='123' and body==expressed.text
        assert metadata['thread_id']=='7' and metadata['_interim_send'] is True
        assert metadata['slack_team_id']=='synthetic-workspace' and metadata['future_host_field']=='retained'
        assert 'renderer' in metadata['model_name'] and metadata['model_name']!='hermes'
    assert len(journal.read(event_type='dispatch.started')) == 1
    assert not journal.read(event_type='transport.publisher.bound')
    assert not journal.read(event_type='delivery.succeeded') and not journal.read(event_type='outcome.recorded')
    if mode != 'revoked':
        async def forbidden(**_): raise AssertionError('recovery repeated inference')
        reopened = AutonomousCycleRuntime(ExperienceJournal(journal.path))
        replay = await reopened.cycle(**{**cycle_args,'expression_parameters':{**expression,'call':forbidden}})
        assert replay.disposition=='attempt_unavailable' and len(received)==int(should_send)
    raw = journal.path.read_bytes()
    assert b'PRIVATE_ERROR_SENTINEL' not in raw and b'PRIVATE_OPAQUE_ID_SENTINEL' not in raw
    if mode=='success':
        # A consumed, unacknowledged standard send is never replayed, but must
        # not globally block a distinct authorized intent after process reopen.
        _, next_parameters, next_expression = await scenario(root/'kernel','share',return_ready=True,
            operation_id='two',source_url='https://example.invalid/observatory',
            source_summary='Public observatory open night, details unverified.')
        second_expression={k:v for k,v in next_parameters.items()
                           if k not in ('subject','operation_id','policy_context')}
        second_args={**cycle_args,'operation_id':'two','expression_parameters':second_expression,
            'authorization_parameters':{**cycle_args['authorization_parameters'],
                                        'authorization_operation_id':'authorize-two'}}
        second=await reopened.cycle(**second_args)
        assert second.disposition=='submitted' and len(received)==2
        assert received[1][1]==next_expression.text and received[1][1]!=received[0][1]
        assert len(journal.read(event_type='dispatch.started'))==2
        cold=AutonomousCycleRuntime(ExperienceJournal(journal.path))
        for original in (cycle_args,second_args):
            replay=await cold.cycle(**{**original,'expression_parameters':{
                **original['expression_parameters'],'call':forbidden}})
            if replay.disposition=='not_authorized':
                # Slow filesystems may outlive the original permit before
                # replay. Expiry must refuse even before the consumed outbox.
                assert replay.prepared.authorization.reasons==('permit_expired',)
            else:
                assert replay.disposition=='attempt_unavailable',repr(replay)
            assert len(received)==2 and len(journal.read(event_type='dispatch.started'))==2
        policies.apply(policies.append_update(subject=owner,actor=owner,
            expected_revision=policies.current(owner).revision,enabled=False,
            context=PolicyContext(can_interrupt=True),operation_id='pause-after-two'))
        paused=await cold.cycle(**{**second_args,'operation_id':'three',
            'expression_parameters':{**second_expression,'call':forbidden}})
        assert paused.disposition=='paused' and len(received)==2
        assert not journal.read(event_type='delivery.succeeded')
        assert not journal.read(event_type='transport.publisher.bound')
        print('standard_channel_two_intents_reopen_pause:PASS')
    print('standard_channel_case='+mode+':PASS')


async def main():
    with tempfile.TemporaryDirectory(prefix='alive-standard-channel-') as directory:
        for mode in ('success','false','unknown','long','cancel','exception','missing','disconnected',
                     'wrong-thread','forged-model','wrong-platform','wrong-profile','revoked','write-failure'):
            await test(Path(directory)/mode,mode)


asyncio.run(main())
print('HERMES_ALIVE_STANDARD_CHANNEL_EXECUTION_OK')
