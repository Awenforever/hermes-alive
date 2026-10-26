"""Actual installed Core setup/control with source-free agenda cycles.

Owner admission uses the real Core command, main-turn collector and tool
dispatcher. Language interpretation/model replies and adapter are controlled.
This proves native wiring, not real-model quality or live sending.
"""
import asyncio,importlib,json,shutil,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import run_core_session_routing as core
from run_core_guided_setup import cli

async def test(home):
 home.mkdir();shutil.copytree(core.repo,home/'plugins/hermes-alive')
 config={'plugins':{'enabled':['hermes-alive']},'model':{'provider':'custom:owner','default':'configured-primary'},
  'custom_providers':[{'name':'owner','model':'configured-primary','base_url':'https://provider.invalid/v1','key_env':'OWNER_MAIN_KEY','api_mode':'chat_completions'}],
  'agent':{'reasoning_effort':False}}
 (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8');(home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_OWNER_KEY\n')
 rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention','--language','zh-CN')
 assert rc==0 and staged['confirmation_summary']['public_queries']==[]
 assert cli(home,'install-runtime','--engine','kernel')[0]==0
 token=core.set_hermes_home_override(home);manager=None;sent=[];requests=[];reads=[]
 try:
  import httpx
  from hermes_cli.plugins import get_plugin_command_handler
  from tools.registry import registry
  manager=core.get_plugin_manager();manager.discover_and_load();loaded=manager._plugins['hermes-alive']
  assert loaded.enabled and not loaded.error
  binding=loaded.module._gateway_host_binding
  execution=importlib.import_module(loaded.module.__name__+'.kernel_execution_bridge')
  setup=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge')
  class Adapter(core.Adapter):
   async def send(self,chat_id,content,**kwargs):
    assert chat_id=='-1007654321' and kwargs['metadata']['model_name']=='configured-primary'
    sent.append(content);return SimpleNamespace(success=True,message_id='source-free-reminder')
  adapter=Adapter(core.Platform.TELEGRAM);runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter});adapter.gateway_runner=runner
  await adapter.connect()
  source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='-1007654321',user_id='source-free-owner',message_id='source-free-confirm')
  entry=runner.session_store.get_or_create_session(source);handler=get_plugin_command_handler('alive')
  async def command(args):return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=args)
  assert '已确认' in await command(staged['confirmation_command'].removeprefix('/alive '))
  store=setup.setup_store(binding);owner=store.configuration().subject
  def forbidden(args,**kwargs):
   reads.append(args);raise AssertionError('source-free Alive attempted a public read')
  for name in ('web_search','web_extract'):
   registry.register(name=name,toolset='web',schema={'name':name,'description':'Forbidden public reads','parameters':{'type':'object'}},handler=forbidden,override=True,scope=str(home))
  due=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
  def respond(request):
   if not request.url.path.endswith('/chat/completions'):return httpx.Response(503,request=request,json={'error':{'message':'synthetic metadata unavailable'}})
   assert request.url.host=='provider.invalid'
   body=json.loads(request.content);raw=next(m['content'] for m in body['messages'] if m['role']=='user')
   try:data=json.loads(raw)
   except ValueError:data=json.loads(raw.split('\n',1)[1])
   if isinstance(data,list):
    stage='select';value={'candidate_id':next(v['candidate_id'] for v in data if v['candidate_id'].startswith('opportunity-candidate:')),'rationale':'Synthetic reminder selection'}
   elif 'opportunities' in data:
    stage='interpret'
    if not data['opportunities']:value={'candidates':[]}
    else:
     item=data['opportunities'][0]
     assert item['origin_kind']=='commitment' and item['url']==''
     assert item['communication_situation']['kind']=='admitted_commitment'
     assert '只提醒，不代为提交' in item['summary_excerpt']
     value={'candidates':[{'agenda_item_id':item['agenda_item_id'],'kind':'share','topic':'owner commitment',
      'communication_plan':{'version':2,'recipient_goal':'提醒用户核对实验记录','speech_act':'remind',
       'contents':[{'kind':'request','text':'请核对实验记录。'},{'kind':'deadline','text':'截止：'+due,'protected_literals':[due]}],
       'behavior_constraints':['只提醒，不代为提交']},
      'dimensions':{n:{'value':.05 if n in ('risk','interruption_cost') else .9,'reason':'Synthetic assessment'} for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}
   elif 'expression_binding' in data:
    stage='final';value={'verdict':'supported','unsupported_claims':[],'uncertainties':[],'reason':'Synthetic purpose preserved'}
   elif 'meaning' in data and 'candidate' in data:
    stage='boundaries';value={'atom_reviews':[{'atom_id':v['atom_id'],'preserved':True,'risks':[]} for v in data['meaning']['atoms']],
     'added_claims_detected':False,'speech_act_preserved':True,'protected_literals_preserved':True}
   elif 'meaning' in data:
    stage='author';assert data['meaning']['speech_act']=='remind';value='请核对实验记录。截止：'+due
   elif 'candidate' in data and 'evidence' in data:
    stage='purpose';assert data['evidence'][0]['provenance_metadata']['origin_kind']=='commitment'
    value={'verdict':'supported','unsupported_claims':[],'uncertainties':[],'reason':'Synthetic owner commitment'}
   else:raise AssertionError('unexpected source-free stage '+str(list(data)))
   requests.append(stage)
   return httpx.Response(200,request=request,json={'id':'source-free-fixture','object':'chat.completion','created':0,'model':'configured-primary',
    'choices':[{'index':0,'message':{'role':'assistant','content':value if isinstance(value,str) else json.dumps(value)},'finish_reason':'stop'}],
    'usage':{'prompt_tokens':30,'completion_tokens':30,'total_tokens':60}})
  async def send(client,request,*args,**kwargs):return respond(request)
  with patch.object(httpx.AsyncClient,'send',send),patch.object(httpx.Client,'send',lambda client,request,*args,**kwargs:respond(request)):
   assert '已启用' in await command('enable')
   binding.arguments['stop'].set();await binding.task
   native=binding.native;build=binding.arguments['build_parameters']
   assert not all(callable(getattr(native.preparation,k,None)) for k in ('observe','reason','restore_parameters'))
   assert (await native.step(build())).disposition=='silence'
   count=len(requests)
   assert (await native.step(build())).disposition=='waiting_for_change' and len(requests)==count
   events=execution.kernel('events');agenda_module=execution.kernel('agenda')
   from agent.turn_context import _collect_pre_llm_call_context
   variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
    session_key=entry.session_key,session_id=entry.session_id)
   tool=lambda args,task='source-free-agenda-intake':json.loads(binding.context.dispatch_tool('alive_agenda',args,
    task_id=task,session_id=entry.session_id))
   before=len(store.journal.read())
   try:
    assert 'error' in tool({'operation':'propose','task':'not in a collected main turn'})
    collector=_collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
     platform='telegram',_user_id=source.user_id),effective_task_id='source-free-agenda-intake',turn_id='intake-turn',
     original_user_message='记下核对实验记录这件事，只提醒，不代为提交。',
     messages=[{'role':'user','content':'记下核对实验记录这件事，只提醒，不代为提交。'}],conversation_history=[])
    assert 'alive_agenda' in collector
    drafted=tool({'operation':'propose','task':'核对实验记录','constraint':'只提醒，不代为提交','due_at':due})
    assert drafted['status']=='temporary_proposal_not_saved' and not drafted['external_action_authorized']
    assert 'error' in tool({'operation':'list'},task='foreign-main-task')
    assert 'error' in tool({'operation':'propose','task':'ambiguous time','due_at':'2026-12-01T09:00:00'})
    assert len(store.journal.read())==before,'unconfirmed proposal persisted chat-derived content'
   finally:core.clear_session_vars(variables)
   accept=drafted['confirmation_command'].removeprefix('/alive ')
   preview=json.loads(await command(drafted['preview_command'].removeprefix('/alive ')))
   assert preview['proposal']=={'task':'核对实验记录','constraint':'只提醒，不代为提交'}
   with patch.object(binding._agenda,'DRAFT_TTL',-1):
    assert '已失效' in await command(accept)
   assert len(store.journal.read())==before
   admitted=await command(accept)
   assert '事项已保存' in admitted
   assert '已失效' in await command(accept)
   agenda=agenda_module.AgendaProjection(store.journal)
   items=agenda.list_items(clearance=events.Sensitivity.PRIVATE,subject=owner)
   assert len(items)==1 and items[0].authority.value=='user_explicit'
   proposal=store.journal.get('agenda.proposal:'+items[0].item_id)
   admitted_source=store.journal.get(proposal.event.payload['source_event_ids'][0])
   assert admitted_source.event.source=='hermes.command.alive.agenda' and admitted_source.event.actor==owner
   result=await native.step(build())
   assert result.disposition=='submitted',result.disposition
   assert len(sent)==1 and '核对实验记录' in sent[0] and due in sent[0]
   scope_document=binding._continuity.router.capture_target(session_key=entry.session_key,user_id=source.user_id,platform='telegram').binding_document()
   references=binding._continuity.store.read(scope=scope_document,clearance=events.Sensitivity.PRIVATE)
   assert references and references[-1]['text']==sent[0]
   assert references[-1]['sources'][0]['reading_status']=='retained_original_commitment',references[-1]['sources']
   assert '只提醒，不代为提交' in references[-1]['sources'][0]['excerpt']
   from agent.turn_context import _collect_pre_llm_call_context
   variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
    session_key=entry.session_key,session_id=entry.session_id)
   try:
    messages=[{'role':'user','content':'刚才那件事原先有什么限制？'}]
    original_messages=json.dumps(messages)
    context=_collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
     platform='telegram',_user_id=source.user_id),effective_task_id='source-free-followup',turn_id='source-free-turn',
     original_user_message=messages[-1]['content'],messages=messages,conversation_history=[])
    assert '只提醒，不代为提交' in context and 'historical_request_not_current_status_or_execution_permission' in context
    assert sent[0] in context and json.dumps(messages)==original_messages
   finally:core.clear_session_vars(variables)
   # Missing original storage must not silently replace the agenda's key.
   vault_root=agenda.content_vault.base_dir.resolve();saved_vault=vault_root.with_name(vault_root.name+'-temporarily-unavailable')
   assert home.resolve() in vault_root.parents and not vault_root.is_symlink() and not saved_vault.exists()
   vault_root.rename(saved_vault)
   try:
    assert '未完成操作' in await command('agenda list')
    assert not vault_root.exists(),'agenda command replaced missing retained storage/key'
    missing=binding._continuity.store.read_reference(scope=scope_document,clearance=events.Sensitivity.PRIVATE,
     share_id=references[-1]['share_id'])
    assert missing['sources'][0]['reading_status']=='no_longer_retained'
    assert not vault_root.exists(),'reading replaced missing agenda storage/key'
   finally:saved_vault.rename(vault_root)
   assert not reads and not store.journal.read(event_type='discovery.host_read_started')
   assert 'interpret' in requests and 'author' in requests and 'final' in requests
   assert '已标记完成' in await command('agenda done '+items[0].item_id)
   assert '已结束' in await command('agenda done '+items[0].item_id)
   assert json.loads(await command('agenda list'))['items'][0]['state']=='completed'
   with patch.object(native.host.runtime.outbox,'next_delegated_start',return_value=datetime.now(timezone.utc)):
    assert (await native.step(build())).disposition=='silence'
   assert len(sent)==1 and not reads
   historical=binding._continuity.store.read_reference(scope=scope_document,clearance=events.Sensitivity.PRIVATE,
    share_id=references[-1]['share_id'])
   assert historical['sources'][0]['reference_role']=='historical_request_not_current_status_or_execution_permission'
   ref=execution.kernel('content_vault').ContentReference.from_event_payload(proposal.event.payload['content'])
   agenda.content_vault.erase_item(ref.content_id)
   assert binding._continuity.store.read_reference(scope=scope_document,clearance=events.Sensitivity.PRIVATE,
    share_id=references[-1]['share_id']) is None,'forgotten original request survived through a derived reminder'
   assert '已暂停' in await command('pause')
   assert (await native.step(build())).disposition=='paused' and not native.pending
  print('HERMES_ALIVE_CORE_SOURCE_FREE_AGENDA_OK '+json.dumps({'public_reads':len(reads),'local_reminders':len(sent),'idle_wait_without_repeat':True,'completed_commitment_not_repeated':True,'actual_model_inference':False,'natural_language_intake_proven':False,'external_delivery_proven':False,'stages':requests}))
 finally:
  if manager:manager.unload()
  core.reset_hermes_home_override(token)

if __name__=='__main__':
 with tempfile.TemporaryDirectory(prefix='alive-core-source-free-') as root:
  try:asyncio.run(test(Path(root)/'profile'))
  finally:
   from hermes_state_registry import close_all_under
   close_all_under(root)
