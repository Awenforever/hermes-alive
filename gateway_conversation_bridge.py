"""Explicit Core-scoped continuity attachment; no sending or model invocation.

The trusted live assembly supplies a store and the actual Core session router.
Merely installing this module does not enable retention or activate the kernel.
"""
from pathlib import Path
from collections import OrderedDict
import json
import threading
from uuid import uuid4


READ_REFERENCE_SCHEMA = {
    'name': 'alive_read_reference',
    'description': 'Read exact retained Alive text or one retained source excerpt in your current conversation. '
                   'Use a reference handle from Alive context. Paged fragments must be read in order; '
                   'text recovers what Alive prepared, not independent verification. Use source pages to inspect '
                   'the collected evidence. The catalog separates sources_linked_in_share from '
                   'background_sources; use their source_index values. A null next_offset ends '
                   'the retained text, not the original source. If material is missing, a permitted Core '
                   'web read of the exact public source can add evidence independently. Image links and '
                   'alt text require separate image inspection to say what an image shows. Cite the source name. '
                   'These handles belong to prepared proactive shares, not agenda request events or Core jobs. '
                   'For a retained task original, use the original_request_lookup returned by alive_agenda. '
                   'A provenance source_event_id is not a read_reference handle. '
                   'This cannot send, search files or access other sessions.',
    'parameters': {'type': 'object', 'properties': {
        'reference': {'type': 'string'},
        'part': {'type': 'string', 'enum': ['text', 'source'], 'default': 'text'},
        'source_index': {'type': 'integer', 'minimum': 0, 'maximum': 7},
        'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
        'max_chars': {'type': 'integer', 'minimum': 256, 'maximum': 4096, 'default': 4096,
                      'description': 'Maximum text characters in this page; bounded metadata is separate.'}},
        'required': ['reference'], 'additionalProperties': False}}

_WIRE_CONTEXT_PREFIX = '[[hermes-alive-context:'
_WIRE_CONTEXT_MARKER_LENGTH = len(_WIRE_CONTEXT_PREFIX) + 34
_WIRE_PAGE_KEY = 'alive_retained_page'
_REFERENCE_ERROR = {'error': 'alive_reference_unavailable'}
_WIRE_MESSAGE_KEYS = {
    'chat_completions': ('messages', 'text'),
    'anthropic_messages': ('messages', 'text'),
    'bedrock_converse': ('messages', None),
    'codex_responses': ('input', 'input_text'),
}


def _wire_user_text(request, api_mode):
    """Yield user text slots from a known provider request, never tool output."""
    if api_mode not in _WIRE_MESSAGE_KEYS or not isinstance(request, dict):
        return
    key, part_type = _WIRE_MESSAGE_KEYS[api_mode]
    messages = request.get(key)
    if not isinstance(messages, list):
        return
    for message in messages:
        if not isinstance(message, dict) or message.get('role') != 'user':
            continue
        content = message.get('content')
        if isinstance(content, str) and api_mode != 'bedrock_converse':
            yield message, 'content'
        elif isinstance(content, list):
            for part in content:
                if (isinstance(part, dict) and part.get('type') == part_type
                        and isinstance(part.get('text'), str)):
                    yield part, 'text'


def _wire_tool_text(request, api_mode):
    """Yield only the result carriers established by Core's converters."""
    key, _ = _WIRE_MESSAGE_KEYS[api_mode]
    rows = request.get(key)
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        if api_mode == 'chat_completions' and row.get('role') == 'tool':
            yield row, 'content', row.get('tool_call_id')
        elif api_mode == 'codex_responses' and row.get('type') == 'function_call_output':
            yield row, 'output', row.get('call_id')
        elif api_mode in ('anthropic_messages', 'bedrock_converse') and row.get('role') == 'user':
            parts = row.get('content')
            for part in parts if isinstance(parts, list) else ():
                if not isinstance(part, dict):
                    continue
                if api_mode == 'anthropic_messages' and part.get('type') == 'tool_result':
                    if isinstance(part.get('content'), str):
                        yield part, 'content', part.get('tool_use_id')
                    elif isinstance(part.get('content'), list):
                        for block in part['content']:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                yield block, 'text', part.get('tool_use_id')
                if api_mode == 'bedrock_converse' and isinstance(part.get('toolResult'), dict):
                    blocks = part['toolResult'].get('content')
                    for block in blocks if isinstance(blocks, list) else ():
                        if isinstance(block, dict):
                            yield block, 'text', part['toolResult'].get('toolUseId')


