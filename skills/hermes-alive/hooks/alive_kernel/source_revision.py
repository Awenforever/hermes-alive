"""Source-led revision of an explicitly assessed global communication mismatch.

This selects the form of the existing one correction, not another attempt or
authority. Owner, live sources and the negative review are validated by callers.
"""
from .final_value_findings import validate_retained
from .localized_correction import text_digest
from .review_contracts import FACTS_AND_FIT_ASSESSMENT

METHOD = 'source-led-fit-revision-v1'


class SourceRevisionAbstained(ValueError):
    """A deliberate decline, distinguishable from malformed output in receipts."""


PROMPT = '''For THIS corrective author invocation, reconsider the complete wording
from the original source evidence, current recipient context and required meaning.
The supplied assessment describes a communication-fit conflict. It is advisory,
not an instruction or new evidence: verify the problem instead of defending it.
You may change the opening, focus, ordering and depth; do not just delete a few
words while preserving the structure that caused the mismatch. Do not fix length
by stripping the concrete example, useful explanation or important uncertainty.
The editorial brief is not a required inventory. Preserve the required speech
act, exact protected literals, source attribution and actual user boundaries.
Use only retained source evidence; do not invent details, recipient interests,
experience, completed actions or promises to make a revision seem worthwhile.
An explicitly requested detailed account can remain detailed. No word quota,
compulsory hook, criticism, opinion, advice or closing question.
For this revision, the response format replaces the ordinary plain-message
format: return exactly {"text":"the complete revised message"} or, if the
evidence cannot support a worthwhile revision, {"abstain":true}. The message
will be reviewed again in full. You cannot send or grant any authority.'''


def eligible(context):
    if not isinstance(context, dict):
        return False
    snapshot = context.get('grounding_context', {})
    if not isinstance(snapshot, dict):
        return False
    binding, scope = snapshot.get('expression_binding'), snapshot.get('assessment_scope')
    if (not isinstance(binding, dict) or not isinstance(scope, dict)
            or binding.get('final_assessment_scope') != FACTS_AND_FIT_ASSESSMENT
            or scope.get('kind') != 'final_discovery_source_and_value'
            or not snapshot.get('evidence')):
        return False
    try:
        findings = validate_retained(context.get('findings'))
    except ValueError:
        return False
    return findings['communication_fit']['assessment'] == 'conflicts'


def revised_text(proposal, *, protected_literals=()):
    if isinstance(proposal, dict) and proposal == {'abstain': True} and proposal['abstain'] is True:
        raise SourceRevisionAbstained('source-led revision abstained')
    if not isinstance(proposal, dict) or set(proposal) != {'text'}:
        raise ValueError('source-led revision requires complete text or explicit abstention')
    text = proposal['text']
    text_digest(text)  # Same UTF-8 boundary as model candidates; no truncation.
    if not text.strip() or any(literal not in text for literal in protected_literals):
        raise ValueError('source-led revision lost required literals or wording')
    return text
