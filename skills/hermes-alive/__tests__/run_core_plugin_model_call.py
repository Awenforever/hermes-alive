"""Caller authority/completion contracts with a fake Core facade, never API proof."""
import asyncio
from pathlib import Path
import sys
import tempfile
from types import ModuleType,SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.core_plugin_model_call import CorePluginModelCaller
from alive_kernel.native_worker_protocol import NativeWorkerError
from alive_kernel.core_shadow_assembly import normalize_settings

base=dict(enabled=True,consent='model_calls_no_delivery',subject='user:synthetic')
assert normalize_settings(base)==normalize_settings({**base,'model':None,'max_cycles':1,'interval_seconds':600.0})
for invalid in ({**base,'enabled':False},{**base,'consent':'not-approved'},{**base,'max_cycles':True},
                {**base,'interval_seconds':float('nan')},{**base,'model':''}):
    try:normalize_settings(invalid)
    except ValueError:pass
    else:raise AssertionError('invalid shadow configuration accepted')

async def main(home):
    current_scope=[{}];config=[b'synthetic-config'];entered=asyncio.Event();release=asyncio.Event()
    constants=ModuleType('hermes_constants');constants.get_hermes_home=lambda:home
    secrets=ModuleType('agent.secret_scope');secrets.current_secret_scope=lambda:current_scope[0]
    def reply(finish='stop',fields=True):
        message=NS(role='assistant',content='{"ok":true}',tool_calls=[],model_fields_set={'role','content'})
        choice=NS(index=0,message=message,finish_reason=finish,model_fields_set={'message','finish_reason'} if fields else set())
        return NS(model='synthetic-served',choices=[choice],model_fields_set={'model','choices'})
    class Facade:
        response=reply();blocked=False;calls=0;alter_text=False
        def _gate(self,*args):
            assert args[-1] is None,'stage deadline must not override Core request timeout'
            if args[1]=='denied':raise PermissionError('synthetic Core override refusal')
            return None,{}
        async def _invoke_async(self,kw):
            self.calls+=1;entered.set()
            if self.blocked:await release.wait()
            return 'synthetic-provider',self.response.model,self.response
        def _finish(self,*args):
            return NS(text='altered' if self.alter_text else self.response.choices[0].message.content,
                provider='synthetic-provider',model='synthetic-served')
    facade=Facade();context=NS(llm=facade,_manager=NS(scope_key=str(home)))
    def caller():return CorePluginModelCaller(context,read_binding=lambda:'synthetic-binding')
    params=dict(task='synthetic-task',model=None,messages=[{'role':'user','content':'synthetic'}],
        temperature=.1,max_tokens=128)
    modules={'hermes_constants':constants,'agent':ModuleType('agent'),'agent.secret_scope':secrets}
    with patch.dict(sys.modules,modules),patch.object(CorePluginModelCaller,'_configuration',lambda self:config[0]):
        c=caller();route={};result=await c(route_info=route,**params)
        assert result.model=='synthetic-served' and route['provider']=='synthetic-provider'
        before=facade.calls
        try:await caller()(**{**params,'model':'denied'})
        except PermissionError:pass
        else:raise AssertionError('override gate bypassed')
        assert facade.calls==before
        for response in (reply('length'),reply('content_filter'),reply(None),reply(fields=False)):
            facade.response=response
            try:await caller()(**params)
            except NativeWorkerError:pass
            else:raise AssertionError('incomplete or synthesized completion admitted')
        facade.response=reply();facade.alter_text=True
        try:await caller()(**params)
        except NativeWorkerError:pass
        else:raise AssertionError('facade/native wording mismatch admitted')
        facade.alter_text=False;facade.blocked=True;entered.clear()
        c=caller();active=asyncio.create_task(c(**params));await entered.wait()
        try:await c(**params)
        except NativeWorkerError:pass
        else:raise AssertionError('overlapping request admitted')
        config[0]=b'changed-config';release.set()
        try:await active
        except NativeWorkerError:pass
        else:raise AssertionError('stale currentness admitted')
        assert not c.pending
        release.clear();c=caller()
        try:await c(**{**params,'timeout':.01})
        except TimeoutError:pass
        else:raise AssertionError('deadline not enforced')
        assert not c.pending

with tempfile.TemporaryDirectory(prefix='alive-core-model-call-') as folder:
    asyncio.run(main(Path(folder)))
print('HERMES_ALIVE_CORE_PLUGIN_MODEL_CALL_UNIT_OK')
