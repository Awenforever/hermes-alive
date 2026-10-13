"""Bounded JSON transport normalization, never semantic repair or schema defaults."""
import json
import math
import re


class ModelJSONError(ValueError):
    pass


def parse_model_json(text, *, max_chars=32000):
    if not isinstance(text, str) or not text.strip() or len(text) > max_chars:
        raise ModelJSONError('model JSON outside text boundary')
    document = text.strip()
    if document.startswith('```'):
        wrapped = re.fullmatch(r'```(?:json)?[ \t]*\r?\n([\s\S]*)\r?\n```', document, re.IGNORECASE)
        if wrapped is None:
            raise ModelJSONError('not one complete JSON code fence')
        document = wrapped.group(1)
    def unique(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ModelJSONError('duplicate model JSON key')
        return value
    def nonfinite(_value):
        raise ModelJSONError('nonfinite model JSON value')
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ModelJSONError('nonfinite model JSON number')
        return parsed
    try:
        value = json.loads(document, object_pairs_hook=unique,
                           parse_constant=nonfinite, parse_float=finite_float)
        pending = [(value, 0)]
        while pending:
            node, depth = pending.pop()
            if depth > 64:
                raise ModelJSONError('model JSON exceeds nesting boundary')
            if isinstance(node, dict):
                pending.extend((child, depth + 1) for child in node.values())
            elif isinstance(node, list):
                pending.extend((child, depth + 1) for child in node)
        return value
    except (ValueError, RecursionError) as error:
        raise ModelJSONError('model response is not strict finite JSON') from error
