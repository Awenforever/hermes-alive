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


def test_configured_route_provenance():
    from alive_kernel.research_evidence import configured_route_context, ROUTE_SEARCH_GUIDANCE
    from alive_kernel.review_contracts import ROUTE_AWARE_REVIEW, FIRST_SEARCH_REVIEW, ROUTE_FIT_ASSESSMENT
    from alive_kernel.final_value_findings import ROUTE_FIT_PROMPT
    assert configured_route_context(FIRST_SEARCH_REVIEW) is None
    role = configured_route_context(ROUTE_AWARE_REVIEW)
    assert role['current_owner_search_request_supplied'] is False
    role['current_owner_search_request_supplied'] = True
    assert configured_route_context(ROUTE_AWARE_REVIEW)['current_owner_search_request_supplied'] is False
    snapshot = {'expression_binding': {'final_assessment_scope': ROUTE_FIT_ASSESSMENT},
        'search_context': configured_route_context(ROUTE_AWARE_REVIEW),
        'candidate': {'text': 'A concrete unexpected trial used an existing instrument.'},
        'evidence': [{'event_id': 'trial', 'excerpt': 'A concrete unexpected trial used an existing instrument.'}],
        'approved_search_queries': ['A different collection route.']}
    wire = dict(facts='supported', fact_reason='Directly stated trial.', fit='fits',
        fit_reason='A concrete useful unexpected result, not a user assignment.',
        recipient_evidence=[], search_alignment='justified_pivot',
        scope_reason='The result has its own supported value; no claim of fulfilling the query.',
        source_witnesses=[{'claim': 'used an existing instrument', 'passage_id': 'P1.1'}])
    reviewer = object.__new__(ExpressionSourceSupportReviewer)
    assert reviewer.prompt_for_snapshot(snapshot) == ROUTE_FIT_PROMPT
    prompt, request = reviewer._assessment_request(snapshot)
    assert ROUTE_SEARCH_GUIDANCE in prompt and request['search_context'] == snapshot['search_context']
    result = parse(json.dumps(wire), witness_snapshot=snapshot)
    assert result['verdict'] == 'supported'
    assert validate_retained(result, witness_snapshot=snapshot) == result


def test_current_collection_route_does_not_apply_to_a_request():
    from alive_kernel.final_value_findings import (COLLECTION_ROUTE_PROMPT, COMPACT_IDENTIFIER_PROMPT,
                                                   SUBSTANTIVE_DISCOVERY_PROMPT, BOUNDED_INFERENCE_PROMPT)
    from alive_kernel.research_evidence import configured_route_context
    from alive_kernel.review_contracts import (COLLECTION_ROUTE_ASSESSMENT, COLLECTION_ROUTE_REVIEW,
                                                COHERENT_PASSAGE_ASSESSMENT, SUBSTANTIVE_DISCOVERY_ASSESSMENT,
                                                BOUNDED_INFERENCE_ASSESSMENT)

    role = configured_route_context(COLLECTION_ROUTE_REVIEW)
    reviewer = object.__new__(ExpressionSourceSupportReviewer)
    snapshot = dict(expression_binding={'final_assessment_scope': COLLECTION_ROUTE_ASSESSMENT},
                    approved_search_queries=['Instrument calibration example facility'], search_context=role,
                    candidate={'text': 'The institute reported a calibration test.'},
                    evidence=[{'event_id': 'test', 'excerpt': 'The institute reported a calibration test.'}])
    assert reviewer.prompt_for_snapshot(snapshot) == COLLECTION_ROUTE_PROMPT
    guess = {**snapshot, 'search_context': {'kind': role['kind']}}
    explicit_request = {**snapshot, 'search_context': {**role, 'current_owner_search_request_supplied': True}}
    previous = {**snapshot, 'expression_binding': {'final_assessment_scope': COHERENT_PASSAGE_ASSESSMENT}}
    for other in (guess, explicit_request, previous):
        assert reviewer.prompt_for_snapshot(other) == COMPACT_IDENTIFIER_PROMPT

    wire = dict(facts='supported', fact_reason='The institute reports the test.', fit='fits',
                fit_reason='Useful concrete finding.', recipient_evidence=[],
                search_alignment='matches', scope_reason='The result concerns the sought test.',
                claim_scope='preserved', claim_scope_reason='Only the institute is named.',
                source_witnesses=[{'claim': snapshot['candidate']['text'], 'passage_id': 'P1.1'}])
    findings = parse(json.dumps(wire), witness_snapshot=snapshot)
    assert findings['verdict'] == 'supported'
    assert validate_retained(findings, witness_snapshot=snapshot) == findings
    for negative in (dict(facts='unsupported'), dict(search_alignment='conflicts'),
                     dict(search_alignment='uncertain'), dict(claim_scope='unresolved')):
        assert parse(json.dumps({**wire, **negative}), witness_snapshot=snapshot)['verdict'] != 'supported'
    discovery = {**snapshot, 'expression_binding': {'final_assessment_scope': SUBSTANTIVE_DISCOVERY_ASSESSMENT}}
    assert reviewer.prompt_for_snapshot(discovery) == SUBSTANTIVE_DISCOVERY_PROMPT
    assert reviewer.prompt_for_snapshot({**discovery, 'search_context': explicit_request['search_context']}) == COMPACT_IDENTIFIER_PROMPT
    weak = parse(json.dumps({**wire, 'fit': 'conflicts', 'fit_reason': 'Only reports that a title was listed.'}),
                 witness_snapshot=discovery)
    assert weak['verdict'] == 'unsupported' and weak['factual_support']['assessment'] == 'supported'
    assert validate_retained(weak, witness_snapshot=discovery) == weak
    bounded = {**snapshot, 'expression_binding': {'final_assessment_scope': BOUNDED_INFERENCE_ASSESSMENT}}
    assert reviewer.prompt_for_snapshot(bounded) == BOUNDED_INFERENCE_PROMPT
    assert (reviewer.prompt_for_snapshot({**bounded, 'search_context': explicit_request['search_context']})
            == COMPACT_IDENTIFIER_PROMPT)
    for fact, place_scope in (('unsupported', 'overstated'), ('uncertain', 'unresolved')):
        unsupported = parse(json.dumps({**wire, 'facts': fact, 'claim_scope': place_scope}),
                            witness_snapshot=bounded)
        assert unsupported['verdict'] != 'supported'
        assert validate_retained(unsupported, witness_snapshot=bounded) == unsupported


