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
                   'the collected evidence; its catalog identifies source indices. An excerpt is not a full source. '
                   'This cannot send, search files or access other sessions.',
    'parameters': {'type': 'object', 'properties': {
        'reference': {'type': 'string'},
        'part': {'type': 'string', 'enum': ['text', 'source'], 'default': 'text'},
        'source_index': {'type': 'integer', 'minimum': 0, 'maximum': 7},
        'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
        'max_chars': {'type': 'integer', 'minimum': 256, 'maximum': 4096, 'default': 4096,
                      'description': 'Maximum text characters in this page; bounded metadata is separate.'}},
        'required': ['reference'], 'additionalProperties': False}}


def _context_budget(store):
    """Respect Core's resolved per-hook cap without writing its configuration."""
    from hermes_cli.config import load_config_readonly
    from tools.hook_output_spill import DEFAULT_ENABLED, DEFAULT_MAX_CHARS
    from tools.tool_output_limits import _coerce_positive_int
    config = load_config_readonly() or {}
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
        self._reference_lock = threading.RLock()
        expected = Path(router.home) / 'plugin-data/hermes-alive/runtime/kernel'
        if Path(store.journal.path).resolve().parent != expected.resolve():
            raise ValueError('continuity store belongs to another Core profile')

    def close(self):
        with self._reference_lock:
            self._closed = True
            self._references.clear()

    def for_target(self, scope):
        """Bind a trusted target, not a user/model-selected scope document."""
        if self._closed:
            raise ValueError('conversation continuity retired')
        current = self.router.for_turn(session_key=scope.session_key,
            session_id=scope.session_id, user_id=scope.user_id, platform=scope.platform)
        if current != scope:
            raise ValueError('conversation target changed')
        return _TargetContinuity(self, scope)

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
        expanded = []
        for share in shares:
            item = self.store.read_reference(scope=scope.binding_document(), clearance=self.clearance,
                                             share_id=share['share_id'])
            if item is None:
                continue
            task = values.get('task_id')
            if isinstance(task, str) and 0 < len(task) <= 4096:
                item['reference'] = self._reference(scope, task, share['share_id'])
            expanded.append(item)
        shares = expanded
        # Use this exact embedded build, never import an unrelated installed one.
        from importlib import import_module
        module = import_module(self.store.__class__.__module__)
        text = module.continuation_context(shares, max_chars=_context_budget(self.store))
        if shares and not text:
            import logging
            logging.getLogger(__name__).warning('Alive conversation reference cannot fit the active Core hook budget')
        return {'context': text} if text else None

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
                for position, original in enumerate(item['sources']):
                    source = module._conversation_source(original)
                    if 'excerpt' in source:
                        source.pop('excerpt')
                        source['excerpt_in_context'] = False
                    candidate = {'source_index': position, **source}
                    if len(json.dumps(catalog + [candidate], ensure_ascii=False)) <= 4096:
                        catalog.append(candidate)
                metadata = {'content_kind': 'exact_prepared_share_not_source_verification',
                            'source_catalog': catalog, 'source_catalog_complete': len(catalog) == item['source_count']}
            else:
                if index >= item['source_count']:
                    raise ValueError('source index unavailable')
                source = module._conversation_source(item['sources'][index])
                text = source.pop('excerpt', None)
                if not isinstance(text, str) or not text.strip():
                    raise ValueError('retained source excerpt unavailable')
                metadata = {'content_kind': 'retained_source_excerpt', 'source_index': index, 'source': source}
            if offset > len(text):
                raise ValueError('page offset beyond the retained text')
            end = min(len(text), offset + count)
            # Recheck live profile/route/generation after the private read.
            if self._closed or self.router.scope_for_hook(values) != scope:
                raise ValueError('conversation scope changed during read')
            return {'reference': args['reference'], 'part': part, 'prepared_at': item['prepared_at'],
                    'offset': offset, 'text': text[offset:end], 'next_offset': end if end < len(text) else None,
                    'total_characters': len(text), 'complete': offset == 0 and end == len(text),
                    'source_count': item['source_count'], **metadata}
        except (ValueError, KeyError, TypeError):
            # No caller IDs, body, exception text or existence oracle crosses a
            # failed owner/profile/retention boundary.
            return {'error': 'alive_reference_unavailable'}
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('Alive reference read failed: %s', type(exc).__name__)
            return {'error': 'alive_reference_unavailable'}


class _TargetContinuity:
    def __init__(self, bridge, scope):
        self.bridge, self.scope = bridge, scope

    def prepare(self, execution, *, clearance, now):
        if self.bridge._closed or clearance != self.bridge.clearance:
            raise ValueError('current conversation continuity clearance required')
        # Recheck the canonical receiving adapter, scope and Gateway loop now.
        self.bridge.router.resolve_channel(self.scope, execution.route)
        return self.bridge.store.prepare(execution, scope=self.scope.binding_document(),
                                         clearance=clearance, now=now)
