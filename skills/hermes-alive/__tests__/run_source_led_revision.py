"""Whole source-led fit revision, one-slot recovery, abstention and erasure."""
import argparse
import asyncio
import copy
from dataclasses import replace
from pathlib import Path
import tempfile
from unittest.mock import patch

from run_discovery_authoring import exercise
from alive_kernel import ExperienceJournal
from alive_kernel.events import _thaw_json
from alive_kernel.expression_support import ExpressionSourceSupportReviewer
from alive_kernel.source_support import SourceSupportError
from alive_kernel.final_value_findings import combine
from alive_kernel.source_revision import eligible, revised_text, METHOD
from alive_kernel.review_contracts import FACTS_AND_FIT_ASSESSMENT


def pure():
    findings=combine({'factual_support':{'assessment':'supported','reason':'Attributed source.'},
        'communication_fit':{'assessment':'conflicts','reason':'Wrong whole form.','recipient_evidence':[]}})
    context={'findings':findings,'grounding_context':{
        'expression_binding':{'final_assessment_scope':FACTS_AND_FIT_ASSESSMENT},
        'assessment_scope':{'kind':'final_discovery_source_and_value'},'evidence':[{'source':'synthetic'}]}}
    assert eligible(context)
    for alteration in ('missing-source','protected-purpose','legacy','fits','only-factual','uncertain','malformed'):
        value=copy.deepcopy(context)
        if alteration=='missing-source':value['grounding_context']['evidence']=[]
        if alteration=='protected-purpose':value['grounding_context']['assessment_scope']['kind']='final_source_and_recipient_purpose'
        if alteration=='legacy':value['grounding_context']['expression_binding'].clear()
        if alteration in ('fits','only-factual','uncertain'):
            value['findings']=combine({'factual_support':{'assessment':'unsupported' if alteration=='only-factual' else 'supported','reason':'Source assessment.'},
                'communication_fit':{'assessment':'uncertain' if alteration=='uncertain' else 'fits','reason':'Actual context.','recipient_evidence':[]}})
        if alteration=='malformed':value['grounding_context']['expression_binding']=None
        assert not eligible(value)
    assert revised_text({'text':'A new opening. exact-source'},protected_literals=('exact-source',))=='A new opening. exact-source'
    for value in ({'abstain':True},{'abstain':1},{'text':'lost the source'},{'text':''},{'text':'x','edits':[]}):
        try:revised_text(value,protected_literals=('exact-source',))
        except ValueError:pass
        else:raise AssertionError('invalid revision or literal loss admitted')


async def test(root,mode):
    await exercise(root,'repair',fit_revision=mode)
    journal=ExperienceJournal(root/'journal.sqlite3')
    starts=[r for r in journal.read(event_type='expression.runtime_started') if 'correction_method' in r.event.payload]
    assert len(starts)==1 and starts[0].event.payload['correction_method']==METHOD
    if mode in ('abstain','erase'):
        assert not journal.read(event_type='expression.source_revision_completed')
        return
    proof=journal.read(event_type='expression.source_revision_completed')[0]
    reviewer=ExpressionSourceSupportReviewer(journal)
    candidate=reviewer.expressions.resolve_model_candidate(proof.event.causation_id)
    assert candidate is not None
    args=dict(subject='user:test',selection_event_id=candidate.selection_event_id)
    assert reviewer.current_correction_binding(candidate,**args)
    get=journal.get
    for mutation in ({'result_text_digest':'0'*64},{'method':'review-anchored-edits-v1'},
                     {'delivery_authority_granted':True}):
        data=_thaw_json(proof.event.payload);data.update(mutation)
        forged=replace(proof,event=replace(proof.event,payload=data))
        with patch.object(journal,'get',side_effect=lambda identity:forged if identity==proof.event.event_id else get(identity)):
            try:reviewer.current_correction_binding(candidate,**args)
            except SourceSupportError:pass
            else:raise AssertionError('tampered revision proof admitted')
    assert not journal.read(event_type='action.attempted')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=('success','reject-again','abstain','erase'))
    selected=parser.parse_args().case
    pure()
    with tempfile.TemporaryDirectory(prefix='alive-source-revision-') as d:
        for mode in ((selected,) if selected else ('success','reject-again','abstain','erase')):
            root=Path(d)/mode;root.mkdir();asyncio.run(test(root,mode))
    print('SOURCE_LED_REVISION_OK')