def test_claim_scope_veto():
    from alive_kernel.final_value_findings import CLAIM_SCOPE_PROMPT, CONTRIBUTION_PROMPT, ROUTE_FIT_PROMPT
    from alive_kernel.review_contracts import CLAIM_SCOPE_ASSESSMENT, CONTRIBUTION_ASSESSMENT, ROUTE_FIT_ASSESSMENT

    snapshot = {'expression_binding': {'final_assessment_scope': CLAIM_SCOPE_ASSESSMENT},
                'candidate': {'text': 'The material cooled. The sensor registered an apparent drop.'},
                'evidence': [{'event_id': 'trial', 'excerpt': 'Only the surface proxy appeared to fall.'}]}
    wire = dict(facts='supported', fact_reason='Synthetic independent facts judgment.', fit='fits',
                fit_reason='Synthetic fit.', recipient_evidence=[], search_alignment='not_applicable',
                scope_reason='No query.', source_witnesses=[{'claim': 'The material cooled.', 'passage_id': 'P1.1'}])
    reviewer = object.__new__(ExpressionSourceSupportReviewer)
    assert reviewer.prompt_for_snapshot(snapshot) == CLAIM_SCOPE_PROMPT
    assert '"claim_scope":' in CLAIM_SCOPE_PROMPT and 'ten top-level fields' in CLAIM_SCOPE_PROMPT
    reason = 'The opening asserts direct cooling; the source only describes the proxy.'
    for status, verdict in (('overstated', 'unsupported'), ('unresolved', 'uncertain'),
                            ('preserved', 'supported')):
        result = parse(json.dumps(dict(wire, claim_scope=status, claim_scope_reason=reason)),
                       witness_snapshot=snapshot)
        assert result['verdict'] == verdict
        assert validate_retained(result, witness_snapshot=snapshot) == result
        if status != 'preserved':
            assert result['reason'] == reason
            tampered = {**result, 'verdict': 'supported'}
            try: validate_retained(tampered, witness_snapshot=snapshot)
            except ValueError: pass
            else: raise AssertionError('claim scope veto lost during retained review recovery')
    try: parse(json.dumps(wire), witness_snapshot=snapshot)
    except ValueError: pass
    else: raise AssertionError('current review accepted an absent scope judgment')
    snapshot['expression_binding']['final_assessment_scope'] = ROUTE_FIT_ASSESSMENT
    assert reviewer.prompt_for_snapshot(snapshot) == ROUTE_FIT_PROMPT
    assert parse(json.dumps(wire), witness_snapshot=snapshot)['verdict'] == 'supported'
    snapshot['expression_binding']['final_assessment_scope'] = CONTRIBUTION_ASSESSMENT
    assert reviewer.prompt_for_snapshot(snapshot) == CONTRIBUTION_PROMPT
    conflict = parse(json.dumps(dict(wire, claim_scope='preserved', claim_scope_reason=reason,
        fit='conflicts', fit_reason='The opening gets lost in peripheral details.')), witness_snapshot=snapshot)
    assert conflict['verdict'] == 'unsupported' and conflict['factual_support']['assessment'] == 'supported'
    assert validate_retained(conflict, witness_snapshot=snapshot) == conflict


