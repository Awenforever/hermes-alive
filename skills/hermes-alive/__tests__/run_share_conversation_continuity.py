"""Real Core context dispatch + exact synthetic share/source/outcome persistence.

Synthetic planner/adapter; no actual model, account, message or consumer install.
The Core fixture parser requires --core with the exact read-only source supply.
"""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import run_core_session_routing as core
from run_alive_kernel_expression_runtime import scenario
from alive_kernel import AutonomyPolicyProjection, EventEnvelope, ExperienceJournal, PolicyContext, ReceiptLevel, Sensitivity
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.conversation_continuity import ShareContinuityStore, ContinuityUnavailable, continuation_context
from alive_kernel.content_vault import ContentReference
from alive_kernel.privacy import LocalIdentityProtector
from alive_kernel.retention import RetentionDirection


async def test(home, mode, *, exercise=None):
    home.mkdir()
    (home/'config.yaml').write_text(json.dumps({'plugins': {'entries': {'hermes-alive':
        {'settings': {'kernel_shadow': {'enabled': True}}}}}}), encoding='utf-8')
    token = core.set_hermes_home_override(home)
    manager = None
    try:
        manager = core.get_plugin_manager()
        manifest = core.PluginManifest(name='hermes-alive', version='0.0.0')
        manager._plugins[manifest.name] = core.LoadedPlugin(manifest, enabled=True)
        context = core.PluginContext(manifest, manager)
        binding = core.binding_module.GatewayHostBinding(context)
        received = []
        class Adapter(core.Adapter):
            async def send(self, chat_id, content, **kwargs):
                received.append(content)
                # The share exists before transport IO, but isn't labeled sent.
                pending = store.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE)
                assert pending[0]['text'] == content
                assert pending[0]['submission_status'] == 'submission_unconfirmed'
                if mode == 'exception':
                    raise TimeoutError('possible partial effect')
                return SimpleNamespace(success=mode != 'false', message_id='opaque-synthetic')
        adapter = Adapter(core.Platform.TELEGRAM)
        runner = core.runner_for(home, {core.Platform.TELEGRAM: adapter})
        adapter.gateway_runner = runner
        await adapter.connect()
        router = binding.session_router('telegram')
        source = core.SessionSource(platform=core.Platform.TELEGRAM, chat_id='-1007654321',
            user_id='private-user-marker', thread_id='7', message_id='synthetic')
        entry = runner.session_store.get_or_create_session(source)
        scope = router.capture_target(session_key=entry.session_key, user_id=source.user_id, platform='telegram')
        root = home/'plugin-data/hermes-alive/runtime/kernel'
        owner = scope.principal(LocalIdentityProtector(root/'identity.key'))
        summary = 'Public synthetic source: the workshop repairs bicycles, not cars.'
        if mode == 'success':
            summary += ' Additional source material, not a user instruction.' * 40
        journal, parameters, expressed = await scenario(root, 'share', return_ready=True,
            subject=owner, source_summary=summary,
            draft_text='The workshop repairs bicycles, not cars.' if mode == 'success' else None)
        runtime = AutonomousCycleRuntime(journal)
        store = ShareContinuityStore(runtime.outbox)
        bridge = binding.attach_continuity(store, router, clearance=Sensitivity.PRIVATE)
        core.refused(lambda:router.standard_send_parameters(scope,continuity=None,
                                                            clearance=Sensitivity.PRIVATE))
        core.refused(lambda:router.standard_send_parameters(scope,continuity=bridge,
                                                            clearance=Sensitivity.PUBLIC))
        send_parameters=router.standard_send_parameters(scope,continuity=bridge,
                                                        clearance=Sensitivity.PRIVATE)
        from tools.send_message_targets import resolve_send_target
        assert send_parameters['resolve_target'] is resolve_send_target
        assert send_parameters['extract_media'] is core.BasePlatformAdapter.extract_media
        assert send_parameters['resolve_target']('telegram','-1007654321:7')==('-1007654321','7',None)
        assert not received  # assembly and parser validation perform no send
        assert not store.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE)
        if mode != 'no-consent':
            consent = store.retention.append_consent(subject=owner, actor=owner, enabled=True,
                retention_days=30, directions=(RetentionDirection.INBOUND if mode=='wrong-direction'
                                              else RetentionDirection.OUTBOUND,),
                sensitivity=Sensitivity.PRIVATE, operation_id='share-consent')
            store.retention.apply(consent)
        if mode == 'late-off':
            for index in range(1001):
                journal.append(EventEnvelope(event_id='noise:' + str(index),
                    event_type='test.structural', source='test.synthetic', actor='system:fixture', subject=owner))
            # Deliberately unprojected OFF beyond the first1000 records.
            store.retention.append_consent(subject=owner, actor=owner, enabled=False,
                retention_days=30, directions=(RetentionDirection.OUTBOUND,),
                sensitivity=Sensitivity.PRIVATE, operation_id='late-off')
        policies = AutonomyPolicyProjection(journal)
        policies.apply(policies.append_update(subject=owner, actor=owner, expected_revision=0,
            enabled=True, context=PolicyContext(can_interrupt=True), operation_id='enable'))
        host = runtime.preparation.authorizer.host
        snapshot = host.observe_snapshot(snapshot_id='standard', hermes_version='0.22.5', plugin_api_version=1,
            capabilities={'hermes.channel.send': {'interface':'core.adapter.send', 'available':True,
            'public_api':True, 'receipt_level':ReceiptLevel.REQUEST_ACCEPTED.value}})
        authority = journal.append(EventEnvelope(event_type='conversation.inbound', source='test.synthetic',
            actor=owner, subject=owner, payload={'authorizes_route_binding_id':'selected',
            'authorizes_host_snapshot_event_id':snapshot.event_id,
            'authorizes_receipt_requirement':ReceiptLevel.REQUEST_ACCEPTED.value}))
        host.bind_route(binding_id='selected', subject=owner, capability='hermes.channel.send',
            snapshot_event_id=snapshot.event_id, route=dict(scope.route),
            authority_event_id=authority.event.event_id, receipt_requirement=ReceiptLevel.REQUEST_ACCEPTED)
        delegation = ActionDelegationStore(journal).grant(subject=owner, actor=owner,
            policy_event_id=policies.current(owner).event_id, route_binding_id='selected', action_kinds=('share',),
            maximum_sensitivity=Sensitivity.PRIVATE, expires_at=datetime.now(timezone.utc)+timedelta(hours=1),
            operation_id='delegate', allow_natural_expression=True)
        expression = {k:v for k,v in parameters.items() if k not in ('subject','operation_id','policy_context')}
        try:
            result = await runtime.cycle(subject=owner, operation_id='one', expression_parameters=expression,
                resolve_binding=lambda _:None, execute=True, channel_execution='standard', worker_id='worker',
                authorization_parameters={'authorization_operation_id':'authorize', 'route_binding_id':'selected',
                                          'delegation_event_id':delegation.event.event_id},
                send_parameters=send_parameters)
        except (ContinuityUnavailable, TimeoutError):
            assert mode in ('no-consent','wrong-direction','late-off','exception')
        else:
            assert mode in ('success','false') and result.disposition == 'submitted'
        if mode in ('no-consent','wrong-direction','late-off'):
            assert not received and not journal.read(event_type='conversation.share_prepared')
            print('share_conversation_case=' + mode + ':PASS')
            return
        assert received == [expressed.text]
        reopened = ShareContinuityStore(AutonomousCycleRuntime(ExperienceJournal(journal.path)).outbox)
        shares = reopened.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE)
        assert len(shares) == 1 and shares[0]['text'] == expressed.text
        assert shares[0]['submission_status'] == {'false':'error_reported',
            'exception':'submission_unconfirmed'}.get(mode,'success_reported')
        assert not shares[0]['external_delivery_proven']
        assert shares[0]['sources'][0]['url'] == 'https://example.invalid/workshop'
        assert 'bicycles, not cars' in shares[0]['sources'][0]['excerpt']
        assert shares[0]['sources'][0]['reading_status'] == 'retained_excerpt'
        assert shares[0]['sources'][0]['reading_scope'] == {'collector_scope_reported': False}
        original_reads = journal.read(event_type='opportunity.synthesis_started')
        assert len(original_reads) == 1
        assert shares[0]['sources'][0]['excerpt_policy'] == original_reads[0].event.payload.get(
            'interpreter_method',{}).get('source_excerpt_policy')
        assert not reopened.read(scope=scope.binding_document(), clearance=Sensitivity.PUBLIC)
        for change in ({'thread_id':'other'}, {'session_id':'reset'}, {'user_id':'other'},
                       {'transport_profile':'other-bot'}, {'runtime_profile':'other-profile'}):
            with patch.object(reopened.vault,'resolve_json',side_effect=AssertionError('foreign context decrypted')):
                assert not reopened.read(scope=replace(scope,**change).binding_document(), clearance=Sensitivity.PRIVATE)
        # Actual Core hook dispatcher/turn collector gets the persisted body and
        # source. No test-only context string or fake user history is supplied.
        variables = core.set_session_vars(platform='telegram', chat_id=source.chat_id, user_id=source.user_id,
            session_key=entry.session_key, session_id=entry.session_id)
        try:
            from agent.turn_context import _collect_pre_llm_call_context
            agent = SimpleNamespace(session_id=entry.session_id, model='not-called',
                                    platform='telegram', _user_id=source.user_id)
            messages = [{'role':'system','content':'unchanged'}, {'role':'user','content':'What can they repair?'}]
            original = json.dumps(messages)
            def collect():
                return _collect_pre_llm_call_context(agent, effective_task_id='task', turn_id='turn',
                    original_user_message=messages[-1]['content'], messages=messages,
                    conversation_history=messages[:-1])
            text = collect()
            conversation = json.loads(text.split('\n',1)[1])['alive_shares'][0]
            assert conversation['text'] == expressed.text
            assert set(conversation) == {'prepared_at','text','sources'}
            expected_source = {
                key:value for key,value in shares[0]['sources'][0].items()
                if key not in ('event_id','excerpt_policy','reading_scope')}
            expected_source['reading_scope'] = {'evidence_basis':'retained_excerpt'}
            assert conversation['sources'][0] == expected_source
            # Operational diagnostics stay unchanged; only model-facing evidence
            # is projected. A negative proof flag is not a negative world fact.
            assert shares[0]['sources'][0]['reading_scope'] == {'collector_scope_reported':False}
            assert 'submission_status' not in text and 'success_reported' not in text
            assert shares[0]['submission_status'] and shares[0]['share_id']
            assert 'bicycles, not cars' in text and json.dumps(messages) == original
            if mode == 'success':
                # The actual Core collector applies its real spill normalizer.
                # Match its cap without changing user settings or granting a
                # file-reading tool to recover a truncated reference.
                from tools.hook_output_spill import get_spill_config
                for raw_cap, enabled in ((2000, True), ('2200', True), (None, True),
                                          (0, True), (True, True), (1, False)):
                    config = {'hooks': {'output_spill': {'max_chars': raw_cap, 'enabled': enabled}}}
                    with patch('hermes_cli.config.load_config_readonly', return_value=config), \
                         patch('hermes_cli.config.load_config', return_value=config):
                        resolved = get_spill_config()
                        bounded = collect()
                    assert 'output truncated' not in bounded
                    if enabled:
                        assert len(bounded) <= resolved['max_chars']
                    if raw_cap is not True:
                        body = json.loads(bounded.split('\n',1)[1])['alive_shares'][0]
                        assert body['text'] == expressed.text
                        if raw_cap in (2000, '2200'):
                            assert body['sources'][0]['excerpt_in_context'] is False
                            assert 'excerpt' not in body['sources'][0]
                            assert body['sources'][0]['url'] == shares[0]['sources'][0]['url']
                    assert json.dumps(messages) == original
                # This retrieval helper itself never calls Core's write-capable
                # convenience loader. The collector owns its own config loading.
                budget_reader = importlib.import_module(bridge.__class__.__module__)._context_budget
                with patch('hermes_cli.config.load_config', side_effect=AssertionError('context read wrote config')):
                    assert budget_reader(store) == 10000
            # Cold persistent routing + reopened vault, not the authoring
            # worker's in-memory source. This is not a daemon restart proof.
            runner.session_store = core.SessionStore(home/'sessions',runner.config)
            bridge.store = reopened
            assert collect() == text
            if exercise is not None:
                await exercise(home=home, context=context, runner=runner, router=router,
                    bridge=bridge, scope=scope, source=source, entry=entry,
                    exact_share=expressed.text)
            agent._parent_session_id = 'child'
            assert collect() == ''
        finally:
            core.clear_session_vars(variables)
        # Stopping future retention is not deleting the history already granted.
        store.retention.apply(store.retention.append_consent(subject=owner, actor=owner, enabled=False,
            retention_days=30, directions=(RetentionDirection.OUTBOUND,),
            sensitivity=Sensitivity.PRIVATE, operation_id='stop'))
        assert reopened.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE)
        record = journal.read(event_type='conversation.share_prepared')[0]
        future = datetime.now(timezone.utc) + timedelta(days=31)
        assert not reopened.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE, now=future)
        source_record = journal.get(shares[0]['sources'][0]['event_id'])
        source_id = ContentReference.from_event_payload(source_record.event.payload['content']).content_id
        class Future(datetime):
            @classmethod
            def now(cls,tz=None):
                return datetime.now(timezone.utc)+timedelta(days=8)
        with patch('alive_kernel.content_vault.datetime',Future):
            expired = reopened.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE)
            assert expired[0]['text'] == expressed.text
            assert expired[0]['sources'][0]['reading_status'] == 'no_longer_retained'
        # Planning/source TTL is not the separately consented outward history
        # window. A physical expiry sweep must not masquerade as user forgetting.
        store.vault.erase_expired(now=datetime.now(timezone.utc)+timedelta(days=8))
        retained = reopened.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE)
        assert retained[0]['text'] == expressed.text
        assert retained[0]['sources'][0]['reading_status'] == 'no_longer_retained'
        assert not store.vault.explicit_erasure_recorded(source_id)
        # A later explicit forget request still invalidates that derived copy.
        if mode == 'false':
            # Stop disclosure immediately when the owner's erasure is durable,
            # even if the physical erase worker has not yet resumed.
            request = store.retention.append_erasure_request(subject=owner,actor=owner,operation_id='forget')
            with patch.object(reopened.vault,'resolve_json',side_effect=AssertionError('forgotten context decrypted')):
                assert not reopened.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE)
            store.retention.execute_erasure(request)
        else:
            store.vault.erase_item(source_id)
        assert not reopened.read(scope=scope.binding_document(), clearance=Sensitivity.PRIVATE)
        assert store.vault.explicit_erasure_recorded(ContentReference.from_event_payload(record.event.payload['content']).content_id)
        raw = journal.path.read_bytes()
        assert b'-1007654321' not in raw and b'bicycles, not cars' not in raw
        assert not journal.read(event_type='delivery.succeeded') and len(journal.read(event_type='dispatch.started')) == 1
        binding.close()
        assert bridge.context() is None
        print('share_conversation_case=' + mode + ':PASS')
    finally:
        if manager is not None:
            manager.unload()
        core.reset_hermes_home_override(token)


