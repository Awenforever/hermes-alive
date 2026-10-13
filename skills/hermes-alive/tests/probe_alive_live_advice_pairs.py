#!/usr/bin/env python3
"""Paired synthetic opportunity decisions, not automatic learning or delivery."""

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ExperienceJournal, OpportunitySynthesizer, DiscoveryCandidate, DiscoveryOpportunityIngestor,
                          EventEnvelope, MemoryProjection, MemoryProposal, MemoryKind, MemoryAuthority)
from alive_kernel.events import _thaw_json
from alive_kernel.preference_learning import PreferenceAxis, PreferenceDirection
from alive_kernel.semantic_comparator import SemanticComparator
from run_alive_kernel_learning_context import seed


CASES = (
    {'id': 'permission-not-enthusiasm', 'axis': PreferenceAxis.TOPIC, 'key': 'city policy updates',
     'option': 'continue sharing', 'direction': PreferenceDirection.SUPPORT,
     'rationale': 'The user said city-policy updates may continue. This permits continuation but does not '
                  'express enjoyment or request higher frequency. No strong interest is established.',
     'title': 'Synthetic library opening-hours update',
     'summary': 'A synthetic public library announcement describes regular opening hours. It has no urgent '
                'deadline, event booking, safety warning or user-specific obligation.',
     'constraints': ['Do not turn tolerance into strong personal interest or increased posting frequency.',
                     'A small optional share, question or no candidate may all be defensible.']},
    {'id': 'meeting-not-permanent-ban', 'axis': PreferenceAxis.TIMING, 'key': 'availability',
     'option': 'send now', 'direction': PreferenceDirection.OPPOSE,
     'rationale': 'The user was in a meeting when the old message arrived and declined interruptions '
                  'on that occasion. That meeting is over. No permanent working-hours ban is expressed.',
     'title': 'Synthetic public repair demonstration',
     'summary': 'A synthetic notice offers a ten-minute public recording about mending torn clothing. '
                'It is available anytime and has no deadline or purchase requirement.',
     'constraints': ['Do not invent a permanent prohibition or assume the old meeting is still in progress.',
                     'Unknown current interest/availability may legitimately justify asking or silence.']},
    {'id': 'one-request-not-global-style', 'axis': PreferenceAxis.PRESENTATION, 'key': 'explanation detail',
     'option': 'detailed explanation', 'direction': PreferenceDirection.SUPPORT,
     'rationale': 'The user requested a detailed explanation for one complex technical topic. This was '
                  'situational, not a lasting preference for long messages about every simple notice.',
     'title': 'Synthetic public transit notice',
     'summary': 'A synthetic notice states that a public information page was updated. It gives no '
                'route disruption, action requirement, deadline or new factual details.',
     'constraints': ['Do not generalize one detailed-answer request to every simple notice.',
                     'Do not invent facts just to make a longer message.']},
)


DISCRIMINATING_CASES = (
    {'id': 'practical-update-without-intensity', 'axis': PreferenceAxis.TOPIC, 'key': 'local public updates',
     'option': 'continue sharing', 'direction': PreferenceDirection.SUPPORT,
     'rationale': 'The user permits local public updates but has not asked for higher posting frequency '
                  'or said they enjoy general municipal news. Specific practical relevance matters.',
     'profile': 'I cycle to work and find practical information about cycle-route access useful.',
     'positive': {'title': 'Public cycle-route access notice', 'summary': 'A synthetic public notice says the '
        'Riverpath cycle-route entrance will be closed for maintenance tomorrow from 08:00 to 10:00. '
        'The parallel Eastpath entrance remains open. No booking, payment or user obligation is required.'},
     'constraints': ['Do not infer enthusiasm for all municipal news or a higher posting frequency.',
                     'Useful route information should not be lost solely because interest in general news is unestablished.']},
    {'id': 'relevant-guide-after-past-interruption', 'axis': PreferenceAxis.TIMING, 'key': 'availability',
     'option': 'send now', 'direction': PreferenceDirection.OPPOSE,
     'rationale': 'The user declined one old message during a meeting. That meeting ended; no enduring '
                  'availability preference or work-hours ban was stated.',
     'profile': 'I repair worn clothes at home and appreciate practical repair instructions.',
     'positive': {'title': 'Public zipper-repair tutorial', 'summary': 'A synthetic public tutorial explains '
        'how to inspect a stuck zipper for trapped fabric and gently release it without pulling hard. '
        'It is free, can be read anytime, and requires no registration, purchase or deadline.'},
     'constraints': ['Do not treat the past meeting as a permanent ban or an ongoing event.',
                     'Respect current explicit availability without treating it as execution permission.']},
    {'id': 'simple-care-tip-after-dense-explanation', 'axis': PreferenceAxis.PRESENTATION, 'key': 'explanation detail',
     'option': 'detailed explanation', 'direction': PreferenceDirection.SUPPORT,
     'rationale': 'The user asked for detail in one past complex chemistry explanation. It does not '
                  'establish a global preference for long messages about simple practical notices.',
     'profile': 'I grow houseplants and appreciate practical information about basic plant care.',
     'positive': {'title': 'Public watering-check note', 'summary': 'A synthetic plant-care note recommends '
        'checking whether the top centimetre of potting mix is dry before watering rather than watering '
        'by a fixed calendar alone. It warns that individual species differ. No deadline or product is offered.'},
     'constraints': ['Do not inflate a simple note or invent details to satisfy a one-off old explanation request.',
                     'Preserve the species qualification instead of making a universal watering promise.']},
)


