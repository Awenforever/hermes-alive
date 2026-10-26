"""Actual Core background-work semantics, synthetic profiles and local artifacts.

No Alive-selected work, configured model or real transport. This nonmanaged
container/CLI topology uses an in-process scheduler worker; its script child
can outlive that process without a terminal receipt. Other fleet topologies
remain unqualified. Do not spoof supervisor markers to obtain another path.
"""
import argparse,json,os,subprocess,sys,tempfile,time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--core',type=Path,required=True)
args=parser.parse_args();sys.path.insert(0,str(args.core))
phase=os.environ.get('ALIVE_JOB_PROBE_PHASE')
if phase:
 home=Path(os.environ['HERMES_HOME']);expected=json.loads((home/'expected.json').read_text()) if (home/'expected.json').exists() else {}
 from cron.jobs import create_job,get_job,trigger_job
 from cron.executions import latest_execution
 if phase=='prepare':
  (home/'scripts').mkdir()
  programs={
   'interrupted':"from pathlib import Path\nimport time\np=Path(__file__).resolve().parent.parent\n(p/'interrupted-started').write_text('started')\ntime.sleep(3)\nwith (p/'interrupted-artifact.txt').open('a') as f:f.write('once\\n')\nprint('completed')\n",
   'actual':"from pathlib import Path\nimport time\ntime.sleep(3)\np=Path(__file__).resolve().parent.parent/'actual-artifact.txt'\np.write_text('observable artifact\\n')\nprint('completed')\n",
   'empty':"print('completed')\n",
   'partial':"from pathlib import Path\np=Path(__file__).resolve().parent.parent/'partial-artifact.txt'\np.write_text('partial effect\\n')\nraise RuntimeError('synthetic failure after partial write')\n"}
  for name,code in programs.items():
   (home/'scripts'/f'{name}.py').write_text(code)
   job=create_job(prompt='',schedule='1h',name='isolated-alive-probe-'+name,repeat=1,
    deliver='local',script=f'{name}.py',no_agent=True,enabled_toolsets=[],paused=True)
   assert get_job(job['id'])['state']=='paused'
   expected[name]=job['id']
  (home/'expected.json').write_text(json.dumps(expected))
 elif phase=='fire':
  from cron.scheduler import tick
  trigger_job(expected['interrupted'])
  assert tick(verbose=False,sync=False,headless=True)==1
  deadline=time.monotonic()+20
  while time.monotonic()<deadline:
   execution=latest_execution(expected['interrupted'])
   if execution and execution['status']=='running' and (home/'interrupted-started').exists():
    (home/'launcher-exit-after-running.json').write_text(json.dumps({'id':execution['id'],'pid':execution['pid'],'status':execution['status']}))
    os._exit(0) # scheduler dies; an already launched script may still mutate its artifact
   time.sleep(.05)
  raise AssertionError('Core execution did not start its actual script')
 elif phase=='verify':
  from cron.scheduler import tick
  from cron.executions import recover_interrupted_executions,list_executions
  deadline=time.monotonic()+10
  while time.monotonic()<deadline and not (home/'interrupted-artifact.txt').exists():time.sleep(.1)
  assert (home/'interrupted-artifact.txt').read_text()=='once\n'
  assert recover_interrupted_executions()==1
  execution=latest_execution(expected['interrupted'])
  assert execution['status']=='unknown',execution
  report={'interrupted':{'core_status':execution['status'],'artifact_satisfied':True,'launcher_exited':True}}
  for name in ('actual','empty','partial'):
   trigger_job(expected[name]);assert tick(verbose=False,sync=True,headless=True)==1
   result=latest_execution(expected[name]);assert result and result['status'] in ('completed','failed'),result
   report[name]={'core_status':result['status'],'artifact_exists':(home/f'{name}-artifact.txt').exists()}
  assert (home/'actual-artifact.txt').read_text()=='observable artifact\n'
  assert report['empty']=={'core_status':'completed','artifact_exists':False},report
  assert report['partial']=={'core_status':'failed','artifact_exists':True},report
  assert len(list_executions(job_id=expected['interrupted']))==1
  before=(home/'actual-artifact.txt').read_bytes()
  assert tick(verbose=False,sync=True,headless=True)==0
  assert (home/'actual-artifact.txt').read_bytes()==before
  assert (home/'interrupted-artifact.txt').read_text()=='once\n'
  assert len(list_executions(job_id=expected['interrupted']))==1
  (home/'report.json').write_text(json.dumps(report))
  print(json.dumps(report))
 print('CORE_JOB_PHASE_OK='+phase)
else:
 with tempfile.TemporaryDirectory(prefix='alive-core-job-proof-') as root:
  home=Path(root)/'profile';home.mkdir();(home/'config.yaml').write_text('plugins:\n  enabled: []\n')
  env={**os.environ,'HOME':root,'HERMES_HOME':str(home),'PYTHONPATH':str(args.core),'PYTHONDONTWRITEBYTECODE':'1'}
  for step in ('prepare','fire','verify'):
   result=subprocess.run([sys.executable,'-B',__file__,'--core',str(args.core)],env={**env,'ALIVE_JOB_PROBE_PHASE':step},capture_output=True,text=True,timeout=90)
   assert result.returncode==0,step+'\n'+result.stdout+'\n'+result.stderr
   if step!='fire':assert 'CORE_JOB_PHASE_OK='+step in result.stdout,result.stdout
  print((home/'report.json').read_text())
 print('HERMES_ALIVE_CORE_BACKGROUND_WORK_OK')
