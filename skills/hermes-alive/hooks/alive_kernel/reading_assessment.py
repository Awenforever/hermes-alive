"""Bounded advisory reading findings, not source truth or agenda completion."""
from collections import Counter
from copy import deepcopy

METHOD = 'inquiry-reading-assessment-v1'
GUIDANCE = '''
Alongside the ordinary candidate/abstention fields return reading_assessments:
one item per tentative_discovery_tasks item_id. Assess what the actual supplied
reading established about that question, not whether a page was retrieved.
Each item has exactly item_id, status (answered|partial|unresolved), findings,
and open_questions. findings contains at most two objects with observation_event_id,
quote (1-600 characters copied verbatim from a supplied research-page excerpt),
and interpretation (1-600 characters explaining what that passage establishes).
open_questions has at most three nonempty questions, each at most 300 characters.
answered needs a finding and no open questions; partial needs both; unresolved
needs an open question and may have no findings. Source announcements, promotional
claims and staged dialogue are not independent confirmation of implementation.
An exact quotation proves only that the text occurs, not that its interpretation
is correct. These are tentative research findings, not user preferences, action
permission or proof the agenda is complete. An unanswered inquiry need not become
a thematic article. You may abstain, pursue a later inquiry or share an alternate
genuine discovery grounded in the supplied material. Do not force a contrast,
criticism, personal relevance slogan or narration of your research process.
Malformed or missing assessments remain unassessed, never silently answered;
they do not by themselves invalidate an otherwise valid communication candidate.
'''


def normalize(raw, *, inquiries, excerpts):
    """Keep complete valid items; no partial repair, inference or provider IO."""
    expected=tuple(i['item_id'] for i in inquiries)
    if len(expected)>4 or len(set(expected))!=len(expected):
        raise ValueError('bounded distinct current inquiries required')
    if not isinstance(raw,list) or len(raw)>8:
        return dict(entries=[],unassessed_item_ids=list(expected),rejected_count=int(raw is not None))
    counts=Counter(r.get('item_id') for r in raw if isinstance(r,dict) and isinstance(r.get('item_id'),str))
    accepted={};rejected=0
    def text(value,limit):return isinstance(value,str) and 0<len(value.strip())<=limit
    for row in raw:
        try:
            if (not isinstance(row,dict) or set(row)!={'item_id','status','findings','open_questions'}
                    or row['item_id'] not in expected or counts[row['item_id']]!=1
                    or row['status'] not in ('answered','partial','unresolved')
                    or not isinstance(row['findings'],list) or len(row['findings'])>2
                    or not isinstance(row['open_questions'],list) or len(row['open_questions'])>3
                    or any(not text(q,300) for q in row['open_questions'])):
                raise ValueError('invalid reading assessment')
            for finding in row['findings']:
                if (not isinstance(finding,dict)
                        or set(finding)!={'observation_event_id','quote','interpretation'}
                        or not isinstance(finding['observation_event_id'],str)
                        or finding['observation_event_id'] not in excerpts
                        or not text(finding['quote'],600) or not text(finding['interpretation'],600)
                        or finding['quote'] not in excerpts[finding['observation_event_id']]):
                    raise ValueError('finding lacks an admitted research passage')
            if (row['status']=='answered' and (not row['findings'] or row['open_questions'])
                    or row['status']=='partial' and (not row['findings'] or not row['open_questions'])
                    or row['status']=='unresolved' and not row['open_questions']):
                raise ValueError('reading status lacks its stated basis')
            accepted[row['item_id']]=deepcopy(row)
        except (KeyError,TypeError,ValueError):rejected+=1
    return dict(entries=[accepted[i] for i in expected if i in accepted],
        unassessed_item_ids=[i for i in expected if i not in accepted],rejected_count=rejected)


def validate(stored, *, inquiries, excerpts):
    if (not isinstance(stored,dict) or set(stored)!={'entries','unassessed_item_ids','rejected_count'}
            or type(stored['rejected_count']) is not int or not 0<=stored['rejected_count']<=8):
        raise ValueError('invalid retained reading assessment')
    normalized=normalize(stored['entries'],inquiries=inquiries,excerpts=excerpts)
    if normalized['rejected_count'] or any(normalized[k]!=stored[k] for k in ('entries','unassessed_item_ids')):
        raise ValueError('retained reading evidence changed')
    return stored
