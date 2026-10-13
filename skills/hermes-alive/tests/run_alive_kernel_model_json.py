#!/usr/bin/env python3
"""Transport wrapping does not repair broken JSON or approve semantic content."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.model_json import parse_model_json, ModelJSONError
from alive_kernel.semantic_comparator import SemanticComparator
from alive_kernel.deliberation_synthesis import DeliberationSynthesizer
from alive_kernel.source_support import SourceSupportReviewer

document = {'text': 'Untrusted ``` content', 'value': .25, 'nested': [True, None, {'k': 'v'}]}
plain = json.dumps(document)
for text in (plain, ' \n' + plain + '\n', '```json\n' + plain + '\n```',
             '```JSON\r\n' + plain + '\r\n```', '```\n' + plain + '\n```'):
    assert parse_model_json(text) == document
for text in ('', '```json\n{}', 'Here is JSON: {}', '{} extra', '{"x":1,"x":2}',
             '{"nested":{"x":1,"x":2}}', '{"v":NaN}', '{"v":Infinity}', '{"v":1e999}',
             '```javascript\n{}\n```', '```json\n{}\n```\n```json\n{}\n```',
             '```json\n{"x":\n```', 'x' * 32001, '[' * 2000 + ']' * 2000):
    try:
        parse_model_json(text)
    except ModelJSONError:
        pass
    else:
        raise AssertionError('invalid/ambiguous model JSON was repaired or accepted')
review = {'atom_reviews': [{'atom_id': 'proposed-message', 'preserved': True, 'risks': []}],
          'added_claims_detected': False, 'speech_act_preserved': True, 'protected_literals_preserved': True}
assert SemanticComparator._findings(json.dumps(review)) == SemanticComparator._findings(
    '```json\n' + json.dumps(review) + '\n```')
selection = {'candidate_id': 'candidate:test', 'rationale': 'Tentative fixture selection'}
assert DeliberationSynthesizer._selection_document('```json\n' + json.dumps(selection) + '\n```') == (
    selection['candidate_id'], selection['rationale'])
support = {'verdict': 'uncertain', 'unsupported_claims': [], 'uncertainties': ['Unverified fixture'],
           'reason': 'Not proof of source truth'}
assert SourceSupportReviewer.findings('```json\n' + json.dumps(support) + '\n```') == support
print('HERMES_ALIVE_KERNEL_MODEL_JSON_OK')
