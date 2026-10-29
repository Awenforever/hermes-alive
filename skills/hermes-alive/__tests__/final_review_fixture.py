"""Controlled HTTP/model output with no shadow-kernel or provider import."""


def controlled_final_findings(snapshot, *, factual='supported', fit='fits', reason='Synthetic assessment.'):
    if snapshot.get('expression_binding', {}).get('final_assessment_scope') == 'factual-support-and-communication-fit-v1':
        return {'factual_support': {'assessment': factual, 'reason': reason},
                'communication_fit': {'assessment': fit, 'reason': reason, 'recipient_evidence': []}}
    verdict = ('unsupported' if factual == 'unsupported' or fit == 'conflicts' else
               'uncertain' if factual == 'uncertain' or fit == 'uncertain' else 'supported')
    return dict(verdict=verdict, unsupported_claims=[reason] if verdict == 'unsupported' else [],
                uncertainties=[reason] if verdict == 'uncertain' else [], reason=reason)
