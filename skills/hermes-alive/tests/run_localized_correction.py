"""Pure local-edit invariants, not semantic quality or installed repair evidence."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.localized_correction import bind_spans,apply_replacements,text_digest,LocalCorrectionError,apply_correction

original='开头保持。\n\n来源甲只支持数字一；来源乙支持数字二。\n\n结尾保持，链接 https://example.invalid/original'
digest=text_digest(original);claims=['数字二被错归来源甲。']
targets=[dict(exact_text='来源乙',claim_index=0)]
spans=bind_spans(original,expected_digest=digest,unsupported_claims=claims,targets=targets)
assert len(spans)==1 and original[spans[0].start:spans[0].end]=='来源乙'
def apply(response,*,text=original,expected=digest,locations=targets,issues=claims,protected=()):
    return apply_replacements(text,expected_digest=expected,unsupported_claims=issues,
        targets=locations,response=response,protected_literals=protected)
response=dict(replacements=[dict(span_id='span1',replacement='报道乙')])
expected=original.replace('来源乙','报道乙')
assert apply(response,protected=('https://example.invalid/original',))==expected
assert apply(response)==expected  # Same input reopens deterministically; no side effects.
for left,right in ((0,spans[0].start),(spans[0].end,len(original))):
    # Exact offsets are recomputed from immutable original, not a model's numbers.
    assert original[left:right] in expected
assert apply(dict(replacements=[dict(span_id='span1',replacement='')]))==original.replace('来源乙','')
unicode='前缀 👩🏽‍💻。\n\n原始 e\u0301 片段\n\n尾部不变。'
fixed=apply(dict(replacements=[dict(span_id='span1',replacement='新的 é 片段')]),text=unicode,
    expected=text_digest(unicode),locations=[dict(exact_text='原始 e\u0301 片段',claim_index=0)])
assert fixed.startswith('前缀 👩🏽‍💻。\n\n') and fixed.endswith('\n\n尾部不变。')

def reject(call):
    try:call()
    except LocalCorrectionError:pass
    else:raise AssertionError('invalid or widened correction accepted')

for bad in ({'abstain':True},{},dict(replacements=[]),
        dict(replacements=[dict(span_id='span2',replacement='wrong')]),
        dict(replacements=[dict(span_id='span1',replacement=True)]),
        dict(replacements=response['replacements']*2),
        dict(replacements=[dict(span_id='span1',replacement='x',start=0)])):
    reject(lambda bad=bad:apply(bad))
reject(lambda:apply(response,text=original+'later change'))
reject(lambda:apply(response,expected='0'*64))
for bad in ([],[dict(exact_text='not present',claim_index=0)],
        [dict(exact_text=original,claim_index=0)],
        [dict(exact_text='来源乙',claim_index=True)],
        [dict(exact_text='来源乙',claim_index=1)],
        [dict(exact_text='来源乙',claim_index=0,start=0)],
        [dict(exact_text='来源乙',claim_index=0),dict(exact_text='来源乙支持',claim_index=0)]):
    reject(lambda bad=bad:apply(response,locations=bad))
reject(lambda:apply(response,issues=claims+['another unlocalized claim']))
reject(lambda:apply(response,text='重复。重复。',expected=text_digest('重复。重复。'),
    locations=[dict(exact_text='重复',claim_index=0)]))
reject(lambda:apply(response,text='aaaa',expected=text_digest('aaaa'),
    locations=[dict(exact_text='aaa',claim_index=0)]))  # count() misses overlapping occurrences.
reject(lambda:apply(dict(replacements=[dict(span_id='span1',replacement='removed')]),
    locations=[dict(exact_text='https://example.invalid/original',claim_index=0)],
    protected=('https://example.invalid/original',)))
multi=[dict(exact_text='数字二',claim_index=1),dict(exact_text='数字一',claim_index=0)]
fixed=apply(dict(replacements=[dict(span_id='span2',replacement='数字甲'),dict(span_id='span1',replacement='数字乙')]),
    locations=multi,issues=['first issue','second issue'])
assert fixed==original.replace('数字一','数字甲').replace('数字二','数字乙')
findings=dict(verdict='unsupported',unsupported_claims=claims,uncertainties=[],reason='Structural fixture only.')
proposal=dict(edits=[dict(exact_text='来源乙',claim_index=0,replacement='报道乙')])
def correct(value,assessment=findings):
    return apply_correction(original,expected_digest=digest,findings=assessment,response=value,
        protected_literals=('https://example.invalid/original',))
assert correct(proposal)==expected
assert correct(proposal,dict(verdict='uncertain',unsupported_claims=[],uncertainties=claims))==expected
for bad in ({'abstain':True},dict(edits=[]),dict(edits=[dict(proposal['edits'][0],start=0)]),
        dict(edits=[dict(exact_text='来源乙',claim_index=0,replacement='来源乙')])):
    reject(lambda bad=bad:correct(bad))
reject(lambda:correct(proposal,dict(findings,verdict='supported')))
reject(lambda:correct(proposal,dict(findings,uncertainties=['uncovered uncertainty'])))
reject(lambda:text_digest('坏\ud800编码'))
reject(lambda:text_digest('汉'*86000))
large='字'*25000+' old suffix'
assert apply_correction(large,expected_digest=text_digest(large),findings=findings,
    response=dict(edits=[dict(exact_text='old',claim_index=0,replacement='new')]))==large.replace('old','new')
print('HERMES_ALIVE_LOCALIZED_CORRECTION_OK')
