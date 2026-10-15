"""Separate recipient-facing meaning from model-proposed behavior constraints.

Structural validation is not semantic support, user consent or send authority.
Plans belong to their immutable opportunity proposal, not to a mutable style cache.
"""
import json

from .semantic_rendering import MessageSpeechAct, SemanticAtom, SemanticAtomKind


def validate_communication_plan(raw, *, action_kind):
    if (not isinstance(raw, dict) or set(raw) != {
            'version', 'recipient_goal', 'speech_act', 'contents', 'behavior_constraints'}
            or type(raw['version']) is not int or raw['version'] != 1
            or not isinstance(raw['recipient_goal'], str)
            or not 1 <= len(raw['recipient_goal']) <= 512
            or not isinstance(raw['contents'], list) or not 1 <= len(raw['contents']) <= 6
            or not isinstance(raw['behavior_constraints'], list)
            or len(raw['behavior_constraints']) > 6
            or any(not isinstance(x, str) or not 1 <= len(x) <= 300
                   for x in raw['behavior_constraints'])):
        raise ValueError('invalid communication plan')
    speech = MessageSpeechAct(raw['speech_act'])
    allowed = ({MessageSpeechAct.ASK} if action_kind == 'ask' else
               {MessageSpeechAct.SHARE, MessageSpeechAct.INFORM,
                MessageSpeechAct.REMIND, MessageSpeechAct.WARN} if action_kind == 'share' else set())
    if speech not in allowed:
        raise ValueError('communication speech act changes selected action')
    for index, item in enumerate(raw['contents']):
        if (not isinstance(item, dict) or not {'kind', 'text'} <= set(item)
                or set(item) - {'kind', 'text', 'protected_literals'}
                or not isinstance(item['text'], str) or not 1 <= len(item['text']) <= 800
                or not isinstance(item.get('protected_literals', []), list)
                or any(not isinstance(x, str) or not x for x in item.get('protected_literals', []))):
            raise ValueError('invalid recipient-facing content')
        kind = SemanticAtomKind(item['kind'])
        if kind is SemanticAtomKind.PROPOSED_CONTENT:
            raise ValueError('a plan cannot protect an undifferentiated draft')
        # Reuse the actual literal/kind limits; the synthetic evidence ID is only
        # for structural validation, never persisted as a real source witness.
        SemanticAtom(f'content-{index}', kind, item['text'], ('plan:structure-only',),
                     tuple(item.get('protected_literals', ())))
    if len(json.dumps(raw, ensure_ascii=False)) > 4000:
        raise ValueError('communication plan exceeds context budget')
    return raw


def plan_atoms(plan, *, evidence):
    return tuple(SemanticAtom(f'content-{index}', SemanticAtomKind(item['kind']),
        item['text'], evidence, tuple(item.get('protected_literals', ())))
        for index, item in enumerate(plan['contents']))


def expression_context(plan):
    return dict(method='recipient-meaning-v1', recipient_goal=plan['recipient_goal'],
        behavior_constraints=plan['behavior_constraints'],
        constraints_are_not_recipient_content=True, authority_granted=False)
