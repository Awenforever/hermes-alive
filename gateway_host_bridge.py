"""Per-plugin-generation Gateway startup handoff; experimental shadow only."""
import asyncio
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
        context.on_unload(self.close)

    def _require_home(self):
        from hermes_constants import get_hermes_home
        if Path(get_hermes_home()).resolve()!=self.home:
            raise ValueError('Gateway binding belongs to another Core profile')

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

    async def startup(self):
        self._require_home()
        if self.closed:return {'status':'unloaded','legacy_allowed':False}
        if self.native is None:return {'status':'not_configured','legacy_allowed':False}
        if self.started:return {'status':'already_started','legacy_allowed':False}
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
        if self.arguments is not None:
            stop=self.arguments['stop']
            if self.task is not None and not self.task.done():
                self.task.get_loop().call_soon_threadsafe(stop.set)
            else:stop.set()
        # Core owns the spawned-task cancellation registration. No default
        # manager lookup or process-wide profile/credential mutation belongs here.