def _wire_safe_text(text, api_mode):
    # This middleware runs after Core's outgoing text sanitation.
    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        return None
    if any(ord(c) < 32 and c not in '\t\r\n' for c in text):
        return None
    if api_mode == 'codex_responses':
        from agent.codex_responses_adapter import _neutralize_harmony_tokens
        return _neutralize_harmony_tokens(text)
    return text


def _context_budget(store, config=None):
    """Respect Core's resolved per-hook cap without writing its configuration."""
    from hermes_cli.config import load_config_readonly
    from tools.hook_output_spill import DEFAULT_ENABLED, DEFAULT_MAX_CHARS
    from tools.tool_output_limits import _coerce_positive_int
    config = (load_config_readonly() or {}) if config is None else config
    hooks = config.get('hooks') if isinstance(config, dict) else None
    section = hooks.get('output_spill') if isinstance(hooks, dict) else None
    section = section if isinstance(section, dict) else {}
    enabled = section.get('enabled', DEFAULT_ENABLED)
    enabled = bool(enabled) if enabled is not None else DEFAULT_ENABLED
    return min(store.MAX_CONTEXT, _coerce_positive_int(section.get('max_chars'), DEFAULT_MAX_CHARS)) if enabled else store.MAX_CONTEXT


class CoreShareContinuity:
    def __init__(self, store, router, *, clearance):
        self.store, self.router, self.clearance = store, router, clearance
        self._closed = False
        self._references = OrderedDict()
        self._wire_turns = OrderedDict()
        self._wire_pages = OrderedDict()
        self._reference_lock = threading.RLock()
        expected = Path(router.home) / 'plugin-data/hermes-alive/runtime/kernel'
        if Path(store.journal.path).resolve().parent != expected.resolve():
            raise ValueError('continuity store belongs to another Core profile')

    def close(self):
        with self._reference_lock:
            self._closed = True
            self._references.clear()
            self._wire_turns.clear()
            self._wire_pages.clear()

    def for_target(self, scope):
        """Bind a trusted target, not a user/model-selected scope document."""
        if self._closed:
            raise ValueError('conversation continuity retired')
        current = self.router.for_turn(session_key=scope.session_key,
            session_id=scope.session_id, user_id=scope.user_id, platform=scope.platform)
        if current != scope:
            raise ValueError('conversation target changed')
        def resolve_scope(execution, clearance):
            if self._closed or clearance != self.clearance:
                raise ValueError('current conversation continuity clearance required')
            self.router.resolve_channel(scope, execution.route)
            return scope.binding_document()

        return self.store.bind_target(resolve_scope)

    def context(self, **values):
        if self._closed:
            return None
        scope = self.router.scope_for_hook(values)
        if scope is None:
            return None
        # Select complete outward text before optional original source excerpts.
        # Otherwise a large source bundle can hide the newest share even before
        # the final hook-budget projection sees it.
        shares = self.store.read(scope=scope.binding_document(), clearance=self.clearance, include_sources=False)
        if not shares:
            return None
        from hermes_cli.config import load_config_readonly
        from hermes_cli.tools_config import _get_platform_tools

        config = load_config_readonly() or {}
        task = values.get('task_id')
        can_page = (isinstance(task, str) and 0 < len(task) <= 4096
                    and 'hermes_alive' in _get_platform_tools(config, scope.platform))
        expanded = []
        for share in shares:
            item = self.store.read_reference(scope=scope.binding_document(), clearance=self.clearance,
                                             share_id=share['share_id'])
            if item is None:
                continue
            if can_page:
                item['reference'] = self._reference(scope, task, share['share_id'])
            expanded.append(item)
        shares = expanded
        # Use this exact embedded build, never import an unrelated installed one.
        from importlib import import_module
        module = import_module(self.store.__class__.__module__)
        text = module.continuation_context(
            shares, max_chars=_context_budget(self.store, config), inline_source_excerpts=not can_page)
        if shares and not text:
            import logging
            logging.getLogger(__name__).warning('Alive conversation reference cannot fit the active Core hook budget')
        return {'context': text} if text else None

    def capture_wire_context(self, **values):
        """Store a turn binding and return only a marker for Core's history."""
        identity = tuple(values.get(k) for k in ('session_id', 'task_id', 'turn_id'))
        if any(not isinstance(k, str) or not 0 < len(k) <= 4096 for k in identity):
            return None
        scope = self.router.scope_for_hook(values)
        if scope is None or _context_budget(self.store) < _WIRE_CONTEXT_MARKER_LENGTH:
            return None
        envelope = {k: values.get(k) for k in ('session_id', 'task_id', 'turn_id',
                    'sender_id', 'platform', 'parent_session_id')}
        with self._reference_lock:
            if self._closed:
                return None
            binding = self._wire_turns.get(identity)
            if binding is None:
                marker = _WIRE_CONTEXT_PREFIX + uuid4().hex + ']]'
                binding = (marker, scope, envelope)
                self._wire_turns[identity] = binding
                while len(self._wire_turns) > 64:
                    self._wire_turns.popitem(last=False)
            elif binding[1:] != (scope, envelope):
                return None
            return {'context': binding[0]}

    def expand_wire_context(self, *, request, session_id, task_id, turn_id, api_mode):
        """Resolve current-turn supplements in the copied provider payload."""
        if api_mode not in _WIRE_MESSAGE_KEYS or not isinstance(request, dict):
            return None
        identity = (session_id, task_id, turn_id)
        with self._reference_lock:
            binding = self._wire_turns.get(identity)
        if binding is None:
            return None
        marker, scope, envelope = binding
        if self.router.scope_for_hook(envelope) != scope:
            return None
        replacements = []
        matches = [(slot, key) for slot, key in _wire_user_text(request, api_mode)
                   if marker in slot[key]]
        if len(matches) == 1:
            slot, key = matches[0]
            pieces = slot[key].split('\n\n')
            if marker in pieces and slot[key].count(marker) == 1:
                result = self.context(**envelope)
                text = _wire_safe_text(result['context'], api_mode) if result else None
                if text is not None:
                    pieces[pieces.index(marker)] = text
                    replacements.append((slot, key, '\n\n'.join(pieces)))
        pages = {}
        for slot, key, call_id in _wire_tool_text(request, api_mode):
            content = slot.get(key)
            if not isinstance(content, str) or not 0 < len(content) <= 128:
                continue
            try:
                document = json.loads(content)
            except ValueError:
                continue
            if isinstance(document, dict) and set(document) == {_WIRE_PAGE_KEY}:
                handle = document[_WIRE_PAGE_KEY]
                if isinstance(handle, str):
                    pages.setdefault(handle, []).append((slot, key, call_id))
        for handle, slots in pages.items():
            with self._reference_lock:
                entry = self._wire_pages.get(handle)
            if len(slots) != 1 or entry is None or entry[:2] != (identity, slots[0][2]):
                continue
            result = self.read_reference(entry[2], task_id=task_id, session_id=session_id)
            text = _wire_safe_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), api_mode)
            if text is not None:
                replacements.append((*slots[0][:2], text))
        if not replacements or self.router.scope_for_hook(envelope) != scope:
            return None
        with self._reference_lock:
            if self._closed or self._wire_turns.get(identity) is not binding:
                return None
            for slot, key, text in replacements:
                slot[key] = text
        return {'request': request, 'source': 'hermes-alive'}

    def queue_reference(self, args, *, task_id=None, session_id=None, **_ignored):
        """Core may retain the marker. The actual page is read on each attempt."""
        from tools import approval_context
        turn_id = approval_context._approval_turn_id.get()
        tool_call_id = approval_context._approval_tool_call_id.get()
        identity = (session_id, task_id, turn_id)
        if (approval_context._approval_session_id.get() != session_id
                or not all(isinstance(k, str) and 0 < len(k) <= 4096 for k in identity)
                or not isinstance(tool_call_id, str) or not 0 < len(tool_call_id) <= 4096
                or not isinstance(args, dict) or set(args) - {'reference', 'part', 'source_index', 'offset', 'max_chars'}
                or not isinstance(args.get('reference'), str) or len(args['reference']) > 64):
            return _REFERENCE_ERROR
        if any(type(value) not in (str, int) or isinstance(value, str) and len(value) > 64
               for value in args.values()):
            return _REFERENCE_ERROR
        with self._reference_lock:
            binding = self._wire_turns.get(identity)
            entry = self._references.get(args['reference'])
            if self._closed or binding is None or entry is None or entry[:2] != (binding[1], task_id):
                return _REFERENCE_ERROR
            marker = uuid4().hex
            self._wire_pages[marker] = (identity, tool_call_id, dict(args))
            while len(self._wire_pages) > 64:
                self._wire_pages.popitem(last=False)
        return {_WIRE_PAGE_KEY: marker}

    def _reference(self, scope, task, share_id):
        with self._reference_lock:
            if self._closed:
                raise ValueError('conversation continuity retired')
            for handle, entry in self._references.items():
                if entry[:3] == (scope, task, share_id):
                    return handle
            handle = 'ar_' + uuid4().hex
            self._references[handle] = (scope, task, share_id)
            while len(self._references) > 64:
                self._references.popitem(last=False)
            return handle

    def read_reference(self, args, *, task_id=None, session_id=None, **_ignored):
        """Core-dispatched scoped read, never a model-supplied identity."""
        try:
            if (self._closed or not isinstance(args, dict)
                    or set(args) - {'reference', 'part', 'source_index', 'offset', 'max_chars'}
                    or not isinstance(args.get('reference'), str) or len(args['reference']) > 64):
                raise ValueError('invalid reference request')
            part, index = args.get('part', 'text'), args.get('source_index')
            offset, count = args.get('offset', 0), args.get('max_chars', 4096)
            if (part not in ('text', 'source') or type(offset) is not int or not 0 <= offset <= self.store.MAX_CONTEXT
                    or type(count) is not int or not 256 <= count <= 4096
                    or part == 'text' and index is not None
                    or part == 'source' and (type(index) is not int or not 0 <= index < self.store.MAX_SOURCES)):
                raise ValueError('invalid reference page')
            from gateway.session_context import get_session_env
            values = dict(session_id=session_id, sender_id=get_session_env('HERMES_SESSION_USER_ID'),
                          platform=get_session_env('HERMES_SESSION_PLATFORM'))
            scope = self.router.scope_for_hook(values)
            with self._reference_lock:
                entry = self._references.get(args['reference'])
            if scope is None or entry is None or entry[:2] != (scope, task_id):
                raise ValueError('reference not available in this Core task')
            item = self.store.read_reference(scope=scope.binding_document(), clearance=self.clearance,
                share_id=entry[2])
            if item is None:
                raise ValueError('retained reference unavailable')
            metadata = {}
            from importlib import import_module
            module = import_module(self.store.__class__.__module__)
            if part == 'text':
                text = item['text']
                catalog = []
                indexed = sorted(enumerate(item['sources']),
                                 key=lambda entry: entry[1].get('linked_in_share') is not True)
                for position, original in indexed:
                    source = module._conversation_source(original)
                    if 'excerpt' in source:
                        source.pop('excerpt')
                        source['excerpt_in_context'] = False
                    candidate = {'source_index': position, **source}
                    if len(json.dumps(module._source_groups(catalog + [candidate]),
                                      ensure_ascii=False)) <= 4096:
                        catalog.append(candidate)
                metadata = {'content_kind': 'exact_prepared_share_not_source_verification',
                            'source_catalog': module._source_groups(catalog),
                            'source_catalog_complete': len(catalog) == item['source_count']}
            else:
                if index >= item['source_count']:
                    raise ValueError('source index unavailable')
                source = module._conversation_source(item['sources'][index])
                text = source.pop('excerpt', None)
                if not isinstance(text, str) or not text.strip():
                    raise ValueError('retained source excerpt unavailable')
                basis = source.get('reading_scope', {}).get('evidence_basis')
                kind = 'retained_search_result_excerpt' if basis == 'search_result_excerpt' else 'retained_source_excerpt'
                metadata = {'content_kind': kind, 'source_index': index, 'source': source}
            if offset > len(text):
                raise ValueError('page offset beyond the retained text')
            end = min(len(text), offset + count)
            # Recheck live profile/route/generation after the private read.
            if self._closed or self.router.scope_for_hook(values) != scope:
                raise ValueError('conversation scope changed during read')
            return {'reference': args['reference'], 'part': part, 'prepared_at': item['prepared_at'],
                    'offset': offset, 'text': text[offset:end], 'next_offset': end if end < len(text) else None,
                    'source_count': item['source_count'], **metadata}
        except (ValueError, KeyError, TypeError):
            # No caller IDs, body, exception text or existence oracle crosses a
            # failed owner/profile/retention boundary.
            return {'error': 'alive_reference_unavailable'}
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('Alive reference read failed: %s', type(exc).__name__)
            return {'error': 'alive_reference_unavailable'}
