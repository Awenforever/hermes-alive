"""Owner-selected local hours for proactive adapter submissions."""
from collections.abc import Mapping
from datetime import datetime, time, timedelta
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
    if 'adaptive_contact' in options:
        # Import is separately confirmed. The runtime gate must remain closed
        # until the adaptive projection owns this checkpoint.
        return None, True
    if 'quiet_window' not in options:
        return None, legacy_preview(legacy_path, environ)['state'] != 'absent'
    saved = options['quiet_window']
    return (quiet_window(saved) if saved is not None else None), False


def contact_status(options, legacy_path, environ, at):
    """Describe the timing gate only. Other authority and delivery checks are separate."""
    window, choice_required = configured_window(options, legacy_path, environ)
    if 'adaptive_contact' in options:
        return {'state': 'adaptive_staged', 'window': None,
                'timezone': options['adaptive_contact']['config']['timezone']}
    if choice_required:
        return {'state': 'choice_required', 'window': None}
    if window is None:
        return {'state': 'unrestricted', 'window': None}
    return {'state': 'open' if open_for_contact(window, at) else 'quiet',
            'window': dict(options['quiet_window'])}


def validate_adaptive_import(document):
    """Validate the bounded document passed from the installed timing engine."""
    if (not isinstance(document, dict) or set(document) != {
            'version', 'captured_at', 'source_digest', 'config', 'checkpoint'}
            or type(document['version']) is not int or document['version'] != 1
            or not isinstance(document['source_digest'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', document['source_digest'])):
        raise ValueError('invalid adaptive contact import identity')
    captured = document['captured_at']
    if (not isinstance(captured, str) or len(captured) > 40
            or datetime.fromisoformat(captured).utcoffset() != timedelta(0)):
        raise ValueError('adaptive contact import needs a UTC capture time')
    config, checkpoint = document['config'], document['checkpoint']
    if (not isinstance(config, dict) or config.get('enabled') is not True or config.get('mode') != 'live'
            or not isinstance(config.get('timezone'), str) or len(config['timezone']) > 128
            or any(type(value) not in (str, bool, int, float) for value in config.values())
            or not isinstance(checkpoint, dict) or set(checkpoint) != {
                'schema_version', 'phase', 'schedule_date', 'planned_sleep_at', 'planned_wake_at',
                'actual_sleep_at', 'actual_wake_at', 'pending_sleep_at', 'last_transition_message',
                'learned_sleep_offset_minutes', 'learned_wake_offset_minutes', 'sleep_debt_minutes'}
            or type(checkpoint['schema_version']) is not int or checkpoint['schema_version'] != 1
            or any(value is not None and type(value) not in (str, int) for value in checkpoint.values())
            or len(json.dumps(document, allow_nan=False)) > 8192):
        raise ValueError('invalid adaptive contact import snapshot')
    try:
        ZoneInfo(config['timezone'])
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError('invalid adaptive contact time zone') from exc


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
    enabled = values.get('circadian_enabled')
    if enabled is None:
        enabled = environ.get('HERMES_ALIVE_CIRCADIAN_ENABLED', 'true')
    mode = values.get('circadian_mode')
    if mode is None:
        mode = environ.get('HERMES_ALIVE_CIRCADIAN_MODE')
    dynamic = str(enabled).strip().lower() not in ('0', 'false', 'no', 'off') and str(mode).strip().lower() == 'live'
    if start is None and end is None and not dynamic:
        return {'state': 'absent'}
    window = {'start': start or '00:30', 'end': end or '08:30',
              'timezone': setting('circadian_timezone', 'HERMES_ALIVE_CIRCADIAN_TIMEZONE')
                  or setting('timezone', 'TZ') or 'Asia/Singapore'}
    try:
        quiet_window(window)
    except ValueError:
        if dynamic:
            return {'state': 'dynamic', 'window': None}
        return {'state': 'invalid'}
    return {'state': 'dynamic' if dynamic else 'fixed', 'window': window}
