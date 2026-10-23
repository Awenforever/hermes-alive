"""Per-plugin-generation Gateway startup handoff; experimental shadow only."""
import asyncio
import logging
from pathlib import Path


class GatewayHostBinding:
    def __init__(self,context):
        self.context=context
        self.home=Path(context._manager.scope_key).resolve()
        self.native=None
        self.arguments=None
        self.task=None
        self.closed=False
        self.started=False
        self.channels={}
        self.channel_error_class=None
        self._unsubscribe_channels=None
        self._session_routers={}
        self._continuity=None
        context.on_unload(self.close)
        read_config=getattr(context,'get_config',None)
        settings=read_config('kernel_shadow',{}) if callable(read_config) else {}
        setup=read_config('kernel_setup',{}) if callable(read_config) else {}
        if (isinstance(settings,dict) and settings.get('enabled') is True
                or isinstance(setup,dict) and (setup.get('pending_intent_id') or setup.get('activation_event_id'))):
            self._refresh_channels()
            # Core's process-owned listener returns an unsubscribe handle. The
            # plugin owns that handle and removes it even on targeted unload.
            self._unsubscribe_channels=context._manager.on_plugin_loaded(self._refresh_channels)

    def _refresh_channels(self,_summaries=None):
        if self.closed:return
        from .gateway_channel_bridge import register_core_channels
        try:
            self._require_home()
            register_core_channels(self.context,existing=self.channels)
            self.channel_error_class=None
        except Exception as exc:
            # Non-sending shadow work may continue. This is not live readiness;
            # never expose config/credential-bearing exception text.
            self.channel_error_class=type(exc).__name__
            logging.getLogger(__name__).warning('Alive channel capability unavailable: %s',self.channel_error_class)

    def _require_home(self):
        from hermes_constants import get_hermes_home
        if Path(get_hermes_home()).resolve()!=self.home:
            raise ValueError('Gateway binding belongs to another Core profile')

    def session_router(self,platform):
        """Gateway-loop capture only; no recipient, memory or sending grant."""
        self._require_home()
        if self.closed or platform not in self.channels:
            raise ValueError('current connected Core channel required')
        adapter=self.channels[platform].adapter()
        gateway=getattr(adapter,'gateway_runner',None)
        if gateway is None:raise ValueError('Core Gateway routing capability unavailable')
        from .gateway_session_bridge import CoreSessionRouter
        previous=self._session_routers.get(platform)
        if previous is not None:
            from .gateway_session_bridge import SessionScopeUnavailable
            try:old_gateway=previous._current()[0]
            except SessionScopeUnavailable:old_gateway=None
            if old_gateway is gateway:return previous
            previous.close()
        router=CoreSessionRouter(self.context,gateway)
        self._session_routers[platform]=router
        return router

    def attach_continuity(self,store,router,*,clearance,replace=False):
        """Explicit trusted assembly; not an enablement or retention grant."""
        self._require_home()
        if (type(replace) is not bool or self.closed or self._continuity is not None and not replace
                or router not in self._session_routers.values()):
            raise ValueError('current owned Core router and one continuity attachment required')
        from .gateway_conversation_bridge import CoreShareContinuity
        fresh=CoreShareContinuity(store,router,clearance=clearance)
        previous=self._continuity
        if previous is not None:previous.close()
        self._continuity=fresh
        if previous is None:self.context.register_hook('pre_llm_call',self._conversation_context)
        return self._continuity

    def _conversation_context(self,**values):
        if self.closed or self._continuity is None:return None
        try:
            self._require_home()
            return self._continuity.context(**values)
        except Exception as exc:
            logging.getLogger(__name__).warning('Alive conversation context unavailable: %s',type(exc).__name__)
            return None

    def attach(self,native,*,build_parameters,max_cycles,interval_seconds=60):
        """Trusted host assembly, not a user/model-supplied action or permission."""
        self._require_home()
        if (self.closed or self.started or self.native is not None
                or native.host.execute is not False
                or Path(native.acquisition['profile_home']).resolve()!=self.home
                or native.profile_scope is None or not callable(build_parameters)
                or type(max_cycles) is not int or not 1<=max_cycles<=1000
                or type(interval_seconds) not in (int,float) or not 0<=interval_seconds<=86400):
            raise ValueError('explicit current shadow host and bounded lifetime required')
        self.native=native
        self.arguments=dict(build_parameters=build_parameters,stop=asyncio.Event(),
            max_cycles=max_cycles,interval_seconds=interval_seconds)

    def runtime_status(self):
        """Observe the owned task, never infer liveness from startup metadata.

        No restart, model call, transport observation or exception text belongs
        in this read. A finished loop can still own unresolved native children.
        """
        self._require_home()
        status={'status':'not_configured','legacy_allowed':False,
                'external_delivery_proven':False,'runtime_active':False}
        if self.native is not None:
            status['mode']='execution' if self.native.host.execute else 'shadow'
            status['pending_work_count']=len(getattr(self.native,'pending',()))
            status['status']='ready'
        if self.task is not None:
            if not self.task.done():
                status.update(status='stopping' if self.closed else 'running',runtime_active=True)
            elif self.task.cancelled():
                status['status']='cancelled'
            else:
                error=self.task.exception()
                if error is not None:
                    status.update(status='failed',failure_class=type(error).__name__)
                else:
                    result=self.task.result()
                    reason=result.get('exit_reason') if isinstance(result,dict) else None
                    if reason in ('budget','stopped','cycle_failed'):
                        status.update(status='failed' if reason=='cycle_failed' else 'stopped',exit_reason=reason)
                    else:
                        status['status']='finished_unknown'
        if self.closed:
            status['binding_unloaded']=True
            if not status['runtime_active']:status['status']='unloaded'
        return status

    async def startup(self):
        self._require_home()
        if self.closed:return {'status':'unloaded','legacy_allowed':False}
        if self.native is None:return {'status':'not_configured','legacy_allowed':False}
        if self.started:
            observed=self.runtime_status()
            if observed['status']=='running':observed['status']='already_started'
            return observed
        legacy=self.home/'hooks/hermes-alive/handler.py'
        adapter=Path(__file__).resolve().parent/'skills/hermes-alive/hooks/kernel_gateway_handler.py'
        if legacy.exists() and legacy.read_text(encoding='utf-8-sig')!=adapter.read_text(encoding='utf-8-sig'):
            return {'status':'legacy_runtime_present','legacy_allowed':False}
        from hermes_constants import get_hermes_home
        for task in asyncio.all_tasks():
            if task.done() or task.get_name()!='hermes-alive-watcher':continue
            task_context=getattr(task,'get_context',None)
            # Without a public task context we cannot prove a named legacy
            # watcher is foreign; fail closed rather than guess its owner.
            if task_context is None or Path(task_context().run(get_hermes_home)).resolve()==self.home:
                return {'status':'legacy_runtime_active','legacy_allowed':False}
        self.task=self.native.start(self.context,**self.arguments)
        self.started=True
        return {'status':'started','legacy_allowed':False,'external_delivery_proven':False}

    def close(self):
        self.closed=True
        if self._continuity is not None:self._continuity.close()
        for router in self._session_routers.values():router.close()
        self._session_routers.clear()
        if self._unsubscribe_channels is not None:
            self._unsubscribe_channels()
            self._unsubscribe_channels=None
        for handle in self.channels.values():
            handle.close()
        self.channels.clear()
        if self.arguments is not None:
            stop=self.arguments['stop']
            if self.task is not None and not self.task.done():
                self.task.get_loop().call_soon_threadsafe(stop.set)
            else:stop.set()
        # Core owns the spawned-task cancellation registration. No default
        # manager lookup or process-wide profile/credential mutation belongs here.
