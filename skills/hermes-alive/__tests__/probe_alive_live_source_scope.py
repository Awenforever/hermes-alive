"""Opt-in source-scope diagnostic: synthetic inputs, actual models, no delivery."""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor,
    EventEnvelope, MemoryAuthority, MemoryKind, MemoryProjection, MemoryProposal)
from alive_kernel.events import _thaw_json
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer
from alive_kernel.source_support import SourceSupportReviewer
from alive_kernel.semantic_comparator import SemanticComparator
import httpx


# Fixture status belongs to the diagnostic envelope. Material qualifications below
# are varied source meanings, not a request to print 'synthetic' in every message.
CASES = (
    dict(id='attributed-listing',
        source='A volunteer repost claims a free bicycle-repair recording is available. '
               'The organizer has not confirmed the listing; availability is unverified.',
        distorted='The organizer has confirmed a free bicycle-repair recording is available.',
        scope_contrast='Found a free bicycle-repair recording you can watch.'),
    dict(id='limited-study',
        source='A preliminary non-peer-reviewed pilot study of 12 participants reports better '
               'bicycle brake-adjustment accuracy after a training video. It did not evaluate crash '
               'risk or long-term outcomes, and cannot establish a safety benefit.',
        distorted='A new study proves this bicycle training video reduces crashes.',
        scope_contrast='This training video improves bicycle brake-adjustment accuracy; it could be worth trying.'),
    dict(id='conditional-access',
        source='A bicycle maintenance workshop offers a free live session to registered students. '
               'Other participants pay $20. The archived recording is available only to paid members.',
        distorted='Everyone can watch the live bicycle workshop and its recording for free.',
        scope_contrast='Here is a free bicycle maintenance workshop with an archived recording.'),
    dict(id='ordinary-positive',
        source='The public library announces a free online bicycle-chain cleaning demonstration. '
               'No account is needed to watch. The notice gives a materials list and a video link.',
        distorted='The library requires a paid membership to watch its bicycle-chain demonstration.',
        scope_contrast='The public library has a free online bicycle-chain cleaning demonstration; no account needed.'),
)