def test_only_explicit_communication_choices_shape_new_discovery_openings():
    from alive_kernel.final_value_findings import PRESENTATION_PROMPT
    from alive_kernel.review_contracts import PRESENTATION_ASSESSMENT, SPLIT_SOURCE_REVIEW, CONTRIBUTION_REVIEW
    from alive_kernel.semantic_comparator import SemanticComparator
    from alive_kernel.feedback_context import source_review_prompt_snapshot

    choice = dict(predicate='profile.communication', kind='preference', value='Use plain language.')
    interest = dict(predicate='profile.interests', kind='preference', value='Robotics and vision.')
    recalled = dict(predicate='profile.external_memory', kind='preference', value='An inferred preference.')
    facts = [choice, interest, recalled]
    author = dict(semantic_source_contract=SPLIT_SOURCE_REVIEW, user_context=facts,
                  literal_feedback_context=[{'feedback_text': 'A one-off comment.'}])
    model_author = SemanticComparator._author_context(author)
    assert model_author['user_context'] == [choice] and not model_author['literal_feedback_context']
    historical = {**author, 'semantic_source_contract': CONTRIBUTION_REVIEW}
    assert SemanticComparator._author_context(historical) == historical
    assert author['user_context'] == facts and author['literal_feedback_context']

    snapshot = dict(expression_binding={'final_assessment_scope': PRESENTATION_ASSESSMENT},
                    explicit_context=facts, learned_advisory=[{'value': 'An inferred format.'}],
                    recent_feedback_context=author['literal_feedback_context'])
    assert object.__new__(ExpressionSourceSupportReviewer).prompt_for_snapshot(snapshot) == PRESENTATION_PROMPT
    model_review = source_review_prompt_snapshot(snapshot)
    assert model_review['explicit_context'] == [choice]
    assert not model_review['learned_advisory'] and not model_review['recent_feedback_context']
    assert snapshot['explicit_context'] == facts and snapshot['learned_advisory'] and snapshot['recent_feedback_context']


def test_numeric_coverage_of_actual_draft():
    from alive_kernel.review_contracts import CLAIM_COVERAGE_ASSESSMENT, PRESENTATION_ASSESSMENT

    opening = 'The new terrain map has a 10 m resolution.'
    comparison = 'The existing regional product uses 1,000 m cells.'
    text = f'{opening}\n\n1. {comparison} [Data](<https://example.invalid/2026/map>)'
    snapshot = dict(candidate={'text': text}, evidence=[
        {'event_id': 'map', 'excerpt': 'The publisher released a 10 m terrain map.'},
        {'event_id': 'baseline', 'excerpt': 'The existing regional product has 1000 m cells.'}])
    wire = dict(facts='supported', fact_reason='The reviewer approves the draft.', fit='fits',
        fit_reason='One concrete contribution.', recipient_evidence=[], search_alignment='not_applicable',
        scope_reason='No query.', claim_scope='preserved', claim_scope_reason='The map is sourced.',
        source_witnesses=[dict(claim=opening, passage_id='P1.1')])

    def evaluate(scope, response):
        bound = {**snapshot, 'expression_binding': {'final_assessment_scope': scope}}
        result = parse(json.dumps(response), witness_snapshot=bound)
        assert validate_retained(result, witness_snapshot=bound) == result
        return result

    assert evaluate(PRESENTATION_ASSESSMENT, wire)['verdict'] == 'supported'
    result = evaluate(CLAIM_COVERAGE_ASSESSMENT, wire)
    assert result['verdict'] == 'uncertain' and '1000' in result['reason']
    assert evaluate(CLAIM_COVERAGE_ASSESSMENT, {**wire, 'source_witnesses': [
        *wire['source_witnesses'], dict(claim=comparison, passage_id='P1.1')]})['verdict'] == 'uncertain'
    witnessed = {**wire, 'source_witnesses': [
        *wire['source_witnesses'], dict(claim=comparison, passage_id='P2.1')]}
    assert evaluate(CLAIM_COVERAGE_ASSESSMENT, witnessed)['verdict'] == 'supported'
    snapshot['candidate']['text'] += '\nThe sensors also operated at a depth of 10 m.'
    assert evaluate(CLAIM_COVERAGE_ASSESSMENT, witnessed)['verdict'] == 'uncertain'


