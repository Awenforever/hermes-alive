"""Host citation identities and candidate-local optional failures; no IO/models."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.citation_selection import citations,normalize,validate,read_targets
from alive_kernel.host_discovery import HostDiscoveryError

text=('PDF project https://EXAMPLE.invalid/Project. '
      '[method](https://example.invalid/Paper_(method)?version=2) '
      '<https://example.invalid/another> '
      'https://user:secret@example.invalid/private '
      'https://example.invalid/already?utm_source=fixture#part '
      'https://example.invalid/bare_(ambiguous)')
links=citations(text,('https://example.invalid/already',))
assert [x['url'] for x in links]==[
    'https://EXAMPLE.invalid/Project.',
    'https://example.invalid/Paper_(method)?version=2',
    'https://example.invalid/another']
assert all(text[x['start']:x['end']]==x['url'] for x in links)
assert len(citations(' '.join('https://example.invalid/'+str(i) for i in range(80))))==32
assert citations('[incomplete](https://example.invalid/unclosed')==[]
catalogs={'source-a':links,'source-b':citations('https://EXAMPLE.invalid/Project.')}
def choose(targets):return dict(read_targets=targets,reason='Investigate an unresolved claim.')
valid=dict(source_ref='source-a',citation_ref='link1')
invalid=dict(source_ref='source-a',citation_ref='not-supplied')
mixed=normalize(choose([valid,invalid]),catalogs)
assert mixed['decision_status']=='selected' and mixed['rejected_count']==1
assert read_targets(mixed,catalogs)==(dict(source_ref='source-a',url=links[0]['url']),)
assert normalize(choose([]),catalogs)['decision_status']=='abstained'
for targets in ([invalid],[dict(source_ref='foreign',citation_ref='link1')],
                [dict(source_ref='source-a',url='https://example.invalid/Project')],
                [dict(source_ref='source-a',citation_ref=True)]):
    result=normalize(choose(targets),catalogs)
    assert result['decision_status']=='invalid' and result['rejected_count']==1
    assert not read_targets(result,catalogs)
for raw in (None,{},choose([valid]*3),dict(read_targets=[],reason=False)):
    result=normalize(raw,catalogs)
    assert result['decision_status']=='invalid' and not read_targets(result,catalogs)
duplicate=normalize(choose([valid,dict(source_ref='source-b',citation_ref='link1')]),catalogs)
assert duplicate['read_targets']==[valid] and duplicate['rejected_count']==1
assert validate(mixed,catalogs)==mixed
for value,source in (({**mixed,'rejected_count':True},catalogs),
        ({**mixed,'decision_status':'abstained'},catalogs),
        (mixed,{}),({**mixed,'read_targets':[invalid]},catalogs)):
    try:validate(value,source)
    except HostDiscoveryError:pass
    else:raise AssertionError('changed retained selection accepted')
print('HERMES_ALIVE_CITATION_SELECTION_OK')