async def run(output, *, model_call=None, contrasts_only=False, contrast_mode='direct'):
    if type(contrasts_only) is not bool or contrast_mode not in ('direct', 'scope'):
        raise ValueError('invalid source-scope diagnostic mode')
    if model_call is None:
        from agent.auxiliary_client import async_call_llm
        model_call = async_call_llm
    root = Path(output)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError('diagnostic output must be empty; preserve earlier evidence')
    report = dict(scope='synthetic source-scope interpretation and diagnostic contrasts only',
        contrast_mode=contrast_mode, contrasts_only=contrasts_only,
        logical_calls=0, http_requests=[], cases=[], sends=0, finished=False,
        semantic_quality_qualified=False, delivery_authority_granted=False)
    def save():
        path = root / 'report.json'
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        path.chmod(0o600)
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    original = httpx.AsyncClient.send
    async def track(client, request, *args, **kwargs):
        if len(report['http_requests']) >= 48:
            raise RuntimeError('diagnostic HTTP-start bound exhausted')
        item = dict(call=report['logical_calls'], host=request.url.host)
        report['http_requests'].append(item); save()
        try:
            result = await original(client, request, *args, **kwargs)
            item['status'] = result.status_code
            return result
        except Exception as error:
            item['error_class'] = type(error).__name__
            raise
        finally:
            save()
    def domain(model):
        # Actual configured family labels, not independence certification.
        name = model.casefold()
        return 'deepseek' if 'deepseek' in name else 'qwen' if 'qwen' in name else model
    httpx.AsyncClient.send = track
    try:
        for fixture in CASES:
            entry = dict(fixture=fixture, model_calls=[])
            report['cases'].append(entry); save()
            journal = ExperienceJournal(root / fixture['id'] / 'experience.sqlite3')
            ingestor = DiscoveryOpportunityIngestor(journal)
            source = ingestor.ingest(DiscoveryCandidate(source='public-notice-fixture',
                title=fixture['id'], summary=fixture['source'],
                url='https://example.invalid/' + fixture['id'],
                observed_at=datetime.now(timezone.utc)), subject='user:scope')
            statement = journal.append(EventEnvelope(event_type='conversation.inbound',
                source='synthetic-fixture', actor='user:scope', subject='user:scope', payload={'synthetic':True}))
            MemoryProjection(journal).append_proposal(MemoryProposal(kind=MemoryKind.PREFERENCE,
                subject='user:scope', predicate='profile.content_preferences',
                value='I enjoy practical bicycle maintenance, public tutorials and relevant research. '
                      'Useful attributed reports and tentative findings are welcome; do not require '
                      'certainty or ask me to reconfirm this interest.', authority=MemoryAuthority.USER_EXPLICIT,
                source_event_ids=(statement.event.event_id,), confidence=1), actor='user:scope')
            async def call(**kwargs):
                if report['logical_calls'] >= 16:
                    raise RuntimeError('diagnostic logical-call bound exhausted')
                report['logical_calls'] += 1
                row = dict(task=kwargs.get('task'), messages=deepcopy(kwargs['messages']))
                entry['model_calls'].append(row); save()
                try:
                    result = await model_call(**kwargs)
                    row.update(actual_model=getattr(result, 'model', None),
                               raw_output=result.choices[0].message.content)
                    return result
                except Exception as error:
                    row['error_class'] = type(error).__name__
                    raise
                finally:
                    save()
            synth = OpportunitySynthesizer(journal, content_vault=ingestor.vault)
            reviewer = SourceSupportReviewer(journal, content_vault=ingestor.vault)
            try:
                if contrasts_only:
                    # No implicit spending to regenerate cases already inspected.
                    generated = None
                else:
                    generated = await synth.run(subject='user:scope', operation_id='scope-generation', call=call)
                if generated is not None:
                    entry.update(candidates=[dict(id=c.action.candidate_id, content=_thaw_json(c.content))
                        for c in generated.candidates], abstentions=[a.reason for a in generated.abstentions],
                        rejected_count=generated.rejected_count)
                if generated is not None and generated.candidates:
                    candidate = generated.candidates[0]
                    receipt = await reviewer.run(subject='user:scope', interpretation_id='scope-generation',
                        candidate_id=candidate.action.candidate_id, operation_id='scope-review', call=call,
                        resolve_domain=domain, require_independence=False, protocol_recovery=True)
                    entry['generated_review'] = reviewer.verify_current(receipt.event_id,
                        subject='user:scope', interpretation_id='scope-generation',
                        candidate_id=candidate.action.candidate_id, allow_correlated=True)
            except Exception as error:
                entry['generation_review_error_class'] = type(error).__name__
            # Negative contrast is explicitly diagnostic, never a retained candidate
            # or a fabricated canonical review receipt. It still runs if generation abstains.
            snapshot = dict(evidence=[dict(event_id=source.observation_event_id,
                title=fixture['id'], url='https://example.invalid/' + fixture['id'],
                excerpt=fixture['source'], published_at=None, excerpt_may_be_truncated=False)],
                explicit_context=[], learned_advisory=[], recent_expression_history=[],
                recent_action_history=[], recent_feedback_context=[],
                candidate=dict(id='diagnostic-contrast', kind='share',
                    text=fixture['distorted' if contrast_mode=='direct' else 'scope_contrast']))
            try:
                route = {}
                raw = await asyncio.wait_for(call(task='alive_source_scope_contrast', model=None,
                    messages=[dict(role='system',content=reviewer.review_prompt),
                              dict(role='user',content=json.dumps(snapshot))],
                    route_info=route, temperature=0, max_tokens=2500, timeout=40), timeout=50)
                text, model, provider = SemanticComparator._response(raw, route)
                entry['contrast_review'] = dict(findings=reviewer.findings(text),
                    actual_model=model, provider=provider, diagnostic_only=True)
            except Exception as error:
                entry['contrast_error_class'] = type(error).__name__
            assert not journal.read(event_type='action.attempted')
            assert not journal.read(event_type='dispatch.started')
            save()
        report['finished'] = True
    finally:
        httpx.AsyncClient.send = original
        logging.disable(previous_logging)
        save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Empty private evidence directory')
    parser.add_argument('--contrasts-only', action='store_true')
    parser.add_argument('--contrast-mode', choices=('direct','scope'), default='direct')
    args = parser.parse_args()
    result = asyncio.run(run(args.output, contrasts_only=args.contrasts_only, contrast_mode=args.contrast_mode))
    print(json.dumps(dict(logical_calls=result['logical_calls'],
        http_starts=len(result['http_requests']), finished=result['finished'], sends=0)))