def test_passage_locator_does_not_replace_the_review_witness():
    from alive_kernel.final_value_findings import passage_request
    from alive_kernel.review_contracts import CLAIM_COVERAGE_ASSESSMENT, PASSAGE_LOCATOR_ASSESSMENT

    claim = 'In survey sector R7, 622 objects were found.'
    original = {'candidate': {'text': claim + ' The condition was good.'},
        'evidence': [{'event_id': 'report', 'excerpt':
            'In survey sector R7 there were 622 objects. '.ljust(500) + 'Most were in good condition.'}]}
    previous = {**original, 'expression_binding': {'final_assessment_scope': CLAIM_COVERAGE_ASSESSMENT}}
    current = {**original, 'expression_binding': {'final_assessment_scope': PASSAGE_LOCATOR_ASSESSMENT}}
    assert 'numeric_passage_locations' not in passage_request(previous, labelled=True)
    located = passage_request(current, labelled=True)
    assert located['numeric_passage_locations'] == [
        {'kind': 'number', 'literal': value, 'matching_passage_ids': ['P1.1']} for value in ('7', '622')]
    wire = dict(facts='supported', fact_reason='Both details are in the supplied report.',
        fit='fits', fit_reason='One point.', recipient_evidence=[], search_alignment='not_applicable',
        scope_reason='No query.', claim_scope='preserved', claim_scope_reason='Survey items are in scope.',
        source_witnesses=[dict(claim=claim, passage_id='P1.2')])
    assert parse(json.dumps(wire), witness_snapshot=current)['verdict'] == 'uncertain'
    wire['source_witnesses'] = [dict(claim=claim, passage_id='P1.1'),
                               dict(claim='The condition was good.', passage_id='P1.2')]
    result = parse(json.dumps(wire), witness_snapshot=current)
    assert result['verdict'] == 'supported'
    assert validate_retained(result, witness_snapshot=current) == result


def test_compact_identifiers_keep_measurements_separate():
    from alive_kernel.final_value_findings import passage_request
    from alive_kernel.review_contracts import COMPACT_IDENTIFIER_ASSESSMENT, PASSAGE_LOCATOR_ASSESSMENT

    claim = 'R72N produced a 0.07° grid on an 80GB card.'
    source = 'R72N produced a 0.07° grid on an 80GB card. There were 71 test stations.'
    wire = dict(facts='supported', fact_reason='The release documents its test.',
        fit='fits', fit_reason='One concrete point.', recipient_evidence=[], search_alignment='not_applicable',
        scope_reason='No query.', claim_scope='preserved', claim_scope_reason='The grid is reported.',
        source_witnesses=[dict(claim=claim, passage_id='P1.1')])

    def assess(text, assessment):
        snapshot = dict(candidate={'text': text}, evidence=[{'event_id': 'release', 'excerpt': source}],
            expression_binding={'final_assessment_scope': assessment})
        wire['source_witnesses'][0]['claim'] = text
        parsed = parse(json.dumps(wire), witness_snapshot=snapshot)
        assert validate_retained(parsed, witness_snapshot=snapshot) == parsed
        return parsed, passage_request(snapshot, labelled=True)['numeric_passage_locations']

    result, locator = assess(claim, COMPACT_IDENTIFIER_ASSESSMENT)
    assert result['verdict'] == 'supported'
    assert [(v['kind'], v['literal']) for v in locator] == [
        ('identifier', 'R72N'), ('number', '0.07'), ('number', '80')]
    result, _ = assess(claim.replace('R72N', 'R71N'), COMPACT_IDENTIFIER_ASSESSMENT)
    assert result['verdict'] == 'uncertain' and 'R71N' in result['reason']
    result, _ = assess(claim.replace('0.07°', '72°'), COMPACT_IDENTIFIER_ASSESSMENT)
    assert result['verdict'] == 'uncertain' and '72' in result['reason']
    result, legacy = assess(claim.replace('R72N', 'R71N'), PASSAGE_LOCATOR_ASSESSMENT)
    assert result['verdict'] == 'supported'
    assert legacy[0]['kind'] == 'number' and legacy[0]['literal'] == '71'


