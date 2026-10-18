"""One model-mediated correction, retained evidence, no retrying stale authority."""
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from copy import deepcopy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (ExperienceJournal, DiscoveryOpportunityIngestor, DiscoveryCandidate,
    OpportunitySynthesizer, OpportunitySynthesisError, Sensitivity, MemoryProjection,
    MemoryProposal, MemoryKind, MemoryAuthority, EventEnvelope)
from alive_kernel.content_vault import ContentReference


def response(text,model='synthetic/initial'):
    return SimpleNamespace(model=model,choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


async def exercise(root,mode):
    journal=ExperienceJournal(root/'experience.sqlite3')
    owner='user:synthetic'
    reader=DiscoveryOpportunityIngestor(journal)
    source=reader.ingest(DiscoveryCandidate(source='synthetic-fixture',title='Synthetic reference',
        summary='Synthetic public learning directory, no verified new event.',
        url='https://example.invalid/reference',observed_at=datetime.now(timezone.utc)),subject=owner)
    synth=OpportunitySynthesizer(journal,content_vault=reader.vault)
    memory=MemoryProjection(journal)
    inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor=owner,subject=owner,payload={'synthetic':True}))
    preference=MemoryProposal(subject=owner,kind=MemoryKind.PREFERENCE,predicate='profile.interest',
        value='Synthetic preference, not a sending grant.',authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(inbound.event.event_id,),confidence=1)
    memory.append_proposal(preference,actor=owner)
    invalid='{"candidates":[],"PRIVATE_UNPARSED":'
    proposal=dict(agenda_item_id=source.agenda_item_id,kind='share',text='SYNTHETIC_CORRECTED_BODY',
        topic='synthetic',dimensions={name:dict(value=.1 if name in ('risk','interruption_cost') else .8,
            reason='Synthetic evidence judgment, not real recipient benefit.')
            for name in ('user_value','urgency','novelty','confidence','risk','interruption_cost')})
    valid=json.dumps(dict(candidates=[proposal]))
    calls=[]
    async def call(**kwargs):
        calls.append(kwargs)
        if mode=='provider-error': raise ConnectionError('PRIVATE_PROVIDER_ERROR')
        if len(calls)==1:
            if mode=='revoked-before-repair':
                memory.forget_item(preference.proposal_id,actor=owner,request_id='withdraw-before')
            return response(invalid)
        data=json.loads(kwargs['messages'][1]['content'])
        assert data['invalid_response']==invalid
        assert data['original_evidence']==json.loads(calls[0]['messages'][1]['content'])
        assert 'single permitted protocol correction' in kwargs['messages'][0]['content']
        if mode=='twice-invalid': return response(invalid,'synthetic/corrector')
        if mode=='cancelled': raise asyncio.CancelledError()
        if mode=='timeout': await asyncio.sleep(2)
        if mode=='revoked-during-repair':
            memory.forget_item(preference.proposal_id,actor=owner,request_id='withdraw-during')
        return response(valid,'synthetic/corrector')
    args=dict(subject=owner,operation_id='protocol:'+mode,call=call,
        protocol_recovery=mode!='disabled',timeout_seconds=.1 if mode=='timeout' else 60)
    try:
        result=await synth.run(**args)
    except (OpportunitySynthesisError,asyncio.CancelledError) as error:
        assert mode!='success',type(error).__name__
        assert not journal.get('opportunity.synthesis:protocol:'+mode+':completed')
        failed=journal.get('opportunity.synthesis:protocol:'+mode+':failed')
        assert failed is not None
        if mode=='cancelled': assert isinstance(error,asyncio.CancelledError)
        if mode=='timeout': assert failed.event.payload['error_class']=='TimeoutError'
        expected=1 if mode in ('provider-error','disabled','revoked-before-repair') else 2
        assert len(calls)==expected,(mode,len(calls))
        try: await synth.run(**args)
        except OpportunitySynthesisError: pass
        else: raise AssertionError('terminal failure was respent')
        assert len(calls)==expected
    else:
        assert mode=='success' and len(calls)==2
        assert result.actual_model=='synthetic/corrector' and len(result.candidates)==1
        assert result.candidates[0].action.authority.value=='none'
        assert result.candidates[0].content['operation']['text'].startswith('SYNTHETIC_CORRECTED_BODY')
        before=journal.last_sequence()
        recovered=OpportunitySynthesizer(ExperienceJournal(journal.path),content_vault=reader.vault).load_completed(
            subject=owner,operation_id='protocol:'+mode)
        assert recovered==result and journal.last_sequence()==before and len(calls)==2
        receipt=journal.get(result.receipt_event_id)
        assert receipt.event.payload['protocol_recovered'] is True
        correction=journal.get('opportunity.synthesis:protocol:'+mode+':protocol-recovery')
        ref=ContentReference.from_event_payload(correction.event.payload['content'])
        preserved=reader.vault.resolve_json(ref.content_id,expected_subject=owner,
            expected_purpose='opportunity.protocol-failure',expected_sensitivity=Sensitivity.PRIVATE)
        assert preserved==dict(invalid_response=invalid,initial_model='synthetic/initial')
        # Recovery labels alone cannot turn a different/suppressed history valid.
        original_get=journal.get
        for altered in (replace(correction.event,subject='user:foreign'),
                        replace(correction.event,payload={**dict(correction.event.payload),
                            'request_prompt_digest':'different'}),
                        replace(receipt.event,payload={**dict(receipt.event.payload),'protocol_recovered':False})):
            target=correction if altered.event_id==correction.event.event_id else receipt
            def damaged_read(event_id):
                return replace(target,event=altered) if event_id==target.event.event_id else original_get(event_id)
            with patch.object(journal,'get',side_effect=damaged_read):
                try: synth.load_completed(subject=owner,operation_id='protocol:'+mode)
                except OpportunitySynthesisError: pass
                else: raise AssertionError('altered recovery evidence accepted')
    corrections=journal.read(event_type='opportunity.synthesis_protocol_recovery')
    assert len(corrections)==(0 if mode in ('provider-error','disabled','revoked-before-repair') else 1)
    assert not journal.read(event_type='action.attempted')
    for path in root.glob('experience.sqlite3*'):
        assert b'PRIVATE_UNPARSED' not in path.read_bytes()
        assert b'SYNTHETIC_CORRECTED_BODY' not in path.read_bytes()