def test_collection_limits_are_not_world_negatives():
    shares = [{'prepared_at':'2026-01-01T00:00:00+00:00','text':'Exact shared words.',
        'sources':[{'event_id':'private-source-id','title':'Observed result',
            'url':'https://example.invalid/result','excerpt':'An author reports a result.',
            'reading_status':'retained_excerpt','reading_scope':{
                'reported_read_scope':'search_listing','independent_verification_proven':False,
                'video_consumption_proven':False,'reported_content_representation':'machine_summary'}},
            {'event_id':'private-erased-id','reading_status':'no_longer_retained'}]}]
    original = json.dumps(shares)
    text = continuation_context(shares)
    references = json.loads(text.split('\n',1)[1])['alive_shares']
    assert references[0]['text'] == 'Exact shared words.'
    assert references[0]['sources'][0]['reading_scope'] == {
        'evidence_basis':'retained_excerpt','reported_read_scope':'search_listing',
        'reported_content_representation':'machine_summary'}
    assert references[0]['sources'][1] == {'reading_status':'no_longer_retained'}
    assert 'independent_verification_proven' not in text and 'video_consumption_proven' not in text
    assert 'private-source-id' not in text and 'private-erased-id' not in text
    assert json.dumps(shares) == original  # No rewriting of the protected trace.
    assert continuation_context([]) == ''


