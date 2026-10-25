"""Read-only per-source retry view; original facts stay available to grounding."""
import asyncio
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile

from run_qualified_content_rejection import make_rejection
from alive_kernel import AutonomyPolicyProjection,DiscoveryCandidate,DiscoveryOpportunityIngestor,EventEnvelope
from alive_kernel.rejection_eligibility import RejectionEligibility
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleResult


async def exercise(root):
    journal,runtime,host,cycle,params,expression,result,calls=await make_rejection(root,'unsupported',retry_window=3600)
    view=RejectionEligibility(host)
    before=(journal.last_sequence(),len(calls))
    held=view.read(expression)
    assert len(held.held)==1 and held.history_complete
    assert held.excluded_urls==('https://example.invalid/workshop',)
    record=journal.read(event_type='autonomous.host.closed')[-1]
    deadline=datetime.fromisoformat(record.event.payload['content_rejection_retry_until'])
    assert held.held[0].until==deadline
    assert view.read(expression)==held
    assert not view.read(expression,limit=1).history_complete
    # Recreate host/controller without creating a new grant or history entry.
    from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
    reopened=AutonomousHostRuntime(runtime,subject=host.subject,configuration_id=host.configuration_id)
    assert RejectionEligibility(reopened).read(expression)==held
    changed=AutonomousHostRuntime(runtime,subject=host.subject,configuration_id='different-config')
    assert not RejectionEligibility(changed).read(expression).held
    assert (journal.last_sequence(),len(calls))==before
    assert not RejectionEligibility(host,clock=lambda:deadline+timedelta(seconds=1)).read(expression).held
    # Actual authenticated empty host completions, not model/transport claims.
    # Their volume must not change the still-live rejection lookup horizon.
    for _ in range(70):
        tick=host.open_cycle()
        host.close_cycle(tick,AutonomousCycleResult('waiting_for_change',dict(next_after_sequence=0)))
    assert view.read(expression)==held
    # Other sources remain ordinary candidate inputs. No source state changed.
    sources=runtime.preparation.expression.planning.synth.reader.active_evidence(subject='user:test',clearance='private',limit=32)
    assert held.held[0].observation_event_id in {s.observation_event_id for s in sources}
    ingest=DiscoveryOpportunityIngestor(journal,content_vault=runtime.preparation.vault)
    unrelated=ingest.ingest(DiscoveryCandidate(source='synthetic separate source',title='Other public topic',
        summary='Different public evidence.',url='https://example.invalid/other',observed_at=datetime.now(timezone.utc)),
        subject='user:test')
    assert view.read(expression).excluded_urls==held.excluded_urls
    assert unrelated.observation_event_id not in {s.observation_event_id for s in held.held}
    reader=runtime.preparation.expression.planning.synth.reader
    assert reader.active_evidence(subject='user:test',clearance='private',limit=1)[0].observation_event_id==held.held[0].observation_event_id
    eligible=reader.candidate_evidence(subject='user:test',clearance='private',limit=1,excluded_urls=held.excluded_urls)
    assert tuple(s.observation_event_id for s in eligible)==(unrelated.observation_event_id,), 'exclusion happened after LIMIT'
    assert reader.active_evidence(subject='user:test',clearance='private',limit=1)[0].observation_event_id==held.held[0].observation_event_id
    assert reader.candidate_evidence(subject='user:test',clearance='private',limit=32)==reader.active_evidence(
        subject='user:test',clearance='private',limit=32)
    # A new version of the actual held source invalidates its old negative proof.
    ingest.ingest(DiscoveryCandidate(source='synthetic public fixture',title='Repair workshop',
        summary='A substantive changed public source.',url='https://example.invalid/workshop',
        observed_at=datetime.now(timezone.utc)),subject='user:test')
    assert not view.read(expression).held
    assert len(calls)==before[1]
    journal.append(replace(record.event,event_id='synthetic-forged-completion-alias'))
    try:view.read(expression)
    except ValueError:pass
    else:raise AssertionError('unauthenticated completion identity became eligible history')


async def owner_change(root,kind):
    journal,runtime,host,cycle,params,expression,result,calls=await make_rejection(root,'semantic',retry_window=3600)
    view=RejectionEligibility(host)
    assert view.read(expression).held
    if kind=='inbound':
        journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',actor='transport:synthetic-inbound',
            subject='user:test',payload=dict(synthetic=True)))
    elif kind=='scope':
        assert runtime.preparation.restore_rejection(result.content_rejection.to_event_payload(),
            {**expression,'subject':'user:test','operation_id':cycle.operation_id,'sensitivity':'public'}) is None
        return
    else:
        policy=AutonomyPolicyProjection(journal);current=policy.current('user:test')
        policy.apply(policy.append_update(subject='user:test',actor='user:test',expected_revision=current.revision,
            enabled=kind!='paused',context=current.context,operation_id='synthetic-policy-change'))
    if kind=='paused':
        try:view.read(expression)
        except ValueError:pass
        else:raise AssertionError('paused owner obtained an eligibility capture')
        return
    assert not view.read(expression).held


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-rejection-eligibility-') as temporary:
        root=Path(temporary)
        print('REJECTION_ELIGIBILITY_CASE=sources',flush=True)
        asyncio.run(exercise(root/'sources'))
        for kind in ('inbound','policy','paused','scope'):
            print('REJECTION_ELIGIBILITY_CASE='+kind,flush=True)
            asyncio.run(owner_change(root/kind,kind))
    print('HERMES_ALIVE_REJECTION_ELIGIBILITY_OK')
