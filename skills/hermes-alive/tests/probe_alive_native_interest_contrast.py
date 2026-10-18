"""Opt-in profile contrast over the same public materials; no delivery authority.

Records real model behavior, not a model-generated satisfaction grade. The
operator supplies bounded public evidence and two synthetic preferences. Neither
this probe nor a successful response qualifies an autonomous production loop.
"""
import argparse
import asyncio
from contextlib import ExitStack
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live-models', action='store_true', required=True)
    parser.add_argument('--core', type=Path, required=True)
    parser.add_argument('--model-projection', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


async def exercise(args):
    sys.path[:0] = [str(args.core.resolve(strict=True)),
                   str(Path(__file__).resolve().parents[1] / 'hooks')]
    from hermes_constants import set_hermes_home_override, reset_hermes_home_override
    from agent.secret_scope import (set_secret_scope, reset_secret_scope,
                                   set_multiplex_context, reset_multiplex_context)
    from alive_kernel import (ExperienceJournal, DiscoveryOpportunityIngestor,
        DiscoveryCandidate, OpportunitySynthesizer, MemoryProjection, MemoryProposal,
        MemoryKind, MemoryAuthority, EventEnvelope, Sensitivity)
    from alive_kernel.native_host_caller import HostModelBinding, HostNativeCaller
    from alive_kernel.native_core_acquisition import CoreScopedModelAcquirer
    from alive_kernel.events import _thaw_json

    spec = json.loads(args.fixture.read_text(encoding='utf-8'))
    if (set(spec) != {'materials', 'preference_a', 'preference_b'}
            or not isinstance(spec['materials'], list) or not 2 <= len(spec['materials']) <= 24
            or any(not isinstance(spec[k], str) or not 1 <= len(spec[k]) <= 1500
                   for k in ('preference_a', 'preference_b'))):
        raise ValueError('bounded public materials and synthetic preferences required')
    for item in spec['materials']:
        if (not isinstance(item, dict) or set(item) != {'title', 'url', 'excerpt', 'priority_hint'}
                or any(not isinstance(item[k], str) or not 1 <= len(item[k]) <= 1500
                       for k in ('title', 'url', 'excerpt'))
                or not item['url'].startswith('https://')):
            raise ValueError('explicit public material required')
    if len({m['url'] for m in spec['materials']}) != len(spec['materials']):
        raise ValueError('distinct material identities required')
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    journal = ExperienceJournal(args.output / 'kernel' / 'experience.sqlite3')
    owner = 'user:synthetic-interest-contrast'
    ingestor = DiscoveryOpportunityIngestor(journal)
    identities = {}
    for item in spec['materials']:
        receipt = ingestor.ingest(DiscoveryCandidate(source='operator-public-evidence',
            title=item['title'], url=item['url'], summary=item['excerpt'],
            priority_hint=item['priority_hint'], observed_at=datetime.now(timezone.utc)), subject=owner)
        identities[receipt.agenda_item_id] = item['title']
    report = dict(fixture=spec, synthetic_owner=owner, logical_calls=0, cases=[],
        material_ids=identities, sends=0, semantic_accuracy_proven=False,
        comparison_is_not_full_chain=True)
    def save():
        path = args.output / 'report.json'
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        path.chmod(0o600)
    def preference(value):
        inbound = journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic-owner',
            actor=owner, subject=owner, payload={'synthetic': True}))
        proposal = MemoryProposal(subject=owner, kind=MemoryKind.PREFERENCE,
            predicate='profile.interest', value=value, authority=MemoryAuthority.USER_EXPLICIT,
            source_event_ids=(inbound.event.event_id,), confidence=1)
        MemoryProjection(journal).append_proposal(proposal, actor=owner)
        return proposal.proposal_id
    projection = json.loads(args.model_projection.read_text())
    host = args.output / 'host'; host.mkdir(mode=0o700)
    workers = args.output / 'workers'; workers.mkdir(mode=0o700)
    binding = HostModelBinding(owner, 'profile:synthetic', 'operation:interest-contrast', 'generation:1')
    save()
    with ExitStack() as stack:
        token = set_hermes_home_override(host); stack.callback(reset_hermes_home_override, token)
        token = set_multiplex_context(True); stack.callback(reset_multiplex_context, token)
        token = set_secret_scope(projection['environment'], profile_home=str(host))
        stack.callback(reset_secret_scope, token)
        acquire = CoreScopedModelAcquirer(profile_home=host, read_binding=lambda: binding,
            read_configuration=lambda: projection['config'],
            read_credential_names=lambda **_: tuple(projection['environment']),
            identity='Candid assistant in a synthetic-owner public-evidence experiment. No sending authority.')
        caller = HostNativeCaller(subject=owner, profile_id=binding.profile_id,
            operation_id=binding.operation_id, acquire=acquire, interpreter=sys.executable,
            core=args.core, private_root=workers, environment=dict(os.environ),
            timeout_seconds=185, max_calls=5)
        current_memory = None
        try:
            for phase in ('baseline', 'interest-a', 'corrected-b', 'reopened-b', 'withdrawn-b'):
                # All phases retain the same observations. Restart/withdrawal must
                # change memory reads, not secretly rebuild a favorable source pool.
                if phase in ('interest-a', 'corrected-b'):
                    if current_memory:
                        MemoryProjection(journal).forget_item(current_memory, actor=owner,
                            request_id='contrast-replace-a')
                    current_memory = preference(spec['preference_a' if phase == 'interest-a' else 'preference_b'])
                elif phase == 'withdrawn-b':
                    MemoryProjection(journal).forget_item(current_memory, actor=owner,
                        request_id='contrast-withdraw-b')
                journal = ExperienceJournal(journal.path)
                interpreter = OpportunitySynthesizer(journal)
                item = dict(phase=phase, calls=[]); report['cases'].append(item); save()
                async def call(**kwargs):
                    report['logical_calls'] += 1
                    invocation = dict(task=kwargs['task'], messages=kwargs['messages'])
                    item['calls'].append(invocation); save()
                    kwargs['timeout'] = 180
                    response = await caller(**kwargs)
                    invocation.update(actual_model=response.model,
                        completion_evidence=asdict(response.native_completion),
                        raw_response=response.choices[0].message.content)
                    save()
                    return response
                try:
                    result = await interpreter.run(subject=owner, operation_id='interest-contrast:' + phase,
                        call=call, timeout_seconds=180)
                    item.update(receipt_event_id=result.receipt_event_id, rejected_count=result.rejected_count,
                        candidates=[dict(candidate_id=c.action.candidate_id, content=_thaw_json(c.content),
                            authority=c.action.authority.value) for c in result.candidates],
                        abstentions=[asdict(a) for a in result.abstentions])
                    before = journal.last_sequence()
                    recovered = OpportunitySynthesizer(ExperienceJournal(journal.path)).load_completed(
                        subject=owner, operation_id='interest-contrast:' + phase)
                    item['replay_without_inference'] = recovered == result and journal.last_sequence() == before
                except Exception as error:
                    item['error_class'] = type(error).__name__
                    break  # Preserve the first failed phase; no blind repeated spend.
                save()
                if caller.pending:
                    break  # Do not start another phase while owned work is unresolved.
        finally:
            await caller.reap_pending(timeout_seconds=5)
            report.update(pending_workers=len(caller.pending),
                action_attempts=len(journal.read(event_type='action.attempted')),
                authorization_evaluations=len(journal.read(event_type='action.authorization_evaluated')),
                external_dispatches=len(journal.read(event_type='dispatch.externally_started')))
            save()
    print(json.dumps({k: report[k] for k in ('logical_calls', 'pending_workers', 'action_attempts',
        'authorization_evaluations', 'external_dispatches', 'sends')}))


if __name__ == '__main__':
    asyncio.run(exercise(arguments()))