def explicit_context(journal, subject, predicate, value):
    source = journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic-public-fixture',
        actor=subject, subject=subject, payload={'fixture': True}))
    MemoryProjection(journal).append_proposal(MemoryProposal(subject=subject, kind=MemoryKind.PREFERENCE,
        predicate=predicate, value=value, authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(source.event.event_id,), confidence=1), actor=subject)


@dataclass(frozen=True)
class AdviceView:
    value: object
    flattened: bool

    @property
    def evidence_event_ids(self):
        return self.value.evidence_event_ids

    def to_prompt(self):
        result = self.value.to_prompt()
        if self.flattened:
            result.pop('evidence_notes')
        return result


class PairedReader:
    def __init__(self, reader, flattened):
        self.reader, self.flattened = reader, flattened

    def read(self, **kwargs):
        return tuple(AdviceView(value, self.flattened) for value in self.reader.read(**kwargs))


def normalized_input(value):
    # Only the note payload is manipulated. Wall-clock as_of inevitably differs
    # between sequential calls and is an explicit remaining nuisance variable.
    return {**value, 'as_of': '<sequential clock>', 'learned_advisory': [
        {k: v for k, v in item.items() if k != 'evidence_notes'} for item in value['learned_advisory']]}


async def exercise(args):
    logging.disable(logging.CRITICAL)
    from agent.auxiliary_client import async_call_llm
    import httpx
    args.output.mkdir(parents=True, exist_ok=False)
    scenario_set = getattr(args, 'scenario_set', 'initial')
    cases = CASES if scenario_set == 'initial' else DISCRIMINATING_CASES if scenario_set == 'discriminating' else None
    if cases is None:
        raise ValueError('unknown paired synthetic scenario set')
    report = {'logical_calls': 0, 'observed_async_http': [], 'sends': 0, 'pairs': [],
              'scenario_set': scenario_set,
              'semantic_accuracy_proven': False, 'utility_improvement_proven': False,
              'automatic_learning_authority': False,
              'reference_status': 'Provisional authored synthetic constraints, not human gold',
              'limitations': ['Same main model and prompt, one sample per arm; not a statistical benefit estimate.',
                              'The flattened arm removes only notes, not the shared mass-semantics label or prompt.',
                              'Sequential as_of differs; no actual user feedback, host delivery or longitudinal benefit.']}
    def save():
        temporary = args.output / 'report.json.tmp'
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(args.output / 'report.json')
    original = httpx.AsyncClient.send
    async def send(client, request, *a, **kw):
        if len(report['observed_async_http']) >= 18:
            raise RuntimeError('paired advice transport budget exhausted')
        item = {'host': request.url.host}
        report['observed_async_http'].append(item)
        try:
            response = await original(client, request, *a, **kw)
            item['status'] = response.status_code
            return response
        except BaseException as error:
            item['error_class'] = type(error).__name__
            raise
    httpx.AsyncClient.send = send
    try:
        for index, case in enumerate(cases):
            opaque = hashlib.sha256((scenario_set + ':' + case['id']).encode()).hexdigest()[:16]
            subject = 'user:synthetic-advice-' + opaque
            base = args.output / case['id'] / 'fixture'
            base.mkdir(parents=True)
            journal = ExperienceJournal(base / 'kernel.sqlite3')
            seed(journal, subject, case['direction'], axis=case['axis'], key=case['key'], option=case['option'],
                 rationale=case['rationale'])
            pair = {'case_id': case['id'], 'constraints': case['constraints'], 'arms': []}
            if scenario_set == 'discriminating':
                explicit_context(journal, subject, 'profile.interest', case['profile'])
                explicit_context(journal, subject, 'profile.availability', 'I am available to read a useful optional update now.')
                explicit_context(journal, subject, 'profile.content_boundary', 'Do not suggest shopping ads or sales pitches to me.')
                sources = [('relevant', case['positive']), ('advertisement', {'title': 'Sponsor product sale',
                    'summary': 'A synthetic commercial advertisement offers a paid accessory subscription. '
                               'It asks readers to buy before a promotional discount expires; it has no safety or practical notice.'})]
                if index % 2:
                    sources.reverse()
            else:
                sources = [('unspecified', case)]
            for number, (role, content) in enumerate(sources):
                item = DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic-public-fixture',
                    title=content['title'], summary=content['summary'], url='https://example.invalid/notice/' + opaque + '/' + str(number),
                    observed_at=datetime.now(timezone.utc)), subject=subject)
                if scenario_set == 'discriminating':
                    pair[role + '_agenda_item_id'] = item.agenda_item_id
            report['pairs'].append(pair)
            for arm in (('qualified', 'flattened') if index % 2 == 0 else ('flattened', 'qualified')):
                target = base.parent / arm
                shutil.copytree(base, target)
                copied = ExperienceJournal(target / 'kernel.sqlite3')
                interpreter = OpportunitySynthesizer(copied)
                interpreter.learning_reader = PairedReader(interpreter.learning_reader, arm == 'flattened')
                item = {'arm': arm}
                pair['arms'].append(item)
                before = tuple(copied.read(event_type='preference.observed'))
                async def call(**kw):
                    report['logical_calls'] += 1
                    if report['logical_calls'] > 6:
                        raise RuntimeError('paired advice logical budget exhausted')
                    item['input'] = json.loads(kw['messages'][1]['content'])
                    route = {}
                    response = await asyncio.wait_for(async_call_llm(**kw, route_info=route, timeout=40), timeout=50)
                    text, model, provider = SemanticComparator._response(response, route)
                    item.update(raw_response=text, actual_model=model, actual_provider=provider)
                    return response
                try:
                    result = await interpreter.run(subject=subject, operation_id='paired-advice:' + arm,
                        requested_model=args.model, call=call, timeout_seconds=55)
                    item.update(completed=True, rejected_count=result.rejected_count, receipt_event_id=result.receipt_event_id,
                        model_proposal_count=len(result.candidates) + result.rejected_count,
                        decision_observation=('model_empty' if not result.candidates and not result.rejected_count
                            else 'all_rejected' if not result.candidates else 'partial' if result.rejected_count else 'proposed'),
                        candidates=[{'authority': c.action.authority.value, 'kind': c.action.action_kind.value,
                                     'agenda_item_id': c.action.agenda_item_id,
                                     'content': _thaw_json(c.content), 'user_value': c.action.dimensions.user_value.value,
                                     'urgency': c.action.dimensions.urgency.value} for c in result.candidates])
                    assert all(c.action.authority.value == 'none' for c in result.candidates)
                except Exception as error:
                    item['error_class'] = type(error).__name__
                item['no_new_preference_signals'] = tuple(copied.read(event_type='preference.observed')) == before
                item['no_external_dispatch'] = not bool(copied.read(event_type='dispatch.externally_started'))
                save()
            inputs = [a.get('input') for a in pair['arms']]
            pair['matched_inputs_except_notes_and_clock'] = all(inputs) and normalized_input(inputs[0]) == normalized_input(inputs[1])
            save()
    finally:
        httpx.AsyncClient.send = original
        save()
    print(json.dumps({'logical_calls': report['logical_calls'], 'pairs': len(report['pairs']), 'sends': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live-models', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario-set', choices=('initial', 'discriminating'), default='initial')
    parser.add_argument('--model', help='An existing Hermes model selection only.')
    asyncio.run(exercise(parser.parse_args()))
