"""Reading progress is attributed advice, never automatic knowledge or permission."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace as NS

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.reading_assessment import normalize,validate,passages,normalize_references,validate_references
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer,OpportunitySynthesisError

inquiries=[dict(item_id='inquiry:one'),dict(item_id='inquiry:two')]
excerpts={'source:one':'A reported technique. No independent validation was provided.'}
item=dict(item_id='inquiry:one',status='partial',findings=[dict(observation_event_id='source:one',
    quote='A reported technique.',interpretation='The report describes a technique, not independent proof.')],
    open_questions=['Was it independently tested?'])
def parse(raw):return normalize(raw,inquiries=inquiries,excerpts=excerpts)
value=parse([item]);assert value['entries']==[item] and value['unassessed_item_ids']==['inquiry:two']
assert validate(value,inquiries=inquiries,excerpts=excerpts)==value
item['findings'][0]['interpretation']='changed caller input'
assert value['entries'][0]['findings'][0]['interpretation']!='changed caller input'
item=deepcopy(value['entries'][0])
assert parse(None)['unassessed_item_ids']==['inquiry:one','inquiry:two']
assert parse([item,item])['entries']==[]
for change in (dict(item_id='inquiry:foreign'),dict(status='answered'),dict(status='invented'),
               dict(open_questions=[]),dict(findings=[dict(observation_event_id='source:foreign',quote='A reported technique.',interpretation='No.')]),
               dict(findings=[dict(observation_event_id='source:one',quote='Not actually in the excerpt.',interpretation='No.')] ),
               dict(unrequested='not a policy')):
    result=parse([{**item,**change}]);assert not result['entries'] and result['rejected_count']==1
unresolved=dict(item_id='inquiry:two',status='unresolved',findings=[],open_questions=['No evidence answers this yet.'])
assert parse([unresolved])['entries']==[unresolved]
answered={**item,'status':'answered','open_questions':[]}
assert parse([answered])['entries']==[answered]
# Even a valid exact quotation does not prove the model interpretation true.
assert parse([{**answered,'findings':[dict(observation_event_id='source:one',
    quote='A reported technique.',interpretation='A tentative interpretation, not a proven fact.')]}])['entries']
for changed in ({**value,'rejected_count':True},{**value,'unassessed_item_ids':[]},
                {**value,'entries':[unresolved]}):
    try:validate(changed,inquiries=inquiries,excerpts=excerpts)
    except ValueError:pass
    else:raise AssertionError('invalid retained reading assessment admitted')
try:OpportunitySynthesizer._validate_recipient_execution(NS(event=NS(payload={'interpreter_method':{}})),
    dict(reading_assessment=value))
except OpportunitySynthesisError:pass
else:raise AssertionError('old operation silently acquired new reading semantics')
# The model selects a reference, never reconstructs PDF typography.
pdf='However, ex-\nisting records are lim-\nited in scope. '+('Original source context. '*60)
units=passages(pdf);assert len(units)>1 and all(len(p['text'])<=560 for p in units)
assert units[0]['text'][-80:]==units[1]['text'][:80]
raw=dict(item_id='inquiry:one',status='partial',findings=[dict(observation_event_id='source:pdf',
    passage_id='p1',interpretation='The source states a limitation, not a factor ranking.')],
    open_questions=['Which factor dominates?'])
scoped={'source:pdf':pdf}
referenced=normalize_references([raw],inquiries=inquiries,excerpts=scoped)
assert referenced['entries'][0]['findings'][0]['quote']==units[0]['text']
assert 'ex-\nisting' in referenced['entries'][0]['findings'][0]['quote']
assert 'quote' not in raw['findings'][0]
assert validate_references(referenced,inquiries=inquiries,excerpts=scoped)==referenced
for finding in ({**raw['findings'][0],'passage_id':'p999'},
                {**raw['findings'][0],'observation_event_id':'source:foreign'},
                {**raw['findings'][0],'quote':'model-supplied replacement'}):
    rejected=normalize_references([{**raw,'findings':[finding]}],inquiries=inquiries,excerpts=scoped)
    assert not rejected['entries'] and rejected['rejected_count']==1
tampered=deepcopy(referenced);tampered['entries'][0]['findings'][0]['quote']='replacement text'
for saved,scope in ((tampered,scoped),(referenced,{'source:pdf':'changed original '+pdf})):
    try:validate_references(saved,inquiries=inquiries,excerpts=scope)
    except ValueError:pass
    else:raise AssertionError('passage reference detached from original text')
# The same repaired wording remains rejected under literal historical v1.
literal={**raw,'findings':[dict(observation_event_id='source:pdf',quote='existing records are limited',
    interpretation='Model repaired typography.') ]}
assert not normalize([literal],inquiries=inquiries,excerpts=scoped)['entries']
print('HERMES_ALIVE_READING_ASSESSMENT_OK')
