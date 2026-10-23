"""Reading progress is attributed advice, never automatic knowledge or permission."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace as NS

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.reading_assessment import normalize,validate
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
print('HERMES_ALIVE_READING_ASSESSMENT_OK')
