"""Source-led revision for mismatched form or incomplete evidence coverage.

This selects the form of the existing one correction, not another attempt or
authority. Owner, live sources and the negative review are validated by callers.
"""
from .final_value_findings import validate_retained
from .localized_correction import text_digest
from .review_contracts import FACTS_AND_FIT_ASSESSMENTS, WITNESS_ASSESSMENTS

METHOD = 'source-led-fit-revision-v1'


class SourceRevisionAbstained(ValueError):
    """A deliberate decline, distinguishable from malformed output in receipts."""


PROMPT = '''Write a fresh message from the source evidence, current recipient
context and required meaning. The supplied assessment explains why an earlier
draft did not serve this conversation. It is advisory, without evidence or
authority of its own. Decide what belongs in this turn before writing.
You may change the opening, focus, ordering and depth. Develop the observation
with a concrete explanation and the uncertainty that matters to it. Leave
supporting material for a reply when it does not help that observation land.
When numeric evidence is unresolved, use only figures and comparisons that
the same source supports at the stated scope. Keep the whole result intelligible
if you omit optional figures or express an established result qualitatively.
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


def revision_author_view(author_context, correction, *, configured_route):
    """Give the reauthor one evidence bundle and the actionable findings.

    The old text, witnesses, and full review remain available to reconstruction
    and independent reassessment. Replaying them to the author would anchor the
    rewrite to the rejected outline and give optional facts undue prominence.
    """
    author = dict(author_context)
    if configured_route:
        author.pop('approved_search_queries', None)
        author.pop('search_context', None)
    review = correction['findings']
    findings = {}
    for field, positive in (('communication_fit', 'fits'), ('factual_support', 'supported'),
                            ('claim_scope', 'preserved'), ('numeric_evidence_coverage', 'covered')):
        finding = review.get(field)
        if finding is not None and finding['assessment'] != positive:
            findings[field] = finding
    return author, {'findings': findings}


def eligible(context):
    if not isinstance(context, dict):
        return False
    snapshot = context.get('grounding_context', {})
    if not isinstance(snapshot, dict):
        return False
    binding, scope = snapshot.get('expression_binding'), snapshot.get('assessment_scope')
    if (not isinstance(binding, dict) or not isinstance(scope, dict)
            or binding.get('final_assessment_scope') not in FACTS_AND_FIT_ASSESSMENTS
            or scope.get('kind') != 'final_discovery_source_and_value'
            or not snapshot.get('evidence')):
        return False
    try:
        findings = validate_retained(context.get('findings'),
            witness_snapshot=snapshot if binding['final_assessment_scope'] in WITNESS_ASSESSMENTS else None)
    except ValueError:
        return False
    return (findings['communication_fit']['assessment'] == 'conflicts'
            or findings.get('numeric_evidence_coverage', {}).get('assessment') == 'unresolved')


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