def test_visible_markdown_claim_witness():
    from alive_kernel.review_contracts import CLAIM_COVERAGE_ASSESSMENT

    snapshot = dict(
        expression_binding={'final_assessment_scope': CLAIM_COVERAGE_ASSESSMENT},
        candidate={'text': 'The museum opens **Quiet Gardens**. [Details](https://example.invalid/exhibit)\n\nBring a coat.'},
        evidence=[{'event_id': 'museum', 'excerpt': 'The museum opens its Quiet Gardens exhibition.'}],
    )
    response = dict(facts='supported', fact_reason='The title appears in the source.', fit='fits',
        fit_reason='One opening to discuss.', recipient_evidence=[], search_alignment='not_applicable',
        scope_reason='No query.', claim_scope='preserved', claim_scope_reason='The title is exact.',
        source_witnesses=[dict(claim='The museum opens Quiet Gardens', passage_id='P1.1')])
    findings = parse(json.dumps(response), witness_snapshot=snapshot)
    assert findings['verdict'] == 'supported'
    assert validate_retained(findings, witness_snapshot=snapshot) == findings
    for changed in ('The museum closes **Quiet Gardens**.',
                    'The museum opens\n\n**Quiet Gardens**.',
                    'The museum opens ![Quiet Gardens](https://example.invalid/image).'):
        bound = {**snapshot, 'candidate': {'text': changed}}
        try: parse(json.dumps(response), witness_snapshot=bound)
        except ValueError: pass
        else: raise AssertionError('a changed claim was accepted as presentation-only')

    snapshot['candidate']['text'] += '\nEntry costs **10 dollars**.'
    response['source_witnesses'].append(dict(claim='Entry costs 10 dollars', passage_id='P1.1'))
    assert parse(json.dumps(response), witness_snapshot=snapshot)['verdict'] == 'uncertain'


def test_named_identifiers_do_not_supply_measurements():
    from alive_kernel.review_contracts import (CLAIM_COVERAGE_ASSESSMENT,
        FIRST_CLAIM_COVERAGE_ASSESSMENT)

    text = 'In this evaluation, Orion-3.8 scored 42.8%.'
    snapshot = dict(candidate={'text': text}, evidence=[
        {'event_id':'trial', 'excerpt':'Trial results: 42.8%.' + ' ' * 500
            + 'The tested model identifier is Orion-3.8.'},
        {'event_id':'unrelated', 'excerpt':'A different trial used Orion-3.9.'},
    ])
    response = dict(facts='supported', fact_reason='The measured score is stated.', fit='fits',
        fit_reason='One focused result.', recipient_evidence=[], search_alignment='not_applicable',
        scope_reason='No query.', claim_scope='preserved', claim_scope_reason='Same evaluation.',
        source_witnesses=[dict(claim=text, passage_id='P1.1')])

    def assess(scope, wording, evidence=snapshot['evidence']):
        current = {**snapshot, 'candidate': {'text': wording}, 'evidence': evidence,
            'expression_binding': {'final_assessment_scope': scope}}
        wire = {**response, 'source_witnesses': [dict(claim=wording, passage_id='P1.1')]}
        result = parse(json.dumps(wire), witness_snapshot=current)
        assert validate_retained(result, witness_snapshot=current) == result
        return result

    assert assess(FIRST_CLAIM_COVERAGE_ASSESSMENT, text)['verdict'] == 'uncertain'
    assert assess(CLAIM_COVERAGE_ASSESSMENT, text)['verdict'] == 'supported'
    wrong_model = assess(CLAIM_COVERAGE_ASSESSMENT, text.replace('Orion-3.8','Orion-3.9'))
    assert wrong_model['verdict'] == 'uncertain' and 'Orion-3.9' in wrong_model['reason']
    identifier_only = [{'event_id':'trial', 'excerpt':'The evaluated model is Orion-3.8.'}]
    wrong_score = assess(CLAIM_COVERAGE_ASSESSMENT, text.replace('42.8%','3.8%'), identifier_only)
    assert wrong_score['verdict'] == 'uncertain' and '3.8' in wrong_score['reason']


