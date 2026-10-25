"""One review-contract correction, not retries for valid negative judgments."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from functools import partial
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from run_alive_kernel_expression_runtime import scenario
from alive_kernel import ExperienceJournal,DiscoveryOpportunityIngestor,DiscoveryCandidate
from alive_kernel.content_vault import ContentReference
from alive_kernel.expression_runtime import ExpressionRuntime
from alive_kernel.semantic_review import SemanticReviewError
from alive_kernel.semantic_comparator import SemanticComparator


async def exercise(root,mode):
    journal,original,_=await scenario(root,'share',return_ready=True)
    runtime=ExpressionRuntime(journal)
    if mode=='disabled':
        runtime.comparator.run=partial(runtime.comparator.run,protocol_recovery=False)
    calls=[]
    good=None
    invalid=None
    first_input=None
    def change_source():
        DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic public fixture',
            title='Repair workshop',summary='Material source correction invalidates the retained interpretation.',
            url='https://example.invalid/workshop',observed_at=datetime.now(timezone.utc)),subject='user:test')
    async def call(**kwargs):
        nonlocal good,invalid,first_input
        if kwargs['task']!='alive_semantic_review':return await original['call'](**kwargs)
        calls.append(kwargs)
        kwargs['route_info']['provider']='synthetic-review-provider'
        if len(calls)==1:
            first_input=json.loads(kwargs['messages'][1]['content'])
            good=dict(atom_reviews=[dict(atom_id=a['atom_id'],preserved=True,risks=[])
                for a in first_input['meaning']['atoms']],added_claims_detected=False,
                speech_act_preserved=True,protected_literals_preserved=True)
            broken=deepcopy(good)
            broken['atom_reviews'][0]['risks']=['omission']
            if mode=='json':invalid='{"PRIVATE_REVIEW_FAILURE":'
            elif mode=='oversize':invalid='PRIVATE_REVIEW_FAILURE'+'x'*70000
            else:
                broken['PRIVATE_REVIEW_FAILURE']='only encrypted'
                # The contradiction still matters when the outer schema is valid.
                if mode not in ('envelope',):broken.pop('PRIVATE_REVIEW_FAILURE')
                if mode=='duplicate':broken['atom_reviews']=[good['atom_reviews'][0]]*len(good['atom_reviews'])
                if mode=='unknown':
                    broken=deepcopy(good);broken['atom_reviews'][0]['atom_id']='foreign-atom'
                if mode=='flags':broken={**good,'speech_act_preserved':'true'}
                invalid=json.dumps(broken)
            if mode=='valid-negative':
                broken=deepcopy(good);broken['atom_reviews'][0].update(preserved=False,risks=['omission'])
                invalid=json.dumps(broken)
            if mode=='provider-error':raise ConnectionError('PRIVATE_REVIEW_FAILURE')
            if mode=='revoke-before-repair':change_source()
            output=invalid
        else:
            feedback=json.loads(kwargs['messages'][1]['content'])
            assert feedback['original_evidence']==first_input
            assert feedback['invalid_review']==invalid
            assert kwargs['timeout']<calls[0]['timeout']
            assert 'single permitted protocol correction' in kwargs['messages'][0]['content']
            if mode=='cancel':raise asyncio.CancelledError()
            if mode=='timeout':await asyncio.sleep(2)
            if mode=='revoke-during-repair':change_source()
            if mode=='erase-during-repair':
                recovery=journal.read(event_type='semantic.comparison_protocol_recovery')[-1]
                ref=ContentReference.from_event_payload(recovery.event.payload['content'])
                runtime.store.content_vault.erase_item(ref.content_id)
            if mode=='twice-invalid':output=invalid
            else:
                fixed=deepcopy(good)
                if mode=='corrected-negative':fixed['atom_reviews'][0].update(preserved=False,risks=['omission'])
                output=json.dumps(fixed)
        return SimpleNamespace(model='synthetic/reviewer',choices=[SimpleNamespace(message=SimpleNamespace(content=output))])
    params={**original,'operation_id':'recovery','call':call}
    if mode=='timeout':params['model_timeout_seconds']=1
    failing=mode in ('provider-error','revoke-before-repair','revoke-during-repair','erase-during-repair',
                    'cancel','timeout','twice-invalid','disabled','oversize')
    try:result=await runtime.run(**params)
    except (ValueError,asyncio.CancelledError) as error:
        assert failing,(mode,type(error).__name__)
        if mode=='cancel':assert isinstance(error,asyncio.CancelledError)
    else:
        assert not failing,mode
        assert result.review_disposition==('rejected' if mode in ('valid-negative','corrected-negative') else 'shadow_eligible')
        before=journal.last_sequence();spent=len(calls)
        async def forbidden(**_):raise AssertionError('completed operation respent model work')
        assert await ExpressionRuntime(ExperienceJournal(journal.path)).run(**{**params,'call':forbidden})==result
        assert journal.last_sequence()==before and len(calls)==spent
        record=journal.get(result.review_event_id)
        assert runtime.store.verify_review(record)
        corrections=journal.read(event_type='semantic.comparison_protocol_recovery')
        if mode!='valid-negative':
            assert len(corrections)==1
            correction=corrections[0]
            assert record.event.payload['protocol_recovery_event_id']==correction.event.event_id
            ref=ContentReference.from_event_payload(correction.event.payload['content'])
            saved=runtime.store.content_vault.resolve_json(ref.content_id,expected_subject='user:test',
                expected_purpose='semantic.protocol-failure')
            assert saved['invalid_review']==invalid and saved['original_evidence']==first_input
            # A vault-authenticated artifact is not proof that its valid original
            # was actually malformed. A stripped marker cannot hide the correction.
            if mode=='success':
                original_get=journal.get
                forged=runtime.store.content_vault.put_json({**saved,'invalid_review':json.dumps(good)},
                    subject='user:test',purpose='semantic.protocol-failure',retention_until=ref.retention_until)
                altered=replace(correction.event,payload={**dict(correction.event.payload),'content':forged.to_event_payload()})
                def damaged(event_id):
                    return replace(correction,event=altered) if event_id==correction.event.event_id else original_get(event_id)
                with patch.object(journal,'get',side_effect=damaged):
                    assert runtime.store.verify_review(record) is None
                for changed in (replace(correction.event,subject='user:foreign'),
                                replace(correction.event,causation_id='foreign-candidate')):
                    def wrong(event_id):
                        return replace(correction,event=changed) if event_id==correction.event.event_id else original_get(event_id)
                    with patch.object(journal,'get',side_effect=wrong):
                        assert runtime.store.verify_review(record) is None
                stripped=dict(record.event.payload);stripped.pop('protocol_recovery_event_id')
                stripped['integrity_authenticator']=runtime.store.protector.authenticate_json('message.semantic_review.v1',
                    runtime.store._authentication_document('message.semantic_review.v1',stripped))
                assert runtime.store.verify_review(replace(record,event=replace(record.event,payload=stripped))) is None
                runtime.store.content_vault.erase_item(ref.content_id)
                assert runtime.store.verify_review(record) is None
    expected=1 if mode in ('provider-error','revoke-before-repair','valid-negative','disabled','oversize') else 2
    assert len(calls)==expected,(mode,len(calls))
    if failing:
        spent=len(calls)
        try:await ExpressionRuntime(ExperienceJournal(journal.path)).run(**params)
        except ValueError:pass
        else:raise AssertionError('terminal semantic failure reused provider')
        assert len(calls)==spent
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')
    for path in root.rglob('*.sqlite3*'):
        assert b'PRIVATE_REVIEW_FAILURE' not in path.read_bytes()


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-semantic-protocol-') as folder:
        for mode in ('success','json','envelope','duplicate','unknown','flags','valid-negative','corrected-negative',
                     'provider-error','revoke-before-repair','revoke-during-repair','erase-during-repair',
                     'cancel','timeout','twice-invalid','disabled','oversize'):
            asyncio.run(exercise(Path(folder)/mode,mode))
    print('HERMES_ALIVE_SEMANTIC_PROTOCOL_RECOVERY_OK')
