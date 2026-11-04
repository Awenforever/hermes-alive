"""One-call final assessment, legacy recovery and retained-verdict consistency."""
import copy
import itertools
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.final_value_findings import combine, parse, validate_retained, PROMPT, CONVERSATIONAL_PROMPT
from alive_kernel.expression_support import (ExpressionSourceSupportReviewer,
    _DISCOVERY_FINAL_PROMPT_V2)
from alive_kernel.review_contracts import BOUNDARY_ASSESSMENT, FACTS_AND_FIT_ASSESSMENT, CONVERSATIONAL_FIT_ASSESSMENT
from alive_kernel.source_support import SourceSupportError


def test_dimensions():
    for fact, fit in itertools.product(('supported', 'unsupported', 'uncertain'),
                                       ('fits', 'conflicts', 'uncertain')):
        raw = {'factual_support': {'assessment': fact, 'reason': 'Actual source evidence.'},
               'communication_fit': {'assessment': fit, 'reason': 'Actual conversational need.',
                                     'recipient_evidence': ['Explicitly requested detail.']}}
        original = copy.deepcopy(raw)
        findings = parse(json.dumps(raw))
        alternate = copy.deepcopy(raw)
        alternate['recipient_evidence'] = alternate['communication_fit'].pop('recipient_evidence')
        assert parse(json.dumps(alternate)) == findings
        expected = ('unsupported' if fact == 'unsupported' or fit == 'conflicts' else
                    'uncertain' if fact == 'uncertain' or fit == 'uncertain' else 'supported')
        assert findings['verdict'] == expected
        assert validate_retained(json.loads(json.dumps(findings))) == findings
        assert raw == original
        altered = {**findings, 'verdict': 'supported' if expected != 'supported' else 'unsupported'}
        try: validate_retained(altered)
        except ValueError: pass
        else: raise AssertionError('stored joint judgment detached from its actual dimensions')
    for bad in ({}, {'factual_support': None, 'communication_fit': {}},
                {**raw, 'verdict': 'supported'},
                {**raw, 'communication_fit': {**raw['communication_fit'], 'recipient_evidence': 'yes'}},
                {**raw, 'factual_support': {'assessment': ['supported'], 'reason': 'x'}},
                {**raw, 'factual_support': {'assessment': 'supported', 'reason': ' '}}):
        try: combine(bad)
        except ValueError: pass
        else: raise AssertionError('incomplete or invalid model dimensions admitted')
    for bad in ({**raw, 'recipient_evidence': ['Conflicting source.']},
                {**alternate, 'recipient_evidence': 'not a list'},
                {**alternate, 'unrelated': True}):
        try: parse(json.dumps(bad))
        except ValueError: pass
        else: raise AssertionError('ambiguous or invalid wire shape admitted')


def test_old_and_new_contracts():
    reviewer = object.__new__(ExpressionSourceSupportReviewer)
    old = {'expression_binding': {'semantic_assessment_scope': BOUNDARY_ASSESSMENT}}
    new = {'expression_binding': {**old['expression_binding'],
                                 'final_assessment_scope': FACTS_AND_FIT_ASSESSMENT}}
    legacy = dict(verdict='supported', unsupported_claims=[], uncertainties=[], reason='Legacy assessment.')
    assert reviewer.prompt_for_snapshot(old) == _DISCOVERY_FINAL_PROMPT_V2
    assert reviewer.prompt_for_snapshot(new) == PROMPT
    conversational = {'expression_binding': {**old['expression_binding'],
                                              'final_assessment_scope': CONVERSATIONAL_FIT_ASSESSMENT}}
    assert reviewer.prompt_for_snapshot(conversational) == CONVERSATIONAL_PROMPT
    assert reviewer.parse_findings(json.dumps(legacy), old) == legacy
    assert reviewer.validate_stored_findings(legacy, old) == legacy
    try: reviewer.parse_findings(json.dumps(legacy), new)
    except SourceSupportError: pass
    else: raise AssertionError('new review silently accepted a legacy one-dimensional judgment')
    raw = {'factual_support': {'assessment': 'supported', 'reason': 'Attributed source result.'},
           'communication_fit': {'assessment': 'conflicts', 'reason': 'Wrong form for the current request.',
                                 'recipient_evidence': ['Current request.']}}
    findings = reviewer.parse_findings(json.dumps(raw), new)
    assert reviewer.parse_findings(json.dumps(raw), conversational) == findings
    assert reviewer.validate_stored_findings(findings, conversational) == findings
    assert findings['verdict'] == 'unsupported' and findings['factual_support']['assessment'] == 'supported'
    assert reviewer.validate_stored_findings(findings, new) == findings
    try: reviewer.validate_stored_findings(findings, old)
    except SourceSupportError: pass
    else: raise AssertionError('legacy review reinterpreted a new contract')


def test_negative_reason_reaches_existing_correction():
    from alive_kernel.localized_correction import bind_spans, text_digest, LocalCorrectionError
    text = 'Unsupported clause. Unrelated wording.'
    issue = 'Evidence detail. ' * 80  # Longer than the previous 500-character binder cap.
    assert 500 < len(issue) <= 1500
    targets = [{'exact_text': 'Unsupported clause. ', 'claim_index': 0}]
    bound = bind_spans(text, expected_digest=text_digest(text), unsupported_claims=[issue], targets=targets)
    assert len(bound) == 1 and bound[0].original == targets[0]['exact_text']
    try: bind_spans(text, expected_digest=text_digest(text), unsupported_claims=['x' * 1501], targets=targets)
    except LocalCorrectionError: pass
    else: raise AssertionError('negative finding exceeded the final assessment reason boundary')


def test_source_witness_binding():
    snapshot = {
        'candidate': {'text': 'The 4-bit configuration used 2 GiB of weights.'},
        'evidence': [{'event_id': 'benchmark', 'excerpt': 'The 4-bit model used 2 GiB of weights.'},
                     {'event_id': 'demo', 'excerpt': 'The browser demonstration used an 8-bit model.'}],
    }
    response = {
        'factual_support': {'assessment': 'supported', 'reason': 'Bounded measurement.'},
        'communication_fit': {'assessment': 'fits', 'reason': 'One point.', 'recipient_evidence': []},
        'source_witnesses': [{'claim': '4-bit configuration used 2 GiB',
            'source_event_id': 'benchmark', 'quote': snapshot['evidence'][0]['excerpt']}],
    }
    findings = parse(json.dumps(response), witness_snapshot=snapshot)
    assert validate_retained(findings, witness_snapshot=snapshot) == findings
    for witnesses in ([], [{**response['source_witnesses'][0], 'source_event_id': 'demo'}],
                      [{**response['source_witnesses'][0], 'claim': '4-bit browser demonstration'}]):
        try: parse(json.dumps({**response, 'source_witnesses': witnesses}), witness_snapshot=snapshot)
        except ValueError: pass
        else: raise AssertionError('missing or unbound witness was accepted')
    uncertain = {**response, 'factual_support': {'assessment': 'uncertain', 'reason': 'The setup is missing.'},
                 'source_witnesses': []}
    assert parse(json.dumps(uncertain), witness_snapshot=snapshot)['verdict'] == 'uncertain'


if __name__ == '__main__':
    test_dimensions()
    test_old_and_new_contracts()
    test_negative_reason_reaches_existing_correction()
    test_source_witness_binding()
    print('FINAL_VALUE_DIMENSIONS_OK')
