"""Owner-selected local hours for proactive adapter submissions."""
from collections.abc import Mapping
from datetime import time
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ContactHoursClosed(ValueError):
    """A new proactive adapter submission cannot start at this time."""


def _clock(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', value):
        raise ValueError('contact hours require 24-hour HH:MM times')
    return time.fromisoformat(value)


def quiet_window(document):
    """Resolve validated civil times, using system or packaged IANA tzdata."""
    if not isinstance(document, Mapping) or set(document) != {'start', 'end', 'timezone'}:
        raise ValueError('a quiet window needs start, end and an IANA time zone')
    start, end = _clock(document['start']), _clock(document['end'])
    if start == end:
        raise ValueError('use the explicit unrestricted contact choice for equal times')
    zone = document['timezone']
    if not isinstance(zone, str) or len(zone) > 128:
        raise ValueError('invalid contact time zone')
    try:
        return start, end, ZoneInfo(zone)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError('invalid contact time zone') from exc


def open_for_contact(window, at):
    if window is None:
        return True
    if at.utcoffset() is None:
        raise ValueError('contact policy requires an absolute current time')
    start, end, zone = window
    local = at.astimezone(zone).time()
    if start < end:
        return not start <= local < end
    return not (local >= start or local < end)


def configured_window(options, legacy_path, environ):
    """Resolve the signed choice, or detect a legacy window needing an owner choice."""
    if 'quiet_window' not in options:
        return None, legacy_preview(legacy_path, environ)['state'] != 'absent'
    saved = options['quiet_window']
    return (quiet_window(saved) if saved is not None else None), False


def contact_status(options, legacy_path, environ, at):
    """Describe the timing gate only. Other authority and delivery checks are separate."""
    window, choice_required = configured_window(options, legacy_path, environ)
    if choice_required:
        return {'state': 'choice_required', 'window': None}
    if window is None:
        return {'state': 'unrestricted', 'window': None}
    return {'state': 'open' if open_for_contact(window, at) else 'quiet',
            'window': dict(options['quiet_window'])}


def legacy_preview(path, environ):
    """Read the fixed legacy inputs without modifying the profile or environment."""
    try:
        raw = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        values = {}
    else:
        try:
            values = json.loads(raw)['values']
        except (KeyError, TypeError, ValueError):
            return {'state': 'invalid'}
        if not isinstance(values, dict):
            return {'state': 'invalid'}
    def setting(key, env):
        return environ.get(env) or values.get(key)

    start = setting('quiet_start', 'HERMES_PROACTIVE_QUIET_START')
    end = setting('quiet_end', 'HERMES_PROACTIVE_QUIET_END')
    enabled = values.get('circadian_enabled', environ.get('HERMES_ALIVE_CIRCADIAN_ENABLED'))
    mode = values.get('circadian_mode', environ.get('HERMES_ALIVE_CIRCADIAN_MODE'))
    dynamic = str(enabled).lower() in ('1', 'true', 'yes', 'on') and mode == 'live'
    if start is None and end is None and not dynamic:
        return {'state': 'absent'}
    window = {'start': start or '00:30', 'end': end or '08:30',
              'timezone': setting('circadian_timezone', 'HERMES_ALIVE_CIRCADIAN_TIMEZONE')
                  or setting('timezone', 'TZ') or 'Asia/Singapore'}
    try:
        quiet_window(window)
    except ValueError:
        return {'state': 'invalid'}
    return {'state': 'dynamic' if dynamic else 'fixed', 'window': window}