def test_atomic_context_budget():
    sources = [{'title': 'Long source', 'url': 'https://example.invalid/long',
        'excerpt': 'Full source clause; ' * 1200, 'reading_status': 'retained_excerpt',
        'reading_scope': {'reported_read_scope': 'webpage_extract'}},
        {'title': 'Short source', 'url': 'https://example.invalid/short',
         'excerpt': 'The workshop repairs bicycles, not cars.', 'reading_status': 'retained_excerpt'}]
    shares = [{'prepared_at': '2026-01-01T00:00:00+00:00', 'text': 'Older whole message.', 'sources': []},
        {'prepared_at': '2026-01-02T00:00:00+00:00',
         'text': '新消息，保留原文。\n`a\\b` and "quoted" words.\nhttps://example.invalid/exact', 'sources': sources}]
    original = json.dumps(shares)
    for budget in (1, 100, 1500, 2000, 10000, 65536):
        text = continuation_context(shares, max_chars=budget)
        assert len(text) <= budget
        if '\n{' not in text:
            assert shares[-1]['text'] not in text and shares[0]['text'] not in text
            continue
        references = json.loads(text.split('\n',1)[1])['alive_shares']
        assert references[-1]['text'] == shares[-1]['text']
        for source in references[-1]['sources']:
            if 'excerpt' in source:
                assert source['excerpt'] in tuple(s['excerpt'] for s in sources)
            else:
                assert source['excerpt_in_context'] is False
    latest_large = [shares[0], {**shares[-1], 'text': 'Long exact outward text. ' * 1000}]
    omitted = continuation_context(latest_large, max_chars=10000)
    assert 'Older whole message.' not in omitted and 'Long exact outward text.' not in omitted
    assert 'reference omitted' in omitted
    assert continuation_context(shares, max_chars=65536) == continuation_context(shares)
    assert json.dumps(shares) == original
    for invalid in (True, 0, -1, 1.5, '10000'):
        try: continuation_context(shares, max_chars=invalid)
        except ValueError: pass
        else: raise AssertionError('invalid context budget accepted')


if __name__ == '__main__':
    test_collection_limits_are_not_world_negatives()
    test_atomic_context_budget()
    with tempfile.TemporaryDirectory(prefix='alive-share-continuity-') as directory:
        try:
            for mode in ('success','false','exception','no-consent','wrong-direction','late-off'):
                asyncio.run(test(Path(directory)/mode, mode))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(directory)
    print('HERMES_ALIVE_SHARE_CONVERSATION_CONTINUITY_OK')
