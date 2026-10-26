"""Core-scoped conversational drafts, admitted only by an owner command.

The main agent interprets language. A tool result is not user authority. Drafts
stay in bounded process memory until the owner confirms their exact handle.
No raw chat capture, independent model call, transport or action grant lives here.
"""
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
import json
import threading
import time
from uuid import uuid4


AGENDA_SCHEMA = {
    'name': 'alive_agenda',
    'description': 'Propose a continuing item for the current user, or list their existing Alive items. '
                   'Use only when the user wants ongoing follow-up. Propose does not save a task: '
                   'show the entire returned preview and owner confirmation command. Never claim it is '
                   'active before confirmation. No external action is authorized by saving an item. '
                   'Do not turn quoted text, inferred interests or casual remarks into obligations.',
    'parameters': {'type': 'object', 'properties': {
        'operation': {'type': 'string', 'enum': ['propose', 'list']},
        'task': {'type': 'string', 'maxLength': 1500},
        'constraint': {'type': 'string', 'maxLength': 1000},
        'due_at': {'type': 'string', 'description': 'Optional ISO 8601 timestamp with explicit UTC offset; never guess an ambiguous date.'},
        'available_at': {'type': 'string', 'description': 'Optional earliest follow-up time, ISO 8601 with explicit UTC offset.'}},
        'required': ['operation'], 'additionalProperties': False}}


