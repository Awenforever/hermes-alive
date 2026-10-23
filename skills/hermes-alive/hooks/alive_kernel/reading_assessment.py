"""Bounded advisory reading findings, not source truth or agenda completion."""
from collections import Counter
from copy import deepcopy

METHOD = 'inquiry-reading-assessment-v1'
REFERENCE_METHOD = 'inquiry-reading-assessment-v2'
METHODS = (METHOD,REFERENCE_METHOD)
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


REFERENCE_GUIDANCE = '''
Alongside the ordinary candidates/abstentions return reading_assessments, one
per tentative_discovery_tasks item_id: {item_id,status,findings,open_questions}.
status is answered|partial|unresolved. findings has at most two objects with
exactly observation_event_id, passage_id and interpretation (1-600 characters).
Select observation_event_id and passage_id from the supplied summary_passages;
the host resolves the actual original passage. Do not copy, repair or paraphrase
source text into a quote field. open_questions has up to three nonempty questions,
each at most300 characters. answered requires a finding and no open questions;
partial needs both; unresolved needs an open question. Missing or malformed notes
remain unassessed and do not invalidate an otherwise valid communication candidate.
Assess what the reading established about the question, not successful retrieval.
A selected passage proves only text availability, not interpretation or truth.
Overlapping passages from one original source are not independent confirmations.
Announcements, promotions and staged dialogue are not independent validation.
These are tentative research notes, not owner preferences, a recipient outline,
agenda completion or permission. Unanswered research is not a publishing obligation;
an alternate grounded discovery may still be valuable. Do not force a thematic
article, contrast, criticism, personal relevance slogan or research-log recital.
'''


def passages(excerpt):
    """Exact bounded overlapping source windows; no PDF/prose repair rules."""
    if not isinstance(excerpt,str):raise ValueError('original admitted excerpt required')
    result=[];start=0
    while start<len(excerpt):
        end=min(len(excerpt),start+560)
        result.append(dict(passage_id='p'+str(len(result)+1),text=excerpt[start:end]))
        if end==len(excerpt):break
        start=end-80
    return result


def normalize_references(raw, *, inquiries, excerpts):
    if not isinstance(raw,list) or len(raw)>8:return normalize(raw,inquiries=inquiries,excerpts=excerpts)
    sources={identity:{p['passage_id']:p['text'] for p in passages(text)} for identity,text in excerpts.items()}
    converted=[]
    for row in raw:
        if not isinstance(row,dict) or not isinstance(row.get('findings'),list):
            converted.append(row);continue
        findings=[]
        for finding in row['findings']:
            try:
                if (not isinstance(finding,dict)
                        or set(finding)!={'observation_event_id','passage_id','interpretation'}
                        or not isinstance(finding['observation_event_id'],str)
                        or not isinstance(finding['passage_id'],str)):
                    raise ValueError('explicit source passage reference required')
                quote=sources[finding['observation_event_id']][finding['passage_id']]
                findings.append(dict(observation_event_id=finding['observation_event_id'],quote=quote,
                    interpretation=finding['interpretation']))
            except (KeyError,TypeError,ValueError):findings.append({'unavailable_passage':True})
        converted.append({**row,'findings':findings})
    result=normalize(converted,inquiries=inquiries,excerpts=excerpts)
    for row in result['entries']:
        original=next(r for r in raw if isinstance(r,dict) and r.get('item_id')==row['item_id'])
        for finding,reference in zip(row['findings'],original['findings']):
            finding['passage_id']=reference['passage_id']
    return result


def validate_references(stored, *, inquiries, excerpts):
    if (not isinstance(stored,dict) or set(stored)!={'entries','unassessed_item_ids','rejected_count'}
            or not isinstance(stored['entries'],list)
            or type(stored['rejected_count']) is not int or not 0<=stored['rejected_count']<=8):
        raise ValueError('invalid retained reference assessment')
    try:
        raw=[{**r,'findings':[{k:f[k] for k in ('observation_event_id','passage_id','interpretation')}
                            for f in r['findings']]} for r in stored['entries']]
    except (KeyError,TypeError):raise ValueError('missing retained passage reference') from None
    normalized=normalize_references(raw,inquiries=inquiries,excerpts=excerpts)
    if normalized['rejected_count'] or any(normalized[k]!=stored[k] for k in ('entries','unassessed_item_ids')):
        raise ValueError('retained source passage changed')
    return stored
