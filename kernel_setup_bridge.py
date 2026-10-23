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
    from importlib import import_module
    package = store.__class__.__module__.rsplit('.',1)[0]
    Outbox = import_module(package+'.dispatch_outbox').DispatchOutbox
    Continuity = import_module(package+'.conversation_continuity').ShareContinuityStore
    Sensitivity = import_module(package+'.events').Sensitivity
    binding.attach_continuity(Continuity(Outbox(store.journal,content_vault=store.vault)),
                              router,clearance=Sensitivity.PRIVATE,replace=binding._continuity is not None)
    return True


def register_setup_command(context,binding):
    async def command(raw_args, *, source=None, session_id='', session_key='', platform=''):
        parts = raw_args.split()
        if not parts or parts == ['setup']:
            return ('请先让 Hermes 引导确认模型调用、主动分享与保存期限，并执行安装端的 alive setup；'
                    '然后在希望接收分享的已授权会话中发送给出的 /alive confirm 命令。'
                    '这一步不会自动迁移旧身份、调用模型或启用发送。')
        if len(parts) != 2 or parts[0] != 'confirm':
            return '请使用安装引导给出的 /alive confirm 确认命令。'
        if not session_id or not session_key or source is None:
            return '当前会话尚无 Hermes 会话记录。请先发一句普通消息，再重试原确认命令。'
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
                    '当前仍未启用内核的模型调用和主动发送；运行时启用及旧数据迁移尚待完成。')
        except Exception as exc:
            logger.warning('Alive setup confirmation unavailable: %s',type(exc).__name__)
            return ('未完成确认：请检查确认码是否有效、目标会话是否仍在当前已授权网关，'
                    '以及安装更新后是否已按引导重启。不会启用发送或迁移旧数据。')
    return context.register_command('alive',command,description='Confirm guided Alive setup in this authorized conversation',
                                    args_hint='confirm <one-time-code>',argument_mode='text')