def test_rejection_survives_invalid_factual_witness():
    from alive_kernel.review_contracts import CLAIM_COVERAGE_ASSESSMENT, IDENTIFIER_COVERAGE_ASSESSMENT

    text = 'The experiment ran for 12 hours.'
    snapshot = dict(candidate={'text': text}, evidence=[
        {'event_id': 'experiment', 'excerpt': text}])
    wire = dict(facts='supported', fact_reason='The duration is stated.', fit='conflicts',
        fit_reason='The reader asked for the result, not the setup.', recipient_evidence=[],
        search_alignment='not_applicable', scope_reason='No query.',
        claim_scope='preserved', claim_scope_reason='Explicit duration.',
        source_witnesses=[dict(claim='the experiment lasted for 12 hours', passage_id='P1.1')])
    current = {**snapshot, 'expression_binding': {'final_assessment_scope': CLAIM_COVERAGE_ASSESSMENT}}
    result = parse(json.dumps(wire), witness_snapshot=current)
    assert result['verdict'] == 'unsupported' and result['reason'] == wire['fit_reason']
    assert result['factual_support']['assessment'] == 'uncertain'
    assert not result['source_witnesses'] and result['numeric_evidence_coverage']['assessment'] == 'unresolved'
    assert validate_retained(result, witness_snapshot=current) == result
    old = {**snapshot, 'expression_binding': {'final_assessment_scope': IDENTIFIER_COVERAGE_ASSESSMENT}}
    for bound, response in ((old, wire), (current, {**wire, 'fit': 'fits'})):
        try: parse(json.dumps(response), witness_snapshot=bound)
        except ValueError: pass
        else: raise AssertionError('the invalid witness escaped its review contract')


def test_passage_boundaries_keep_the_measured_clause_together():
    from alive_kernel.final_value_findings import passage_request
    from alive_kernel.review_contracts import COHERENT_PASSAGE_ASSESSMENT, COMPACT_IDENTIFIER_ASSESSMENT

    sentence = 'Across the 15 held-out workloads measured under the same pre-silicon assumptions, the median was 3.83 watts.'
    excerpt = 'Background: ' + 'a' * 420 + '. ' + sentence + '\n' + 'b' * 1100
    text = 'The median was 3.83 watts on the 15 held-out workloads.'
    response = dict(facts='supported', fact_reason='The retained comparison reports both values.', fit='fits',
        fit_reason='One focused result.', recipient_evidence=[], search_alignment='not_applicable',
        scope_reason='No query.', claim_scope='preserved', claim_scope_reason='Same held-out workload group.',
        source_witnesses=[dict(claim=text, passage_id='P1.2')])

    def wire(scope):
        snapshot = dict(expression_binding={'final_assessment_scope': scope}, candidate={'text': text},
                        evidence=[{'event_id': 'held-out-study', 'excerpt': excerpt}])
        request = passage_request(snapshot, labelled=True)
        passages = request['evidence'][0]['passages']
        assert ''.join(p['text'] for p in passages) == excerpt
        assert all(0 < len(p['text']) <= 500 for p in passages)
        return snapshot, passages

    old, previous = wire(COMPACT_IDENTIFIER_ASSESSMENT)
    assert not any(sentence in passage['text'] for passage in previous)
    assert parse(json.dumps(response), witness_snapshot=old)['verdict'] == 'uncertain'
    snapshot, current = wire(COHERENT_PASSAGE_ASSESSMENT)
    assert sentence in current[1]['text']
    findings = parse(json.dumps(response), witness_snapshot=snapshot)
    assert findings['verdict'] == 'supported'
    assert validate_retained(findings, witness_snapshot=snapshot) == findings
    response['source_witnesses'][0]['passage_id'] = 'P1.1'
    assert parse(json.dumps(response), witness_snapshot=snapshot)['verdict'] == 'uncertain'


if __name__ == '__main__':
    test_dimensions()
    test_old_and_new_contracts()
    test_negative_reason_reaches_existing_correction()
    test_source_witness_binding()
    test_independent_search_alignment()
    test_configured_route_provenance()
    test_current_collection_route_does_not_apply_to_a_request()
    test_claim_scope_veto()
    test_only_explicit_communication_choices_shape_new_discovery_openings()
    test_numeric_coverage_of_actual_draft()
    test_passage_locator_does_not_replace_the_review_witness()
    test_compact_identifiers_keep_measurements_separate()
    test_visible_markdown_claim_witness()
    test_named_identifiers_do_not_supply_measurements()
    test_rejection_survives_invalid_factual_witness()
    test_passage_boundaries_keep_the_measured_clause_together()
    print('FINAL_VALUE_DIMENSIONS_OK')
