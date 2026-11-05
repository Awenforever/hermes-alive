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
    from alive_kernel.final_value_findings import passage_request
    from alive_kernel.review_contracts import FLAT_FIT_ASSESSMENT, LABELLED_FIT_ASSESSMENT, PASSAGE_FIT_ASSESSMENT
    snapshot['expression_binding'] = {'final_assessment_scope': PASSAGE_FIT_ASSESSMENT}
    request = passage_request(snapshot)
    assert ''.join(request['evidence'][0]['passages']) == snapshot['evidence'][0]['excerpt']
    witness = {'claim': '4-bit configuration used 2 GiB', 'source_event_id': 'benchmark', 'passage': 1}
    indexed = {**response, 'source_witnesses': [witness]}
    findings = parse(json.dumps(indexed), witness_snapshot=snapshot)
    assert findings['source_witnesses'] == [{**witness, 'quote': snapshot['evidence'][0]['excerpt']}]
    assert validate_retained(findings, witness_snapshot=snapshot) == findings
    for passage in (0, 2, True, '1'):
        try: parse(json.dumps({**indexed, 'source_witnesses': [{**witness, 'passage': passage}]}),
                   witness_snapshot=snapshot)
        except ValueError: pass
        else: raise AssertionError('invalid passage reference was accepted')

    snapshot['expression_binding']['final_assessment_scope'] = LABELLED_FIT_ASSESSMENT
    request = passage_request(snapshot, labelled=True)
    first, second = [source['passages'][0] for source in request['evidence']]
    assert first['passage_id'] != second['passage_id']
    assert first['text'] == snapshot['evidence'][0]['excerpt']
    labelled = {**response, 'source_witnesses': [
        {'claim': witness['claim'], 'passage_id': first['passage_id']}]}
    findings = parse(json.dumps(labelled), witness_snapshot=snapshot)
    assert findings['source_witnesses'] == [{**labelled['source_witnesses'][0],
        'source_event_id': 'benchmark', 'quote': first['text']}]
    assert validate_retained(findings, witness_snapshot=snapshot) == findings
    bad_response = {**labelled, 'source_witnesses': [
        {**labelled['source_witnesses'][0], 'passage_id': 'P1.15'}]}
    bad_receipt = {**findings, 'source_witnesses': [
        {**findings['source_witnesses'][0], 'passage_id': second['passage_id']}]}
    for action in (
        lambda: parse(json.dumps(bad_response), witness_snapshot=snapshot),
        lambda: validate_retained(bad_receipt, witness_snapshot=snapshot),
    ):
        try: action()
        except ValueError: pass
        else: raise AssertionError('an absent or rebound passage ID was accepted')
    snapshot['expression_binding']['final_assessment_scope'] = FLAT_FIT_ASSESSMENT
    flat = dict(facts='supported', fact_reason='Bounded measurement.', fit='fits',
        fit_reason='One point.', recipient_evidence=[], source_witnesses=labelled['source_witnesses'])
    assert parse(json.dumps(flat), witness_snapshot=snapshot) == findings
    assert validate_retained(findings, witness_snapshot=snapshot) == findings
    try:
        parse(json.dumps({**flat, 'factual_support': labelled['factual_support']}), witness_snapshot=snapshot)
    except ValueError:
        pass
    else:
        raise AssertionError('mixed old and new review fields were accepted')


def test_independent_search_alignment():
    from alive_kernel.final_value_findings import SEARCH_FIT_PROMPT
    from alive_kernel.review_contracts import SEARCH_FIT_ASSESSMENT
    snapshot = {'expression_binding': {'final_assessment_scope': SEARCH_FIT_ASSESSMENT},
        'candidate': {'text': 'A public trial used an existing instrument.'},
        'evidence': [{'event_id': 'public-trial', 'excerpt': 'A public trial used an existing instrument.'}],
        'approved_search_queries': ['Current public trials in the specified region.']}
    wire = dict(facts='supported', fact_reason='The source reports this trial.', fit='fits',
        fit_reason='A useful plain explanation.', recipient_evidence=[],
        source_witnesses=[{'claim': 'used an existing instrument', 'passage_id': 'P1.1'}])
    reviewer = object.__new__(ExpressionSourceSupportReviewer)
    assert reviewer.prompt_for_snapshot(snapshot) == SEARCH_FIT_PROMPT
    for alignment, expected in (('matches', 'supported'), ('justified_pivot', 'supported'),
                                ('conflicts', 'unsupported'), ('uncertain', 'uncertain')):
        result = parse(json.dumps({**wire, 'search_alignment': alignment,
            'scope_reason': 'Synthetic explicit scope judgment.'}), witness_snapshot=snapshot)
        assert result['verdict'] == expected
        assert result['factual_support']['assessment'] == 'supported'
        assert result['communication_fit']['assessment'] == 'fits'
        assert validate_retained(result, witness_snapshot=snapshot) == result
        tampered = copy.deepcopy(result)
        tampered['search_alignment']['assessment'] = 'conflicts' if alignment != 'conflicts' else 'matches'
        try: validate_retained(tampered, witness_snapshot=snapshot)
        except ValueError: pass
        else: raise AssertionError('search judgment detached from retained verdict')
    for extra in ({}, {'search_alignment': 'not_applicable', 'scope_reason': 'No query'},
                  {'search_alignment': 'matches', 'scope_reason': ''}):
        try: parse(json.dumps({**wire, **extra}), witness_snapshot=snapshot)
        except ValueError: pass
        else: raise AssertionError('missing or inapplicable search judgment admitted')
    snapshot.pop('approved_search_queries')
    result = parse(json.dumps({**wire, 'search_alignment': 'not_applicable',
        'scope_reason': 'No approved search supplied.'}), witness_snapshot=snapshot)
    assert validate_retained(result, witness_snapshot=snapshot)['verdict'] == 'supported'


if __name__ == '__main__':
    test_dimensions()
    test_old_and_new_contracts()
    test_negative_reason_reaches_existing_correction()
    test_source_witness_binding()
    test_independent_search_alignment()
    print('FINAL_VALUE_DIMENSIONS_OK')
