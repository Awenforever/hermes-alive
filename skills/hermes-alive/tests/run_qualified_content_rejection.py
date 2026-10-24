"""Current negative proof is not unknown work, authority or a source dismissal."""
import asyncio
from dataclasses import replace
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'hooks'),str(Path(__file__).resolve().parent)]
from alive_kernel import ExperienceJournal,AutonomyPolicyProjection,PolicyContext
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
from alive_kernel.content_vault import ContentReference
from run_alive_kernel_expression_runtime import scenario


async def exercise(root,mode):
    journal=ExperienceJournal(root/'experience.sqlite3')
    runtime=AutonomousCycleRuntime(journal)
    policy=AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject='user:test',actor='user:test',expected_revision=0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='synthetic-policy'))
    host=AutonomousHostRuntime(runtime,subject='user:test',configuration_id='synthetic-rejection-proof')
    cycle=host.open_cycle()
    _,params,_=await scenario(root,'share',return_ready=True,grounding=True,single_family=True,
        semantic_speech_shift=mode=='semantic',operation_id=cycle.operation_id)
    calls=[]
    async def source(**kw):
        calls.append(kw['task'])
        assert kw['task']=='alive_source_support'
        kw['route_info']['provider']='synthetic-provider'
        verdict='supported' if mode=='supported' else 'uncertain' if mode=='uncertain' else 'unsupported'
        value=dict(verdict=verdict,unsupported_claims=['Synthetic unsupported relation.'] if verdict=='unsupported' else [],
            uncertainties=['Synthetic unresolved relation.'] if verdict=='uncertain' else [],reason='Synthetic review.')
        return NS(model='synthetic/renderer',choices=[NS(message=NS(content=json.dumps(value)))])
    expression={k:v for k,v in params.items() if k not in ('subject','operation_id','policy_context')}
    expression.update(call=source,allow_repair=False)
    result=await host.step(dict(expression_parameters=expression,resolve_binding=lambda _:None))
    if mode=='supported':
        assert result.disposition=='shadow_selected' and result.content_rejection is None
        return
    assert result.disposition=='content_review_attention'
    witness=result.content_rejection
    assert witness is not None,'current completed negative proof was not classified: '+mode
    assessed=result.quality_assessment
    assert witness.subject=='user:test' and witness.operation_id==cycle.operation_id
    assert witness.expression_event_id==result.expression.expression_event_id
    assert witness.review_event_id==assessed.final_review_event_id
    assert witness.source_event_ids and witness.valid_until>datetime.now(timezone.utc)
    closed=journal.read(event_type='autonomous.host.closed')[-1]
    assert host._validate(closed.event)['content_rejection']==witness.to_event_payload()
    parameters={**expression,'subject':'user:test','operation_id':cycle.operation_id,
        'policy_context':PolicyContext(can_interrupt=True)}
    before=(journal.last_sequence(),len(calls))
    verify=lambda value=assessed,options=parameters:runtime.preparation.rejection_witness(value,options)
    assert verify()==witness
    assert verify(options={**parameters,'subject':'user:other'}) is None
    assert verify(options={**parameters,'operation_id':'foreign-cycle'}) is None
    assert verify(replace(assessed,expression=replace(assessed.expression,text='Foreign unreviewed wording.'))) is None
    assert verify(replace(assessed,expression=replace(assessed.expression,
        planning=replace(assessed.expression.planning,selection_event_id='foreign-selection')))) is None
    assert verify(replace(assessed,quality_disposition='final_repair_unavailable')) is None
    assert verify(replace(assessed,final_review_event_id='missing-review')) is None
    source.pending=({'phase':'synthetic_unknown_child'},)
    assert verify() is None,'a pending physical model operation became safe content rejection'
    source.pending=()
    assert verify()==witness
    assert (journal.last_sequence(),len(calls))==before,'proof inspection created work or journal events'
    for foreign in (replace(witness,subject='user:other'),replace(witness,operation_id='foreign-cycle')):
        try:host.close_cycle(cycle,replace(result,content_rejection=foreign))
        except ValueError:pass
        else:raise AssertionError('foreign rejection scope reached a closed cycle')
    # Source truth and availability were not dismissed/snoozed by classification.
    retained=runtime.preparation.expression.planning.synth.reader.active_evidence(subject='user:test',
        clearance='private',limit=32,observation_event_ids=witness.source_event_ids)
    assert tuple(e.observation_event_id for e in retained)==witness.source_event_ids
    for event_id in witness.source_event_ids:
        original=journal.get(event_id)
        ref=ContentReference.from_event_payload(original.event.payload['content'])
        runtime.preparation.vault.erase_item(ref.content_id)
    assert verify() is None,'erased source ancestry remained a qualified negative proof'
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_delivered')


with tempfile.TemporaryDirectory(prefix='alive-qualified-rejection-') as temporary:
    for mode in ('semantic','unsupported','uncertain','supported'):
        print('QUALIFIED_REJECTION_CASE='+mode,flush=True)
        asyncio.run(exercise(Path(temporary)/mode,mode))
print('HERMES_ALIVE_QUALIFIED_CONTENT_REJECTION_OK')
