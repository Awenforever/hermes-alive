"""Actual Core queued-work deactivation and reload controls, synthetic data.

No real model, private history, channel send or daemon admission is qualified.
The autonomous-work fixture supplies the real signed handoff and Core worker.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


async def qualify(*,binding,manager,home,work,state,store,command,jobs,tick,
                  artifact,actual_body,work_requests,cli):
    action=os.environ['ALIVE_RETIREMENT_ACTION']
    assert action in ('disable','cli-disable','pause','uninstall','reload','upgrade')
    assert not artifact.exists() and not work_requests
    assert work.status(state['work_id'],subject=store.configuration().subject).get(
        'core_execution_state') not in ('claimed','running','completed')
    marker=home/'existing-result.txt';marker.write_text('keep prior result',encoding='utf-8')
    unowned=jobs.create_job('Unrelated public synthetic future work','1d',
        name='alive-'+'f'*32,deliver='local',enabled_toolsets=[])
    # A matching job name is neither ownership nor authority to cancel it.
    unowned_before=jobs.get_job(unowned['id'])
    keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
    digests={name:hashlib.sha256((store.root/name).read_bytes()).hexdigest() for name in keys}
    if action=='pause':
        answer=await command('pause');assert '已暂停' in answer,answer
        observed=binding.runtime_status()['core_work_retirement']
    elif action=='cli-disable':
        rc,answer=await asyncio.to_thread(cli,home,'disable');assert rc==0,answer
        observed=answer['core_work_retirement'];assert not observed['needs_attention'],observed
    elif action=='uninstall':
        rc,answer=await asyncio.to_thread(cli,home,'uninstall-runtime');assert rc==0,answer
        observed={'status':'uninstall_completed'}
        assert not (home/'hooks/hermes-alive').exists()
    else:
        if action=='disable':
            import yaml
            path=home/'config.yaml';selected=yaml.safe_load(path.read_text(encoding='utf-8'))
            selected['plugins']['enabled']=[];selected['plugins']['disabled']=['hermes-alive']
            path.write_text(yaml.safe_dump(selected,allow_unicode=True,sort_keys=False),encoding='utf-8')
        if action=='upgrade':
            rc,answer=await asyncio.to_thread(cli,home,'install-runtime','--engine','kernel')
            assert rc==0,answer
        assert manager.unload('hermes-alive') and binding.closed
        observed=getattr(binding,'_core_retirement_status',None)
        if action in ('reload','upgrade'):assert observed is None,observed
        else:
            assert observed and not observed['needs_attention'],observed
            assert observed['owned_work_count']==1,observed
    count=await asyncio.to_thread(tick,verbose=False,sync=True,headless=False)
    after=work.status(state['work_id'],subject=store.configuration().subject)
    if action in ('reload','upgrade'):
        assert count==1 and artifact.read_text(encoding='utf-8')==actual_body
        assert work_requests and not after.get('owner_stop_requested')
    else:
        assert count==0 and not artifact.exists() and not work_requests,(count,after)
        assert after['owner_stop_requested'] is True
        job=jobs.get_job(state['job_id']);assert job['state']=='paused' and job['enabled'] is False
    assert marker.read_text(encoding='utf-8')=='keep prior result'
    assert jobs.get_job(state['job_id']) is not None
    assert jobs.get_job(unowned['id'])==unowned_before
    assert digests=={name:hashlib.sha256((store.root/name).read_bytes()).hexdigest() for name in keys}
    result={'action':action,'work_id':state['work_id'],'job_id':state['job_id'],
        'retirement':observed,'worker_requests':len(work_requests),
        'kernel_root':str(store.root),'keys':digests,'artifact':str(artifact),
        'existing_result_preserved':True,'core_job_preserved':True,'external_deliveries':0}
    result['unowned_job_id']=unowned['id'];result['unowned_job']=unowned_before
    (home/'retirement-proof.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('CORE_RETIREMENT_ACTION_PROVEN '+action,flush=True)


def cold(home):
    from cron.jobs import get_job
    proof=json.loads((home/'retirement-proof.json').read_text(encoding='utf-8'))
    job=get_job(proof['job_id']);assert job is not None
    assert get_job(proof['unowned_job_id'])==proof['unowned_job']
    stopping=proof['action'] not in ('reload','upgrade')
    assert (job['state']=='paused' and job['enabled'] is False) if stopping else job['state']=='completed'
    assert Path(proof['artifact']).exists() is (not stopping)
    assert (home/'existing-result.txt').read_text(encoding='utf-8')=='keep prior result'
    assert proof['keys']=={name:hashlib.sha256((Path(proof['kernel_root'])/name).read_bytes()).hexdigest()
                           for name in proof['keys']}
    print('CORE_RETIREMENT_COLD_PROVEN '+proof['action'],flush=True)


async def qualify_running(*,binding,manager,home,store,execution,command,started,configured,
                          stop_release,clock,artifact,work_store):
    from contextlib import nullcontext
    from unittest.mock import patch
    action=os.environ['ALIVE_RETIRE_RUNNING']
    assert action in ('pause','disable','unknown') and clock is not None
    async def unavailable(*args,**kwargs):raise TimeoutError('synthetic cancellation answer lost')
    control=execution.kernel('core_work_control').CoreWorkControl
    fault=patch.object(control,'_cancel_owner',unavailable) if action=='unknown' else nullcontext()
    try:
        with fault:
            if action=='disable':
                import yaml
                path=home/'config.yaml';selection=yaml.safe_load(path.read_text(encoding='utf-8'))
                selection['plugins']['enabled']=[];selection['plugins']['disabled']=['hermes-alive']
                path.write_text(yaml.safe_dump(selection,allow_unicode=True,sort_keys=False),encoding='utf-8')
                assert manager.unload('hermes-alive') and binding.closed
                task=getattr(binding,'_core_retirement_task',None)
                assert task is not None,'running Core cancellation was not scheduled'
                await asyncio.wait_for(asyncio.shield(task),30)
            else:
                answer=await command('pause');assert '已暂停' in answer,answer
            observed=binding._core_retirement_status
            assert observed['effects_undone'] is False and observed['results_deleted'] is False
            if action=='unknown':
                assert observed['needs_attention'] and observed['core_cancellation_acknowledged_count']==0,observed
                count=len(list(store.journal.read(event_type='work.stop_dispatch_started')))
                again=await command('pause');assert '尚未确认' in again,again
                assert len(list(store.journal.read(event_type='work.stop_dispatch_started')))==count==1
            else:
                assert observed['core_cancellation_acknowledged_count']==1,observed
    finally:
        stop_release.set()
        await clock
    assert not artifact.exists(),'stopped worker produced a new file'
    current=work_store.status(started['work_id'],subject=configured.subject)
    assert current['owner_stop_requested'] and current.get('core_execution_state') not in ('claimed','running')
    keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
    (home/'stop-expected.json').write_text(json.dumps({'work_id':started['work_id'],
        'owner':configured.subject,'artifact':str(artifact),
        'keys':{name:hashlib.sha256((store.root/name).read_bytes()).hexdigest() for name in keys}}),encoding='utf-8')
    print('CORE_RUNNING_RETIREMENT_PROVEN '+action+' '+json.dumps(observed,sort_keys=True),flush=True)


if __name__=='__main__':
    if os.environ.get('ALIVE_RETIREMENT_COLD')=='1':
        import run_core_session_routing  # admits the explicitly supplied Core path
        cold(Path(os.environ['HERMES_HOME']))
    else:
        with tempfile.TemporaryDirectory(prefix='alive-core-retirement-') as directory:
            for action in ('disable','cli-disable','pause','uninstall','reload','upgrade'):
                env={**os.environ,'HOME':directory,'HERMES_HOME':str(Path(directory)/action),
                     'ALIVE_AUTOWORK_CHILD':'1','ALIVE_AUTOWORK_CASE':'execute',
                     'ALIVE_RETIREMENT_ACTION':action,'PYTHONDONTWRITEBYTECODE':'1'}
                try:
                    for script,extra in (('run_core_autonomous_work.py',{}),
                                         ('run_core_work_retirement.py',{'ALIVE_RETIREMENT_COLD':'1'})):
                        result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name(script)),*sys.argv[1:]],
                            env={**env,**extra},capture_output=True,text=True,timeout=300)
                        assert result.returncode==0,action+'\n'+result.stdout+'\n'+result.stderr
                        print(result.stdout,flush=True)
                finally:
                    result=subprocess.run([sys.executable,'-B','-m','hermes_cli.main','gateway','stop'],
                        env=env,capture_output=True,text=True,timeout=30)
                    assert result.returncode==0,result.stderr
        print('HERMES_ALIVE_CORE_WORK_RETIREMENT_OK')
