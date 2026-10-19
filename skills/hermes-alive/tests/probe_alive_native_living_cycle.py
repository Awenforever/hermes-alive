"""Real Core/worker/host composition with synthetic historical feedback; no sends.

All model HTTP is intercepted in the test bootstrap. This is lifecycle/privacy
wiring evidence, never real model intelligence, external delivery or installation.
"""
import argparse
import asyncio
from contextlib import ExitStack
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
package=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(package/'hooks'),str(package/'tests'),str(a.core.resolve(strict=True))]

async def main():
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override
    from agent.secret_scope import set_secret_scope,reset_secret_scope,set_multiplex_context,reset_multiplex_context
    from alive_kernel import AutonomyPolicyProjection,DiscoveryCandidate,DiscoveryOpportunityIngestor,ExperienceJournal,PolicyContext,Sensitivity
    from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
    from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
    from alive_kernel.native_cognition_host import NativeCognitionHost
    from alive_kernel.feedback_assimilation import FeedbackAssimilationRuntime
    from alive_kernel.learning_context import CognitionLearningReader
    from probe_alive_live_feedback import prepare_case
    a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    fixture=dict(id='native-living-cycle',sent='Synthetic earlier detailed repair guide.',
        reply='SYNTHETIC_RAW_FEEDBACK: I like repair topics, but I am busy today. Please start with brief points.')
    interpreter,owner,_=prepare_case(a.output/'kernel',fixture)
    journal=interpreter.journal;vault=interpreter.vault
    policies=AutonomyPolicyProjection(journal);current=policies.current(owner)
    policies.apply(policies.append_update(subject=owner,actor=owner,expected_revision=current.revision if current else 0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='enable-synthetic-native-cycle'))
    reader=DiscoveryOpportunityIngestor(journal,content_vault=vault)
    def observe(text):
        return reader.ingest(DiscoveryCandidate(source='synthetic-native-cycle',title='Synthetic repair update',
            summary=text,url='https://example.invalid/living-cycle',observed_at=datetime.now(timezone.utc)),subject=owner)
    observe('Synthetic public repair fact one.')
    protected=('memory.proposed','preference.observed','reflection.reviewed','action.attempted','dispatch.externally_started')
    before={kind:len(journal.read(event_type=kind)) for kind in protected}
    home=a.output/'profile';home.mkdir(mode=0o700)
    workers=a.output/'workers';workers.mkdir(mode=0o700)
    configuration=dict(model=dict(default='configured-primary',provider='custom:owner'),
        custom_providers=[dict(name='owner',model='configured-primary',base_url='https://provider.invalid/v1',
            key_env='OWNER_MAIN_KEY',api_mode='chat_completions')],fallback_providers=[],agent=dict(reasoning_effort=False))
    params=dict(expression_parameters=dict(grounding=True,recipient_meaning=True,require_independent_grounding=False,
        model_timeout_seconds=30,language='en'),resolve_binding=lambda _:None,interpret_feedback=True)
    def wired(host):
        return NativeCognitionHost(host,profile_id='profile:synthetic',profile_home=home,
            read_configuration=lambda:configuration,read_credential_names=lambda **_:('OWNER_MAIN_KEY',),
            interpreter=sys.executable,core=a.core,private_root=workers,environment=dict(os.environ),
            resolve_domain=lambda *labels:'synthetic-shared-family',identity='SYNTHETIC_NATIVE_LIVING_CYCLE',
            entrypoint=package/'tests/fixtures/native-living-cycle-bootstrap.py',timeout_seconds=60,max_calls=16)
    class CrashBeforeClose(AutonomousHostRuntime):
        def close_cycle(self,cycle,result):
            assert result.disposition=='shadow_selected' and result.external_delivery_proven is False
            raise RuntimeError('synthetic crash after completed inner cycle')
    def observations():
        return [json.loads(line) for line in (a.output/'http-observations.jsonl').read_text().splitlines()]
    with ExitStack() as stack:
        token=set_hermes_home_override(home);stack.callback(reset_hermes_home_override,token)
        token=set_multiplex_context(True);stack.callback(reset_multiplex_context,token)
        token=set_secret_scope({'OWNER_MAIN_KEY':'SYNTHETIC_CYCLE_KEY'},profile_home=str(home));stack.callback(reset_secret_scope,token)
        host=CrashBeforeClose(AutonomousCycleRuntime(journal,content_vault=vault),subject=owner,configuration_id='synthetic-living-cycle')
        cycle=host.open_cycle();native=wired(host)
        try:await native.step(params)
        except RuntimeError as error:assert str(error)=='synthetic crash after completed inner cycle'
        else:raise AssertionError('controlled host crash did not occur')
        assert native.last_call_count==8 and not native.pending and not list(workers.iterdir())
        assert journal.get(cycle.event_id+':closed') is None
        first_count=len(observations())
        assert first_count==8
        assert len(journal.read(event_type='feedback.synthesis_completed'))==1
        restarted=ExperienceJournal(journal.path)
        resumed=AutonomousHostRuntime(AutonomousCycleRuntime(restarted,content_vault=vault),
            subject=owner,configuration_id='synthetic-living-cycle')
        resumed_native=wired(resumed)
        result=await resumed_native.step(params)
        assert result.disposition=='shadow_selected' and resumed_native.last_call_count==0
        assert len(observations())==first_count and restarted.get(cycle.event_id+':closed')
        assert not resumed_native.pending and not list(workers.iterdir())
        assert FeedbackAssimilationRuntime(restarted,content_vault=vault).read(subject=owner,clearance=Sensitivity.PRIVATE)
        vault.erase_item('input:fixture')
        assert not FeedbackAssimilationRuntime(restarted,content_vault=vault).read(subject=owner,clearance=Sensitivity.PRIVATE)
        assert not any(item.to_prompt().get('kind')=='tentative_feedback_interpretation'
            for item in CognitionLearningReader(restarted,hypothesis_vault=vault).read(subject=owner,clearance=Sensitivity.PRIVATE))
        observe('Synthetic public repair fact two.')
        result=await resumed_native.step(params)
        assert result.disposition=='shadow_selected' and resumed_native.last_call_count==7
        assert not resumed_native.pending and not list(workers.iterdir())
        trace=observations()
        generated=[item for item in trace if item['stage']=='generation']
        assert len(generated)==2
        assert generated[0]['feedback_hypotheses']==1 and generated[0]['raw_feedback_present'] is True
        assert generated[1]['feedback_hypotheses']==0 and generated[1]['raw_feedback_present'] is False
        assert sum(item['stage']=='feedback' for item in trace)==1
        assert {kind:len(journal.read(event_type=kind)) for kind in protected}==before
    report=dict(controlled_model_calls=len(observations()),actual_model_inference=False,
        real_core_protocol_exercised=True,restart_inference_calls=0,feedback_interpretations=1,
        forgotten_feedback_excluded=True,automatic_profile_writes=0,new_action_attempts=0,
        physical_sends=0,semantic_quality_proven=False,production_installation_proven=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('HERMES_ALIVE_NATIVE_LIVING_CYCLE_OK '+json.dumps(report))
asyncio.run(main())
