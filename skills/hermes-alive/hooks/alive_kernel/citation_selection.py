"""Bounded source-text references; never URL repair or network authorization."""
import re
from urllib.parse import urlsplit

from .discovery_opportunities import canonicalize_discovery_url
from .host_discovery import HostDiscoveryError


METHOD = 'cited-public-followup-v2'
# Conservative URI runs, not a general hyperlink parser. Preserve punctuation
# inside a run exactly, including a possible sentence-ending period. Structured
# hyperlinks are not supplied by the current Core extract capability. Ambiguous
# text cannot justify silently editing a fetch target.
_RUN = re.compile(r'https?://[^\s<>\"\'\[\]{}]+')
_BOUNDARIES = ' \t\r\n<>\"\'()[]{}'
LIMIT = 32


def citations(excerpt, visited=()):
    seen = {canonicalize_discovery_url(url) for url in visited}
    result = []
    for match in _RUN.finditer(excerpt):
        if match.start() and excerpt[match.start()-1] not in _BOUNDARIES:
            continue
        raw = match.group()
        # A parenthesized link can contain balanced parentheses in its path.
        # Never manufacture a shorter endpoint by splitting a path at '('.
        end = match.end()
        if match.start() and excerpt[match.start()-1] == '(':
            depth = 0
            for index, character in enumerate(raw):
                if character == '(':
                    depth += 1
                elif character == ')':
                    if depth == 0:
                        raw = raw[:index]
                        end = match.start()+index
                        break
                    depth -= 1
            else:
                continue  # Incomplete enclosing syntax: no guessed endpoint.
        elif '(' in raw or ')' in raw:
            continue  # Bare ambiguous framing is unavailable, never truncated.
        try:
            parts = urlsplit(raw)
            identity = canonicalize_discovery_url(raw)
            if parts.username is not None or parts.password is not None:
                continue
        except (TypeError, ValueError):
            continue
        if identity in seen:
            continue
        seen.add(identity)
        result.append(dict(citation_ref='link'+str(len(result)+1), url=raw,
            start=match.start(), end=end))
        if len(result) == LIMIT:
            break
    return result


def _target(raw, catalogs):
    if (not isinstance(raw, dict) or set(raw) != {'source_ref', 'citation_ref'}
            or not isinstance(raw['source_ref'], str)
            or not isinstance(raw['citation_ref'], str)):
        return None
    source = catalogs.get(raw['source_ref'], ())
    return next((item for item in source if item['citation_ref'] == raw['citation_ref']), None)


def normalize(raw, catalogs):
    """One unusable optional choice does not destroy other available evidence.

    Counts describe the model decision, not completed reads. Nothing here catches
    consent changes, stale sources, transport uncertainty or provider exceptions.
    """
    if (not isinstance(raw, dict) or set(raw) != {'read_targets', 'reason'}
            or not isinstance(raw['read_targets'], list) or len(raw['read_targets']) > 2
            or not isinstance(raw['reason'], str) or not 1 <= len(raw['reason'].strip()) <= 1200):
        return dict(read_targets=[], reason='Optional source selection was unusable.',
            rejected_count=1, decision_status='invalid')
    valid = []
    seen = set()
    rejected = 0
    for target in raw['read_targets']:
        link = _target(target, catalogs)
        identity = canonicalize_discovery_url(link['url']) if link else None
        if link is None or identity in seen:
            rejected += 1
            continue
        seen.add(identity)
        valid.append(dict(target))
    return dict(read_targets=valid, reason=raw['reason'], rejected_count=rejected,
        decision_status='selected' if valid else 'invalid' if rejected else 'abstained')


def validate(value, catalogs):
    """Reopen the retained exact choice, never retroactively repair a decision."""
    if (not isinstance(value, dict)
            or set(value) != {'read_targets','reason','rejected_count','decision_status'}
            or type(value['rejected_count']) is not int or not 0 <= value['rejected_count'] <= 2):
        raise HostDiscoveryError('invalid retained citation selection')
    checked = normalize(dict(read_targets=value['read_targets'], reason=value['reason']), catalogs)
    if (checked['rejected_count'] or checked['read_targets'] != value['read_targets']
            or checked['reason'] != value['reason']
            or len(value['read_targets'])+value['rejected_count'] > 2
            or value['decision_status'] != ('selected' if value['read_targets'] else
                'invalid' if value['rejected_count'] else 'abstained')):
        raise HostDiscoveryError('retained citation selection changed or lost its source')
    return value


def read_targets(value, catalogs):
    validate(value, catalogs)
    return tuple(dict(source_ref=target['source_ref'], url=_target(target, catalogs)['url'])
        for target in value['read_targets'])
