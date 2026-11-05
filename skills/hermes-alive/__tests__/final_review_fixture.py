"""Controlled HTTP/model output with no shadow-kernel or provider import."""


def controlled_final_findings(snapshot, *, factual='supported', fit='fits', reason='Synthetic assessment.'):
    scope = snapshot.get('expression_binding', {}).get('final_assessment_scope')
    if scope in ('factual-support-and-communication-fit-v6', 'factual-support-and-communication-fit-v7',
                 'factual-support-and-communication-fit-v8'):
        witnesses = []
        if factual == 'supported':
            passage = next(p for source in snapshot['evidence'] for p in source['passages'] if p['text'].strip())
            witnesses = [{'claim': snapshot['candidate']['text'][:200], 'passage_id': passage['passage_id']}]
        result = dict(facts=factual, fact_reason=reason, fit=fit, fit_reason=reason,
                      recipient_evidence=[], source_witnesses=witnesses)
        if scope in ('factual-support-and-communication-fit-v7', 'factual-support-and-communication-fit-v8'):
            result.update(search_alignment='matches' if snapshot.get('approved_search_queries') else 'not_applicable',
                          scope_reason='Synthetic source answers the supplied synthetic search, if present.')
        return result
    if scope in ('factual-support-and-communication-fit-v1', 'factual-support-and-communication-fit-v2',
                 'factual-support-and-communication-fit-v3', 'factual-support-and-communication-fit-v4',
                 'factual-support-and-communication-fit-v5'):
        result = {'factual_support': {'assessment': factual, 'reason': reason},
                'communication_fit': {'assessment': fit, 'reason': reason, 'recipient_evidence': []}}
        if scope == 'factual-support-and-communication-fit-v5':
            passage = next(p for source in snapshot['evidence'] for p in source['passages'] if p['text'].strip())
            result['source_witnesses'] = [{'claim': snapshot['candidate']['text'][:200],
                'passage_id': passage['passage_id']}] if factual == 'supported' else []
        elif scope == 'factual-support-and-communication-fit-v4':
            source = next(item for item in snapshot['evidence'] if item['passages'][0].strip())
            result['source_witnesses'] = [{'claim': snapshot['candidate']['text'][:200],
                'source_event_id': source['event_id'], 'passage': 1}] if factual == 'supported' else []
        elif scope == 'factual-support-and-communication-fit-v3':
            source = next(item for item in snapshot['evidence'] if item['excerpt'].strip())
            result['source_witnesses'] = [{'claim': snapshot['candidate']['text'][:200],
                'source_event_id': source['event_id'], 'quote': source['excerpt'][:200]}] if factual == 'supported' else []
        return result
    verdict = ('unsupported' if factual == 'unsupported' or fit == 'conflicts' else
               'uncertain' if factual == 'uncertain' or fit == 'uncertain' else 'supported')
    return dict(verdict=verdict, unsupported_claims=[reason] if verdict == 'unsupported' else [],
                uncertainties=[reason] if verdict == 'uncertain' else [], reason=reason)
