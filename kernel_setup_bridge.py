"""Core-registered conversation confirmation of operator-initiated choices."""
import logging

from .tool_receipt_bridge import _kernel_module

logger = logging.getLogger(__name__)


def setup_store(binding):
    binding._require_home()
    return _kernel_module('kernel_setup').KernelSetupStore(
        binding.home/'plugin-data/hermes-alive/runtime/kernel')


def attach_configured_continuity(binding, configured=None):
    if binding.closed:
        return False
    store = setup_store(binding)
    configured = configured or store.configuration()
    if configured is None:
        return False
    document = configured.scope
    router = binding.session_router(document['platform'])
    current = router.capture_target(session_key=document['session_key'],
        user_id=document['user_id'],platform=document['platform'])
    saved = dict(document)
    actual = current.binding_document()
    # A reset starts a new discussion history, not a new person or recipient.
    # Current turn retrieval still uses the NEW exact session ID and cannot
    # restore old-session history. Other realm/receiver/thread changes refuse.
    saved.pop('session_id');actual.pop('session_id')
    if saved != actual:
        raise ValueError('configured Core conversation realm changed')
    if (getattr(binding,'_continuity_configuration_id',None)==configured.event_id
            and binding._continuity is not None and not binding._continuity._closed
            and binding._continuity.router is router):return True
    from importlib import import_module
    package = store.__class__.__module__.rsplit('.',1)[0]
    Outbox = import_module(package+'.dispatch_outbox').DispatchOutbox
    Continuity = import_module(package+'.conversation_continuity').ShareContinuityStore
    Sensitivity = import_module(package+'.events').Sensitivity
    binding.attach_continuity(Continuity(Outbox(store.journal,content_vault=store.vault)),
                              router,clearance=Sensitivity.PRIVATE,replace=binding._continuity is not None)
    binding._continuity_configuration_id=configured.event_id
    return True


def register_setup_command(context,binding):
    async def command(raw_args, *, source=None, session_id='', session_key='', platform=''):
        parts = raw_args.split()
        if not parts or parts == ['setup']:
            return ('请先让 Hermes 引导确认模型调用、主动分享与保存期限，并执行安装端的 alive setup；'
                    '然后在希望接收分享的已授权会话中发送给出的 /alive confirm 命令。'
                    '这一步不会自动迁移旧身份、调用模型或启用发送。')
        control=len(parts)==1 and parts[0] in ('enable','pause','status')
        if not control and (len(parts) != 2 or parts[0] != 'confirm'):
            return '请使用 /alive confirm 确认配置，或 /alive enable、/alive pause、/alive status。'
        if not session_id or not session_key or source is None:
            return '当前会话尚无 Hermes 会话记录。请先发一句普通消息，再重试原确认命令。'
        scope=None
        enable_attempted=False
        try:
            binding._require_home()
            if (not platform or getattr(getattr(source,'platform',None),'value',None) != platform
                    or not getattr(source,'user_id',None)):
                raise ValueError('current admitted Core command source required')
            router = binding.session_router(platform)
            scope = router.capture_target(session_key=session_key,user_id=source.user_id,platform=platform)
            if scope.session_id != session_id:
                raise ValueError('Core command session changed')
            for name in ('chat_id','user_id','thread_id','scope_id','guild_id','parent_chat_id'):
                if (getattr(source,name,None) or '') != getattr(scope,name):
                    raise ValueError('Core command source differs from its persisted conversation')
            if control:
                from . import kernel_execution_bridge as execution
                async with binding.control_lock:
                    store,configured=execution.configured_owner(binding,scope)
                    if parts[0]=='status':
                        active=store.activation()
                        observed=binding.runtime_status()
                        return ('Alive 状态：'+observed['status']+'；当前发送授权：'
                            +('有效' if active else '未启用、已暂停或已到期')+'。'
                            +'待收拢工作：'+str(observed.get('pending_work_count',0))+' 项。'
                            '运行状态不代表消息已送达。')
                    if parts[0]=='pause':
                        execution.pause(binding,scope)
                        return 'Alive 已暂停。不会发起新的分享；已提交给消息渠道的内容由该渠道继续处理。'
                    if binding.task is not None and not binding.task.done():
                        return 'Alive 后台任务仍在运行或停止中，请先查看 /alive status。'
                    if execution.runtime_engine(binding)!='kernel':
                        return ('请先让 Hermes 执行 alive install-runtime --engine kernel 并按引导重启网关。'
                                '影子模式保持不发送，不会自动切换为正式执行。')
                    enable_attempted=True
                    execution.attach(binding,execution.enable(binding,scope))
                    result=await binding.startup()
                    if result['status']!='started':
                        execution.pause(binding,scope)
                        raise ValueError('Gateway did not start the authorized host')
                    return ('Alive 已启用：授权持续有效，直到你暂停或撤销；最多每日3次、间隔至少1小时。'
                            '模型及备用模型由 Hermes 管理；可用 /alive pause 暂停，/alive status 查询。'
                            '消息提交不代表对方已收到。')
            settings = context.get_config('kernel_setup',{})
            intent_id = settings.get('pending_intent_id')
            if not intent_id and settings.get('activation_event_id'):
                intent_id = settings['activation_event_id'].removesuffix(':confirmed')
            configured = setup_store(binding).confirm(intent_id,parts[1],scope=scope.binding_document())
            # Config is an inventory/startup hint; the signed journal remains
            # authoritative if another operator stages a replacement concurrently.
            if setup_store(binding).configuration().event_id != configured.event_id:
                raise ValueError('a newer setup superseded this confirmation')
            from hermes_cli.plugins_state import save_plugin_setting
            save_plugin_setting('hermes-alive',('kernel_setup',),
                {'activation_event_id':configured.event_id,'status':'configured','enabled':False})
            attach_configured_continuity(binding,configured)
            return ('目标会话和所选权限已确认，分享接续读取已接入。'
                    '当前仍未启用模型调用和主动发送。可发送 /alive enable 启用；公开检索是可选能力，'
                    '授权持续有效直到暂停或撤销，最多每日3次且间隔至少1小时；'
                    '/alive pause 可暂停。资料保留期限单独管理。旧身份不会自动迁移。')
        except Exception as exc:
            if enable_attempted and scope is not None:
                try:
                    from . import kernel_execution_bridge as execution
                    execution.pause(binding,scope)
                except Exception as rollback_error:
                    logger.warning('Alive enable rollback requires attention: %s',type(rollback_error).__name__)
            logger.warning('Alive setup confirmation unavailable: %s',type(exc).__name__)
            return ('未完成操作：请检查确认码或配置是否有效、公开检索主题是否已配置、目标会话是否仍在当前已授权网关，'
                    '以及安装更新后是否已按引导重启。不会自动补发历史消息。')
    return context.register_command('alive',command,description='Configure and control Alive in this authorized conversation',
                                    args_hint='confirm <one-time-code> | enable | pause | status',argument_mode='text')
