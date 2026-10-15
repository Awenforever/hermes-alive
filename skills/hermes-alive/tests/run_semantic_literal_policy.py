"""Versioned exact literals versus semantic polarity; never delivery approval."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.semantic_rendering import (SemanticAtom, SemanticAtomKind, LiteralPolicy,
    MeaningDocument, MessageSpeechAct, Sensitivity, SemanticRenderingError,
    serialize_meaning, deserialize_meaning, assess_fidelity, RendererClass, FidelityStatus)
from alive_kernel.semantic_review import (IndependentSemanticReview, AtomReview, SemanticRisk,
    ReviewerKind, assess_independent_review, candidate_digest, ReviewDisposition)
from alive_kernel.communication_plan import validate_communication_plan, plan_atoms


def rejected(call):
    try: call()
    except (ValueError,TypeError): return
    raise AssertionError('invalid literal policy accepted')


def main():
    now=datetime.now(timezone.utc)
    legacy=SemanticAtom('negation',SemanticAtomKind.NEGATION,'不对公众开放',('source:synthetic',),('不对公众开放',))
    old=MeaningDocument('meaning:old','user:test',MessageSpeechAct.INFORM,(legacy,),now,now+timedelta(hours=1))
    serialized=serialize_meaning(old)
    assert serialized['schema_version']==1 and 'literal_policy' not in serialized['atoms'][0]
    assert deserialize_meaning(serialized)==old
    semantic=SemanticAtom('negation',SemanticAtomKind.NEGATION,'不对公众开放',('source:synthetic',),(),LiteralPolicy.SEMANTIC)
    uncertain=SemanticAtom('uncertainty',SemanticAtomKind.UNCERTAINTY,'可能需要预约',('source:synthetic',),(),LiteralPolicy.SEMANTIC)
    new=replace(old,message_id='meaning:new',atoms=(semantic,uncertain))
    encoded=serialize_meaning(new)
    assert encoded['schema_version']==2 and deserialize_meaning(encoded)==new
    assert all(a['literal_policy']=='semantic' for a in encoded['atoms'])
    forged=deepcopy(encoded); forged['schema_version']=1
    rejected(lambda:deserialize_meaning(forged))
    forged=deepcopy(encoded); forged['atoms'][0]['literal_policy']='legacy'
    rejected(lambda:deserialize_meaning(forged))
    for kind in (SemanticAtomKind.DEADLINE,SemanticAtomKind.AMOUNT,SemanticAtomKind.LINK,
                 SemanticAtomKind.CONTACT,SemanticAtomKind.FACT):
        rejected(lambda:SemanticAtom('bad',kind,'text',('source:synthetic',),(),LiteralPolicy.SEMANTIC))
    rejected(lambda:SemanticAtom('old',SemanticAtomKind.NEGATION,'not public',('source:synthetic',)))
    for version in (1,2):
        plan=dict(version=version,recipient_goal='说明参加资格',speech_act='inform',
            contents=[dict(kind='negation',text='不对公众开放')],behavior_constraints=[])
        if version==1: rejected(lambda:validate_communication_plan(plan,action_kind='share'))
        else:
            validate_communication_plan(plan,action_kind='share')
            assert plan_atoms(plan,evidence=('source:synthetic',))[0].literal_policy is LiteralPolicy.SEMANTIC
    good='仅受邀者可参加，或许需要先预约。'
    assessment=assess_fidelity(new,good,renderer_class=RendererClass.MODEL_CANDIDATE)
    assert assessment.status is FidelityStatus.REVIEW_REQUIRED and not assessment.fidelity_proven
    review=IndependentSemanticReview(review_id='review:test',meaning_event_id='message.meaning:'+new.message_id,
        candidate_digest=candidate_digest(good),renderer_execution_id='execution:render',renderer_model='family-a/render',
        renderer_independence_domain='a',reviewer_kind=ReviewerKind.MODEL,reviewer_execution_id='execution:review',
        reviewer_model='family-b/review',reviewer_independence_domain='b',
        atom_reviews=(AtomReview('negation',True),AtomReview('uncertainty',True)),
        added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True)
    result=assess_independent_review(new,good,review)
    assert result.disposition is ReviewDisposition.SHADOW_ELIGIBLE and not result.safe_for_automatic_delivery
    reverse='欢迎所有公众参加，无需预约。'
    bad=replace(review,candidate_digest=candidate_digest(reverse),atom_reviews=(
        AtomReview('negation',False,(SemanticRisk.POLARITY_SHIFT,)),
        AtomReview('uncertainty',False,(SemanticRisk.UNCERTAINTY_SHIFT,))))
    assert assess_independent_review(new,reverse,bad).disposition is ReviewDisposition.REJECTED
    exact=replace(semantic,protected_literals=('不对公众开放',))
    exact_document=replace(new,atoms=(exact,))
    assert assess_fidelity(exact_document,good,renderer_class=RendererClass.MODEL_CANDIDATE).status is FidelityStatus.REJECTED
    print('HERMES_ALIVE_SEMANTIC_LITERAL_POLICY_OK')
    return 0


if __name__=='__main__': raise SystemExit(main())