async def structure(root,mode):
    journal=ExperienceJournal(root/'experience.sqlite3'); owner='user:synthetic'
    reader=DiscoveryOpportunityIngestor(journal)
    source=reader.ingest(DiscoveryCandidate(source='synthetic-fixture',title='Synthetic public resource',
        summary='A synthetic resource; no promise of eligibility.',url='https://example.invalid/resource',
        observed_at=datetime.now(timezone.utc)),subject=owner)
    synth=OpportunitySynthesizer(journal,content_vault=reader.vault)
    memory=MemoryProjection(journal)
    inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor=owner,subject=owner,payload={'synthetic':True}))
    preference=MemoryProposal(subject=owner,kind=MemoryKind.PREFERENCE,predicate='profile.interest',
        value='Synthetic structural recovery preference.',authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(inbound.event.event_id,),confidence=1)
    memory.append_proposal(preference,actor=owner)
    proposal=dict(agenda_item_id=source.agenda_item_id,kind='share',text='PRIVATE_VALID_MEANING',topic='synthetic',
        dimensions={k:dict(value=.5,reason='Synthetic judgment') for k in (
            'user_value','urgency','novelty','confidence','risk','interruption_cost')},
        communication_plan=dict(version=2,recipient_goal='Share a public resource',speech_act='share',
            contents=[dict(kind='fact',text='Synthetic public resource.')],behavior_constraints=[]))
    broken=deepcopy(proposal)
    broken['communication_plan']['contents'][0]['protected_literals']=['PRIVATE_ABSENT_LITERAL']
    initial=dict(candidates=[broken])
    if mode=='envelope': initial['unexpected_envelope_field']=True
    if mode=='foreign-id': initial['candidates'][0]['agenda_item_id']='foreign:unavailable'
    if mode=='non-action': initial=dict(candidates=[proposal],abstentions='invalid')
    if mode=='mixed': initial=dict(candidates=[broken,proposal])
    if mode=='empty': initial=dict(candidates=[])
    calls=[]
    async def call(**kwargs):
        calls.append(kwargs)
        if mode=='provider-error': raise ConnectionError('PRIVATE_PROVIDER_ERROR')
        if len(calls)==1:
            document=initial
            if mode=='revoked-before-repair':
                memory.forget_item(preference.proposal_id,actor=owner,request_id='structural-withdraw-before')
        else:
            data=json.loads(kwargs['messages'][1]['content'])
            assert data['failure_diagnostics'] and data['invalid_response']==json.dumps(initial)
            assert data['original_evidence']==json.loads(calls[0]['messages'][1]['content'])
            if mode=='cancelled': raise asyncio.CancelledError()
            if mode=='timeout': await asyncio.sleep(2)
            if mode=='revoked-during-repair':
                memory.forget_item(preference.proposal_id,actor=owner,request_id='structural-withdraw-during')
            if mode=='twice-invalid': document=initial
            elif mode=='erased': document=dict(candidates=[])
            elif mode=='explicit-abstention':
                document=dict(candidates=[],abstentions=[dict(agenda_item_id=source.agenda_item_id,
                    reason='The source does not establish sufficient recipient value.')])
            else: document=dict(candidates=[proposal])
        return response(json.dumps(document),'synthetic/structure')
    args=dict(subject=owner,operation_id='structure:'+mode,call=call,recipient_meaning=True,
        protocol_recovery=mode!='disabled',timeout_seconds=.1 if mode=='timeout' else 60)
    if mode in ('twice-invalid','erased','provider-error','revoked-before-repair',
                'revoked-during-repair','cancelled','timeout'):
        try: await synth.run(**args)
        except (OpportunitySynthesisError,asyncio.CancelledError) as error:
            if mode=='cancelled': assert isinstance(error,asyncio.CancelledError)
        else: raise AssertionError('invalid/unassessed correction became a success')
        expected=1 if mode in ('provider-error','revoked-before-repair') else 2
        assert len(calls)==expected
        failed=journal.get('opportunity.synthesis:structure:'+mode+':failed')
        assert failed is not None
        if mode=='timeout': assert failed.event.payload['error_class']=='TimeoutError'
        try: await synth.run(**args)
        except OpportunitySynthesisError: pass
        else: raise AssertionError('terminal structural failure was respent')
        assert len(calls)==expected
    else:
        result=await synth.run(**args)
        assert len(calls)==(1 if mode in ('mixed','empty','disabled') else 2)
        assert len(result.candidates)==(0 if mode in ('empty','disabled','explicit-abstention') else 1)
        before=journal.last_sequence()
        assert OpportunitySynthesizer(journal,content_vault=reader.vault).load_completed(
            subject=owner,operation_id='structure:'+mode)==result
        assert journal.last_sequence()==before
        if len(calls)==2:
            recovery=journal.get('opportunity.synthesis:structure:'+mode+':protocol-recovery')
            assert recovery.event.payload['error_class']=='OpportunityStructureError'
            ref=ContentReference.from_event_payload(recovery.event.payload['content'])
            saved=reader.vault.resolve_json(ref.content_id,expected_subject=owner,
                expected_purpose='opportunity.protocol-failure')
            assert saved['invalid_response']==json.dumps(initial) and saved['failure_diagnostics']
            if mode=='success':
                # Even an authenticated artifact/label cannot declare a valid
                # original invalid. Recovery proof must rerun pure admission.
                forged=reader.vault.put_json({**saved,'invalid_response':json.dumps(dict(candidates=[proposal]))},
                    subject=owner,purpose='opportunity.protocol-failure')
                changed=replace(recovery.event,payload={**dict(recovery.event.payload),'content':forged.to_event_payload()})
                original_get=journal.get
                def changed_get(event_id):
                    return replace(recovery,event=changed) if event_id==recovery.event.event_id else original_get(event_id)
                with patch.object(journal,'get',side_effect=changed_get):
                    try: synth.load_completed(subject=owner,operation_id='structure:'+mode)
                    except OpportunitySynthesisError: pass
                    else: raise AssertionError('fake structural failure accepted')
        if mode=='mixed': assert result.rejected_count==1
        if mode=='explicit-abstention': assert len(result.abstentions)==1
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')
    for path in root.glob('experience.sqlite3*'):
        assert b'PRIVATE_ABSENT_LITERAL' not in path.read_bytes()
        assert b'PRIVATE_VALID_MEANING' not in path.read_bytes()


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-protocol-recovery-') as folder:
        for mode in ('success','twice-invalid','disabled','provider-error','revoked-before-repair',
                     'revoked-during-repair','cancelled','timeout'):
            asyncio.run(exercise(Path(folder)/mode,mode))
        for mode in ('success','envelope','foreign-id','non-action','mixed','empty','disabled',
                     'twice-invalid','erased','explicit-abstention','provider-error',
                     'revoked-before-repair','revoked-during-repair','cancelled','timeout'):
            asyncio.run(structure(Path(folder)/('structure-'+mode),mode))
    print('HERMES_ALIVE_OPPORTUNITY_PROTOCOL_RECOVERY_OK')