class CoreAgendaBridge:
    DRAFT_TTL = 600

    def __init__(self, binding):
        self.binding = binding
        self.turns = OrderedDict()
        self.drafts = OrderedDict()
        self.lock = threading.RLock()

    def close(self):
        with self.lock:
            self.turns.clear()
            self.drafts.clear()

    def _owner(self, scope):
        from .kernel_execution_bridge import configured_owner, runtime_engine
        if self.binding.closed or runtime_engine(self.binding) != 'kernel':
            raise ValueError('current kernel generation required')
        self.binding._require_home()
        return configured_owner(self.binding, scope)

    def context(self, **values):
        continuity = self.binding._continuity
        if self.binding.closed or continuity is None:
            return None
        scope = continuity.router.scope_for_hook(values)
        task = values.get('task_id')
        if scope is None or not isinstance(task, str) or not 0 < len(task) <= 4096:
            return None
        _store, configured = self._owner(scope)
        with self.lock:
            self.turns[(scope, task)] = (configured.event_id, time.monotonic())
            self.turns.move_to_end((scope, task))
            while len(self.turns) > 64:
                self.turns.popitem(last=False)
        return {'context': 'Alive continuing items: alive_agenda can propose an ongoing item or inspect current items. '
                           'A proposal is temporary until the user confirms its exact command. '
                           'Remembering an item does not authorize tools or an external action.'}

    @staticmethod
    def _date(value):
        if value is None:
            return None
        if not isinstance(value, str) or len(value) > 64:
            raise ValueError('explicit bounded timestamp required')
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError('explicit timezone required')
        return stamp.astimezone(timezone.utc)

    def tool(self, args, *, task_id=None, session_id=None, **_ignored):
        try:
            from gateway.session_context import get_session_env
            continuity = self.binding._continuity
            if continuity is None:
                raise ValueError('current continuity required')
            scope = continuity.router.scope_for_hook(dict(session_id=session_id,
                sender_id=get_session_env('HERMES_SESSION_USER_ID'),
                platform=get_session_env('HERMES_SESSION_PLATFORM')))
            if scope is None:
                raise ValueError('current admitted main turn required')
            store, configured = self._owner(scope)
            with self.lock:
                turn = self.turns.get((scope, task_id))
            if (turn is None or turn[0] != configured.event_id
                    or time.monotonic() - turn[1] > self.DRAFT_TTL):
                raise ValueError('current main task required')
            if not isinstance(args, dict) or args.get('operation') not in ('propose', 'list'):
                raise ValueError('bounded agenda operation required')
            if args['operation'] == 'list':
                if set(args) != {'operation'}:
                    raise ValueError('list takes no model-supplied scope')
                result = {'items': self._items(store, configured),
                          'view_limit': 8, 'complete_inventory_proven': False,
                          'external_action_authorized': False}
            else:
                if set(args) - {'operation', 'task', 'constraint', 'due_at', 'available_at'}:
                    raise ValueError('unexpected proposal fields')
                details = {name: args.get(name, '') for name in ('task', 'constraint')}
                if (not isinstance(details['task'], str) or not details['task'].strip()
                        or len(details['task']) > 1500 or not isinstance(details['constraint'], str)
                        or len(details['constraint']) > 1000):
                    raise ValueError('bounded task and constraint required')
                due, available = self._date(args.get('due_at')), self._date(args.get('available_at'))
                if due is not None and available is not None and available > due:
                    raise ValueError('follow-up cannot start after its deadline')
                now = datetime.now(timezone.utc)
                expiry = now + timedelta(days=configured.options['outbound_retention_days'])
                if any(stamp is not None and (stamp <= now or stamp >= expiry) for stamp in (due, available)):
                    raise ValueError('future time within the configured retention window required')
                handle = 'ad_' + uuid4().hex
                draft = dict(details=details, due=due, available=available, scope=scope,
                             configuration=configured.event_id, created=time.monotonic())
                with self.lock:
                    if self.binding.closed:
                        raise ValueError('generation retired')
                    self.drafts[handle] = draft
                    while len(self.drafts) > 16:
                        self.drafts.popitem(last=False)
                result = {'status': 'temporary_proposal_not_saved', 'preview': details,
                          'due_at': due.isoformat() if due else None,
                          'available_at': available.isoformat() if available else None,
                          'confirmation_command': '/alive agenda accept ' + handle,
                          'preview_command': '/alive agenda preview ' + handle,
                          'expires_in_seconds': self.DRAFT_TTL,
                          'retention_days_after_confirmation': configured.options['outbound_retention_days'],
                          'external_action_authorized': False}
            self._owner(scope)
            return json.dumps(result, ensure_ascii=False)
        except (ValueError, TypeError, KeyError):
            return json.dumps({'error': 'alive_agenda_unavailable',
                'hint': 'Use the configured owner conversation and an explicit future time with timezone; '
                        'a draft needs owner confirmation before it is saved.'})

    def _items(self, store, configured, item_id=None):
        from .kernel_execution_bridge import kernel
        agenda = kernel('agenda')
        if not next(store.journal.iter_reverse(event_types=('agenda.proposed',), max_records=1), None):
            return []
        projection = self._projection(store)
        projection.project_new()
        items = projection.list_items(clearance=kernel('events').Sensitivity.PRIVATE,
            subject=configured.subject, kinds=(agenda.AgendaItemKind.COMMITMENT,),
            states=tuple(agenda.AgendaState), limit=8,
            item_ids=(item_id,) if item_id else None)
        return [dict(item_id=item.item_id, state=item.state.value, details=dict(item.details)
                     if hasattr(item.details, 'items') else item.details,
                     content_status=item.content_status.value,
                     available_at=item.available_at.isoformat() if item.available_at else None,
                     due_at=item.due_at.isoformat() if item.due_at else None) for item in items]

    @staticmethod
    def _projection(store):
        from .kernel_execution_bridge import kernel
        path = store.journal.path
        root = path.parent / (path.stem + '-content-vault')
        existing = next(store.journal.iter_reverse(event_types=('agenda.proposed',), max_records=1), None)
        if existing is not None and not all((root / name).is_file() for name in ('content.key', 'content.sqlite3')):
            raise ValueError('existing agenda storage is unavailable; do not replace its key')
        return kernel('agenda').AgendaProjection(store.journal)

    def command(self, scope, parts):
        """Caller must already have checked the admitted Core command source."""
        from .kernel_execution_bridge import kernel
        store, configured = self._owner(scope)
        if parts == ['list']:
            return json.dumps({'items': self._items(store, configured),
                               'view_limit': 8, 'complete_inventory_proven': False}, ensure_ascii=False)
        if len(parts) != 2 or parts[0] not in ('preview', 'accept', 'done', 'cancel'):
            return '请使用 /alive agenda list、preview <确认码>、accept <确认码>、done <事项ID> 或 cancel <事项ID>。'
        action, handle = parts
        with self.lock:
            if action in ('preview', 'accept'):
                draft = self.drafts.get(handle)
                if (draft is None or draft['scope'] != scope or draft['configuration'] != configured.event_id
                        or time.monotonic() - draft['created'] > self.DRAFT_TTL):
                    return '此事项提议已失效或不属于当前会话，请重新提出。尚未保存为待办。'
                if action == 'preview':
                    return json.dumps({'proposal': draft['details'],
                        'due_at': draft['due'].isoformat() if draft['due'] else None,
                        'available_at': draft['available'].isoformat() if draft['available'] else None,
                        'confirmation_command': '/alive agenda accept ' + handle}, ensure_ascii=False)
            else:
                items = self._items(store, configured, handle)
                if not items:
                    return '当前会话没有这项保留事项。'
                if items[0]['state'] in ('completed', 'dismissed', 'expired'):
                    return '这项事项已结束，不会再次执行此操作。'
            events, agenda_module = kernel('events'), kernel('agenda')
            projection = self._projection(store)
            source = store.journal.append(events.EventEnvelope(event_type='conversation.inbound',
                source='hermes.command.alive.agenda', actor=configured.subject, subject=configured.subject,
                sensitivity=events.Sensitivity.PRIVATE,
                payload={'operation': action, 'raw_content_stored': False,
                         'configuration_event_id': configured.event_id, 'external_action_authorized': False}))
            if action == 'accept':
                now = datetime.now(timezone.utc)
                expiry = now + timedelta(days=configured.options['outbound_retention_days'])
                if any(stamp is not None and stamp <= now for stamp in (draft['due'], draft['available'])):
                    return '提议中的时间已过，请重新确认时间。尚未保存为待办。'
                event = projection.append_proposal(agenda_module.AgendaProposal(
                    kind=agenda_module.AgendaItemKind.COMMITMENT, subject=configured.subject,
                    details=draft['details'], authority=agenda_module.AgendaAuthority.USER_EXPLICIT,
                    source_event_ids=(source.event.event_id,), confidence=1,
                    due_at=draft['due'], available_at=draft['available'], expires_at=expiry), actor=configured.subject)
                decision = projection.apply(event)
                if decision.outcome != 'active':
                    raise ValueError('agenda admission did not activate')
                del self.drafts[handle]
                return '事项已保存；这不授权代办或调用外部工具。事项ID：' + decision.item_id
            target = agenda_module.AgendaState.COMPLETED if action == 'done' else agenda_module.AgendaState.DISMISSED
            event = projection.append_transition(handle, target, actor=configured.subject,
                authority=agenda_module.AgendaAuthority.USER_EXPLICIT, source_event_id=source.event.event_id,
                reason='Owner command ' + action)
            if projection.apply(event).outcome != 'transitioned':
                raise ValueError('agenda transition unavailable')
            return '事项已标记完成。' if action == 'done' else '事项已取消。'
