"""Current Core guided setup -> authorized native cycle -> deeper source -> share.

Core SDK/registry/session/adapter paths are real; HTTP, pages, model decisions and
URL safety are controlled. Extracts deliberately have no source title, to prove
that optional display metadata cannot discard usable evidence. No actual provider call, physical message or quality
round. In particular this does not use the old kernel-shadow setup surface.
"""
import asyncio,importlib,json,os,shutil,sys,tempfile
from datetime import timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import run_core_session_routing as core
from run_core_guided_setup import cli


async def test(home,*,fit_revision=False,revoke_after_capture=False,search_alignment='matches',
               claim_scope_conflict=False):
    feedback_case=os.environ.get('HERMES_ALIVE_TEST_NATIVE_FEEDBACK')=='1'
    assert search_alignment in ('matches','justified_pivot','conflicts','uncertain')
    assert search_alignment=='matches' or not (fit_revision or revoke_after_capture)
    search_negative=search_alignment in ('conflicts','uncertain')
    assert not claim_scope_conflict or (search_alignment=='matches' and not (fit_revision or revoke_after_capture or feedback_case))
    review_negative=search_negative or claim_scope_conflict
    import httpx
    home.mkdir(exist_ok=True)
    assert not any(home.iterdir()),'fixture requires its newly reserved empty profile'
    shutil.copytree(core.repo,home/'plugins/hermes-alive',ignore=shutil.ignore_patterns('.git'))
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':{'provider':'custom:owner','default':'configured-primary'},
        'custom_providers':[{'name':'owner','model':'configured-primary','base_url':'https://provider.invalid/v1',
            'key_env':'OWNER_MAIN_KEY','api_mode':'chat_completions'}],'agent':{'reasoning_effort':False}}))
    (home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_OWNER_KEY\n')
    rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention',
        '--public-query','synthetic public observation','--confirm-public-reads','--confirm-cited-reads',
        '--confirm-public-refinement',*(('--confirm-share-feedback',) if feedback_case else ()))
    assert rc==0 and cli(home,'install-runtime','--engine','kernel')[0]==0
    token=core.set_hermes_home_override(home);manager=None
    url='https://example.invalid/observation';reads=[];stages=[];sent=[]
    feedback_probe={'expected':None,'seen':False,'author_seen':False}
    fixture_errors=[]
    qualifier='The trial used an existing instrument, not a newly constructed one.'
    overstatement='The trial used a newly constructed instrument.'
    try:
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];binding=loaded.module._gateway_host_binding
        from hermes_cli.plugins import get_plugin_command_handler
        from tools.registry import registry
        handler=get_plugin_command_handler('alive')
        class Adapter(core.Adapter):
            async def send(self,chat_id,content,**kwargs):
                sent.append((chat_id,content))
                return core.SimpleNamespace(success=True,message_id='synthetic-local-submission')
        adapter=Adapter(core.Platform.TELEGRAM)
        runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter});adapter.gateway_runner=runner
        await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='7654321',
            user_id='synthetic-depth-owner',message_id='synthetic-depth-confirm')
        entry=runner.session_store.get_or_create_session(source)
        async def command(args):
            return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=args)
        assert '已确认' in await command(staged['confirmation_command'].removeprefix('/alive '))
        def dispatch(name):
            def operation(args,**kwargs):
                reads.append((name,args))
                if name=='web_search':
                    assert args==dict(query='synthetic public observation',limit=3)
                    return json.dumps({'success':True,'data':{'web':[dict(url=url,title='Public trial',
                        description='A public observation with a qualification worth understanding.')]}})
                assert args['urls']==[url] and args['char_limit'] in (6000,15000)
                text=('An introduction describes observing before intervention.' if args['char_limit']==6000
                    else 'Public background. '*510+qualifier)
                return json.dumps({'results':[dict(url=url,title='',content=text)]})
            return operation
        for name in ('web_search','web_extract'):
            registry.register(name=name,toolset='web',schema=dict(name=name,description='Synthetic public source',
                parameters={'type':'object'}),handler=dispatch(name),override=True,scope=str(home))
        def excerpt(row):
            return row.get('summary_excerpt') or ''.join(p['text'] for p in row.get('summary_passages',[]))
        def respond(request):
            if not request.url.path.endswith('/chat/completions'):
                return httpx.Response(503,request=request,json={'error':{'message':'synthetic metadata unavailable'}})
            assert request.url.host=='provider.invalid'
            body=json.loads(request.content)
            raw=next(m['content'] for m in body['messages'] if m['role']=='user')
            try:data=json.loads(raw)
            except ValueError:data=json.loads(raw.split('\n',1)[1])
            if isinstance(data,list):
                stage='select';value={'candidate_id':next(c['candidate_id'] for c in data
                    if c['candidate_id'].startswith('opportunity-candidate:')),'rationale':'Synthetic selection'}
            elif data.get('method')=='public-source-depth-v2':
                stage='deepen';assert 'user_context' not in data
                value=dict(search_query=None,read_targets=[],deepen_source_ref=data['deeper_read_sources'][0]['source_ref'],
                    reason='Read the scope qualification of the current trial.')
            elif 'sources' in data:
                stage='reading';value=dict(source_refs=[data['sources'][0]['source_ref']],question='What was actually tried?',
                    value_hypothesis='A bounded understandable result.')
            elif 'index_windows' in data:
                stage='feedback_recall'
                entries=[item for window in data['index_windows'] for item in window['entries']]
                assert entries and entries[0]['attribution']=='main_turn_semantic_association_not_quote_proof'
                value=dict(outcome_event_ids=[entries[0]['outcome_event_id']],continue_older=False,
                    reason='Inspect the exact bounded prior feedback, preserving its one-off scope.')
            elif 'opportunities' in data:
                stage='interpret';assert any(qualifier in excerpt(e) for e in data['opportunities'])
                if feedback_probe['expected'] is not None:
                    pairs=data.get('recent_feedback_context',[])
                    assert any(pair.get('status')=='tentative_reaction_to_prior_share_topic'
                        and pair.get('reaction')=='positive' and pair.get('automatic_profile_update') is False
                        for pair in pairs),pairs
                    assert feedback_probe['expected'] not in raw
                    feedback_probe['seen']=True
                if 'search_context' in data:
                    assert data['search_context']['current_owner_search_request_supplied'] is False
                else:
                    # A later wake can interpret retained opportunities without
                    # doing another configured search. The first source-depth
                    # journey must still exercise its explicit route contract.
                    assert feedback_probe['expected'] is not None
                item=next(e for e in data['opportunities'] if qualifier in excerpt(e))
                assert item['provenance_metadata']['source_title_available'] is False
                assert item['provenance_metadata']['title_is_placeholder'] is True
                value={'candidates':[dict(agenda_item_id=item['agenda_item_id'],kind='share',topic='public trial',
                    communication_plan=dict(version=3,recipient_goal='Synthetic contribution',speech_act='share',contents=[],behavior_constraints=[]),
                    dimensions={n:dict(value=.05 if n in ('risk','urgency','interruption_cost') else .9,reason='Synthetic judgment')
                        for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')})]}
            elif 'expression_binding' in data:
                from final_review_fixture import controlled_final_findings
                assert data['expression_binding']['final_assessment_scope'] == 'factual-support-and-communication-fit-v12'
                assert 'test fit as an opening in a real conversation' in body['messages'][0]['content']
                if feedback_probe['expected'] is not None:
                    assert not data['recent_feedback_context'] and feedback_probe['expected'] not in raw
                if feedback_probe['expected'] is None or 'search_context' in data:
                    assert data['search_context']['kind']=='configured-discovery-route-v1'
                    assert data['search_context']['current_owner_search_request_supplied'] is False
                conflict=(fit_revision and 'DENSE_TEST_OPENING' in data['candidate']['text']
                    or feedback_probe['expected'] is not None)
                stage='final';value=controlled_final_findings(data,
                    fit='conflicts' if conflict else 'fits',
                    reason='Synthetic whole-form mismatch.' if conflict else 'Synthetic form fits the situation.')
                if search_alignment!='matches':
                    assert data.get('approved_search_queries')==['synthetic public observation']
                    value.update(search_alignment=search_alignment,scope_reason='Synthetic unresolved search scope.')
                if claim_scope_conflict:
                    assert data['candidate']['text'].startswith(overstatement)
                    assert qualifier in data['candidate']['text']
                    value.update(claim_scope='overstated',claim_scope_reason='The opening contradicts the retained passage.')
            elif 'meaning' in data and 'candidate' in data:
                stage='semantic';value=dict(atom_reviews=[dict(atom_id=x['atom_id'],preserved=True,risks=[])
                    for x in data['meaning']['atoms']],added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True)
            elif 'meaning' in data:
                stage='author';assert qualifier in raw
                if not data.get('correction'):
                    assert body['messages'][0]['content'].startswith('Open a conversation with a worthwhile discovery.')
                if feedback_probe['expected'] is None:
                    assert data['expression_context']['search_context']['kind']=='configured-discovery-route-v1'
                    assert 'not a current research request' in body['messages'][0]['content']
                    assert any(e['provenance_metadata'].get('title_is_placeholder') is True
                        for e in data['expression_context']['source_evidence'])
                if feedback_probe['expected'] is not None:
                    pairs=data['expression_context'].get('literal_feedback_context',[])
                    assert not pairs, 'author received an old native feedback pair'
                    assert feedback_probe['expected'] not in raw, (
                        'old native wording reached the repair prompt' if data.get('correction')
                        else 'old native wording reached the initial author prompt')
                    if data.get('correction'):
                        assert not data['correction']['grounding_context']['recent_feedback_context']
                    feedback_probe['author_seen']=True
                    feedback_probe['author_mode']=data['expression_context'].get('method')
                source_url=url
                if feedback_probe['expected'] is not None:
                    urls={literal for atom in data['meaning']['atoms']
                          for literal in atom['protected_literals']
                          if literal.startswith('https://example.invalid/')}
                    assert len(urls)==1,urls
                    source_url=next(iter(urls))
                value=qualifier+' [Source](<'+source_url+'>)'
                if claim_scope_conflict:
                    value=overstatement+' '+value
                if (review_negative or feedback_probe['expected'] is not None) and data.get('correction'):
                    if review_negative:
                        assert 'review-anchored' in body['messages'][0]['content'] or 'Repair the supplied' in body['messages'][0]['content']
                    else:
                        assert isinstance(data['correction'],dict)
                    stage='abstain';value={'abstain':True}
                if fit_revision:
                    if data.get('correction'):
                        assert 'may change the opening, focus, ordering and depth' in body['messages'][0]['content']
                        stage='revision';value={'text':'One concrete finding: '+value}
                    else:value='DENSE_TEST_OPENING. '+value
            elif 'candidate' in data and 'evidence' in data:
                stage='source';assert qualifier in raw
                value=dict(verdict='supported',unsupported_claims=[],uncertainties=[],reason='Synthetic source verdict')
            else:raise AssertionError('unexpected controlled stage '+str(list(data)))
            stages.append(stage)
            return httpx.Response(200,request=request,json=dict(id='synthetic-depth',object='chat.completion',created=0,
                model=body['model'],choices=[dict(index=0,message=dict(role='assistant',content=value if isinstance(value,str)
                    else json.dumps(value)),finish_reason='stop')],usage=dict(prompt_tokens=30,completion_tokens=30,total_tokens=60)))
        def checked(request):
            try:return respond(request)
            except Exception as exc:
                fixture_errors.append(type(exc).__name__)
                import traceback;traceback.print_exc();raise
        async def send(client,request,*args,**kwargs):return checked(request)
        execution=importlib.import_module(loaded.module.__name__+'.kernel_execution_bridge')
        continuity=execution.kernel('conversation_continuity').ShareContinuityStore
        prepare=continuity._prepare
        captured=[]
        def capture(store,dispatch,**kwargs):
            record=prepare(store,dispatch,**kwargs)
            if revoke_after_capture:
                captured.append(record)
                authorization=store.journal.get(
                    store.journal.get('action.attempt:'+dispatch.lease.attempt_id).event.payload['authorization_event_id'])
                store.outbox.host.revoke_route(authorization.event.payload['route_binding_id'])
            return record
        async def allowed(self,target):return target==url
        with patch.object(httpx.AsyncClient,'send',send),patch.object(httpx.Client,'send',lambda client,request,*a,**k:checked(request)),\
             patch.object(execution.kernel('core_discovery_tools').CoreDiscoveryTools,'allow_url',allowed),\
             patch.object(continuity,'_prepare',capture):
            assert '已启用' in await command('enable')
            binding.arguments['stop'].set();await binding.task
            native=binding.native
            if revoke_after_capture:
                error=execution.kernel('dispatch_outbox').DispatchOutboxError
                try:
                    await native.step(binding.arguments['build_parameters']())
                except error as exc:
                    assert 'launch route is no longer authorized' in str(exc),str(exc)
                else:
                    raise AssertionError('revocation after capture did not stop launch')
                assert len(captured)==1 and not sent
                assert captured[0].event.payload['external_delivery_proven'] is False
                print('HERMES_ALIVE_NATIVE_CAPTURE_REVOCATION_OK',flush=True)
                return
            result=await native.step(binding.arguments['build_parameters']())
            if review_negative:
                assert result.disposition=='content_review_attention',result
                assert result.prepared is not None and result.prepared.authorization is None
                assert result.prepared.attempt_event_id is None and result.submission is None
                assert stages.count('final')==1 and stages.count('abstain')==1 and not sent
                setup=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge')
                journal=setup.setup_store(binding).journal
                review=journal.get(result.prepared.initial_final_review_event_id)
                assert review.event.payload['verdict']==('uncertain' if search_alignment=='uncertain' else 'unsupported')
                assert not journal.read(event_type='dispatch.started')
                assert not journal.read(event_type='action.authorization_evaluated')
                assert not native.pending
                marker=('HERMES_ALIVE_CORE_CLAIM_SCOPE_REFUSAL_OK' if claim_scope_conflict
                        else 'HERMES_ALIVE_CORE_SEARCH_ALIGNMENT_REFUSAL_OK '+search_alignment)
                print(marker,flush=True)
                return
            assert result.disposition=='submitted',result
            assert not native.pending
        assert reads==[('web_search',dict(query='synthetic public observation',limit=3)),
            ('web_extract',dict(urls=[url],char_limit=6000)),('web_extract',dict(urls=[url],char_limit=15000))]
        assert len(sent)==1 and qualifier in sent[0][1]
        assert stages.count('final')==(2 if fit_revision else 1)
        assert stages.count('revision')==int(fit_revision)
        if fit_revision:assert 'DENSE_TEST_OPENING' not in sent[0][1]
        assert stages.count('reading')==stages.count('deepen')==1
        assert all(stage in stages for stage in ('interpret','select','author','semantic','final'))
        if not feedback_case:
            from core_native_feedback_case import exercise_unconsented
            await exercise_unconsented(core,loaded,binding,runner,source,entry)
        if feedback_case:
            from core_native_feedback_case import exercise
            setup = importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge')
            store = setup.setup_store(binding)
            vault_type = type(store.vault)
            put_json = vault_type.put_json
            feedback_module = execution.kernel('native_feedback')
            legacy = os.environ.get('HERMES_ALIVE_TEST_LEGACY_FEEDBACK_DERIVATIVES') == '1'
            erase_frames = legacy or os.environ.get('HERMES_ALIVE_TEST_FRAME_ERASURE') == '1'
            graph_only = os.environ.get('HERMES_ALIVE_TEST_FRAME_GRAPH_ONLY') == '1'
            projection_type = execution.kernel('deliberation_store').DeliberationProjection
            append_frame = projection_type.append_frame
            affected, unrelated = {}, {}

            def legacy_frame(projection, *args, **options):
                options.pop('candidate_sources', None)
                return append_frame(projection, *args, **options)

            def write_legacy(vault, value, **options):
                if options['purpose'] in ('opportunity.candidates', 'opportunity.protocol-failure',
                                          'opportunity.source-support', 'opportunity.source-support-invalid',
                                          'message.model_candidate', 'semantic.local-correction',
                                          'semantic.source-revision', 'semantic.protocol-failure',
                                          'deliberation.selection'):
                    options.pop('depends_on', None)
                return put_json(vault, value, **options)

            async def next_cycle(text):
                nonlocal url
                shadow = os.environ.get('HERMES_ALIVE_TEST_FEEDBACK_SHADOW') == '1'
                feedback_probe['expected']=text
                # Offer a fresh synthetic resource if collection is due. A
                # normal wake may instead reason over retained opportunities.
                url='https://example.invalid/next-public-observation'
                waiting=await native.step(binding.arguments['build_parameters']())
                assert waiting.disposition=='waiting_for_change',waiting.disposition
                assert not feedback_probe['seen'],'normal cadence was bypassed'
                cycle_clock=execution.kernel('autonomous_cycle_runtime')
                actual_datetime=cycle_clock.datetime
                class AfterCadence(actual_datetime):
                    @classmethod
                    def now(cls,tz=None):
                        moment=actual_datetime.now(timezone.utc)+timedelta(hours=1,seconds=1)
                        return moment.astimezone(tz) if tz is not None else moment.replace(tzinfo=None)
                original_binder = native.preparation.bind_parameters
                async def bind_shadow(**kwargs):
                    bound = await original_binder(**kwargs)
                    # The installed preparation attaches delivery fields even
                    # when they were absent at the test's input boundary.
                    assert bound.pop('defer_until_eligible') is True
                    assert bound.pop('authorization_parameters')
                    bound.pop('send_parameters', None)
                    bound.pop('worker_id', None)
                    return bound
                with patch.object(httpx.AsyncClient,'send',send),patch.object(httpx.Client,'send',lambda client,request,*a,**k:checked(request)),\
                     patch.object(execution.kernel('core_discovery_tools').CoreDiscoveryTools,'allow_url',allowed),\
                     patch.object(cycle_clock,'datetime',AfterCadence),\
                     patch.object(native.host,'execute',not shadow),\
                     patch.object(native.preparation,'bind_parameters',bind_shadow if shadow else original_binder),\
                     patch.object(projection_type,'append_frame',legacy_frame if legacy else append_frame),\
                     patch.object(vault_type,'put_json',write_legacy if legacy else put_json):
                    following=await native.step(binding.arguments['build_parameters']())
                if shadow:
                    assert following.prepared is None and following.submission is None
                assert feedback_probe['seen'], ('next Native cycle did not receive recorded feedback',following.disposition)
                assert feedback_probe['author_seen'],'source-led author did not receive the feedback'
                assert following.disposition=='content_review_attention' and len(sent)==1,following.disposition
                assert stages.count('abstain')==1 and not fixture_errors,fixture_errors
                affected_selection = None
                for row in store.journal.read(event_type='opportunity.source_support_completed'):
                    content_id = row.event.payload['content']['content_id']
                    document = store.vault.resolve_json(content_id, expected_subject=row.event.subject,
                        expected_purpose='opportunity.source-support', expected_sensitivity=row.event.sensitivity)
                    has_input = any(pair.get('current_input') == text
                                    for pair in document['snapshot']['recent_feedback_context'])
                    group = affected if has_input else unrelated
                    group[content_id] = 'snapshot'
                    start = store.journal.get(row.event.causation_id)
                    expression = store.journal.get(start.event.causation_id)
                    assert expression.event.event_type == 'message.model_candidate'
                    expression_ref = expression.event.payload['content']['content_id']
                    assert store.vault.resolve_json(expression_ref)['text']
                    group[expression_ref] = 'text'
                    selection = store.journal.get(expression.event.causation_id)
                    selection_ref = selection.event.payload['content']['content_id']
                    assert store.vault.resolve_json(selection_ref)['rationale']
                    group[selection_ref] = 'rationale'
                    if erase_frames:
                        frame_row = store.journal.get('deliberation.frame:' + selection.event.payload['frame_id'])
                        frame_ref = frame_row.event.payload['content']['content_id']
                        document = store.vault.resolve_json(frame_ref)
                        body = next(item['content_id'] for item in document['candidates']
                                    if item['candidate_id'] == selection.event.payload['candidate_id'])
                        assert store.vault.resolve_json(body)
                        group[frame_ref] = 'candidates'
                        group[body] = 'candidate-content'
                    if has_input:
                        affected_selection = selection
                assert affected and unrelated and affected_selection is not None
                selection = affected_selection.event.payload
                frame = store.journal.get('deliberation.frame:' + selection['frame_id'])
                silence_id = frame.event.payload['silence_id']

                async def choose_silence(**kwargs):
                    prompt = kwargs['messages'][1]['content']
                    assert selection['candidate_id'] in prompt and silence_id in prompt
                    choice = json.dumps(dict(candidate_id=silence_id, rationale='Synthetic rationale for silence.'))
                    return SimpleNamespace(model='controlled/selector',
                        choices=[SimpleNamespace(message=SimpleNamespace(content=choice))])

                selector = execution.kernel('deliberation_synthesis').DeliberationSynthesizer(
                    store.journal, content_vault=store.vault)
                with patch.object(vault_type,'put_json',write_legacy if legacy else put_json):
                    silent = await selector.run(frame_id=selection['frame_id'],
                        gate_event_id=selection['exploration_gate_event_id'],
                        subject=affected_selection.event.subject, operation_id='feedback-select-silence',
                        call=choose_silence, attempts=1)
                silent_row = store.journal.get(silent.selection_event_id)
                assert silent_row.event.payload['candidate_id'] == silence_id
                silent_ref = silent_row.event.payload['content']['content_id']
                assert store.vault.resolve_json(silent_ref)['rationale']
                affected[silent_ref] = 'rationale'
                if erase_frames and not graph_only:
                    owner = store.configuration().subject
                    outcome = store.journal.read(event_type=feedback_module.EVENT)[0].event.event_id
                    dependencies = feedback_module._legacy_feedback_dependents(
                        store.journal, store.vault, owner, outcome)
                    assert set(affected).issubset(dependencies)
                    assert set(unrelated).isdisjoint(dependencies)
                    if legacy:
                        recorded = store.journal.read(event_type='deliberation.frame_lineage_recorded')
                        assert any(row.event.causation_id == frame.event.event_id for row in recorded)
                if erase_frames and not legacy:
                    assert frame.event.payload['feedback_lineage']['candidates'][selection['candidate_id']]
                print('CORE_NATIVE_FEEDBACK_NEXT_CYCLE_OK '+json.dumps(dict(
                    disposition=following.disposition,main_turn_association_provenance_preserved=True,
                    eligibility_clock_simulated=True,normal_cadence_wait_observed=True,
                    topic_signal_reached_intent=True,native_reply_excluded_from_author_and_review=True,
                    author_mode=feedback_probe.get('author_mode'),
                    actual_model_inference=False,quality_rounds=0)),flush=True)
            migration = feedback_module._legacy_feedback_dependents if erase_frames and not graph_only else lambda *_: ()
            with patch.object(feedback_module, '_legacy_feedback_dependents', migration):
                await exercise(core,loaded,binding,runner,source,entry,command,next_cycle)
            if graph_only:
                owner = store.configuration().subject
                outcome = store.journal.read(event_type=feedback_module.EVENT)[0].event.event_id
                remaining_lineage = feedback_module._legacy_feedback_dependents(
                    store.journal, store.vault, owner, outcome)
                assert set(affected).issubset(remaining_lineage)
            unavailable = execution.kernel('content_vault').ContentErasedError
            for content_id in affected:
                try:
                    store.vault.resolve_json(content_id)
                    raise AssertionError(f'dependent {affected[content_id]} remained readable')
                except unavailable:
                    pass
            for content_id, field in unrelated.items():
                document = store.vault.resolve_json(content_id)
                assert document if field == 'candidate-content' else document[field]
            print('HERMES_ALIVE_CORE_DEPENDENT_FEEDBACK_ERASURE_OK '+json.dumps(dict(
                legacy_writer_simulated=legacy, erased_artifacts=sorted(affected.values()),
                preserved_unrelated_artifacts=sorted(unrelated.values()))),flush=True)
        print('HERMES_ALIVE_CORE_SOURCE_READING_DEPTH_OK '+json.dumps(dict(stages=stages,
            requested_windows=[6000,15000],local_adapter_submissions=1,physical_sends=0,actual_model_inference=False,
            qualification_after_old_window_preserved=True,untitled_extracts_retained=True,
            final_facts_and_fit_exercised=True,source_led_revision_exercised=fit_revision,
            search_alignment=search_alignment,quality_rounds=0)),flush=True)
    finally:
        if manager is not None:manager.unload()
        core.reset_hermes_home_override(token)


if __name__=='__main__':
    from hermes_constants import get_default_hermes_root
    from pm.environments import install_state_dir
    owner=Path(os.environ['HERMES_HOME']).resolve()
    parent=None
    if (owner/'config.yaml').is_file() and (install_state_dir(core.args.core)/'facts.json').is_file():
        # A real installed Core owns its environment at the home root. Use its
        # ordinary profile namespace, not an unrelated data root that asks Core
        # to bootstrap a fresh dependency environment for every test invocation.
        parent=get_default_hermes_root()/'profiles';parent.mkdir(exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix='alive-core-source-depth-',dir=parent))
    succeeded=False
    try:
        asyncio.run(test(directory,fit_revision=os.environ.get('HERMES_ALIVE_TEST_FIT_REVISION')=='1',
                         revoke_after_capture=os.environ.get('HERMES_ALIVE_TEST_CAPTURE_REVOCATION')=='1',
                         search_alignment=os.environ.get('HERMES_ALIVE_TEST_SEARCH_ALIGNMENT','matches'),
                         claim_scope_conflict=os.environ.get('HERMES_ALIVE_TEST_CLAIM_SCOPE_CONFLICT')=='1'))
        succeeded=True
    finally:
        from hermes_state_registry import close_all_under
        close_all_under(directory)
        if succeeded:shutil.rmtree(directory)
        else:print('preserved failed synthetic profile: '+str(directory),file=sys.stderr)
