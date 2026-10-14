#!/usr/bin/env python3
"""Synthetic cache semantics, not actual authorization or platform attribution."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.admission_metadata import AdmissionMetadataCache


def event(message='m1', profile='profile-a', bot=False, text='synthetic body'):
    snapshot = {'platform':'telegram', 'user_id':'u1', 'chat_id':'c1', 'thread_id':None, 'profile':profile}
    source = SimpleNamespace(is_bot=bot, to_dict=lambda:snapshot)
    return SimpleNamespace(source=source, message_id=message, text=text,
                           reply_to_message_id='outbound-1', reply_to_is_own_message=True)


def values(item):
    return {'platform':'telegram', 'source':item.source.to_dict(), 'message_id':item.message_id,
            'text':item.text}


def main():
    now = [0.0]
    cache = AdmissionMetadataCache(capacity=2, ttl_seconds=10, clock=lambda:now[0])
    first = event()
    cache.remember(first)
    assert b'synthetic body' not in repr(cache._entries).encode()
    assert b'profile-a' not in repr(cache._entries).encode()
    metadata = cache.take(values(first))
    assert metadata.is_bot is False and metadata.quoted_message_id == 'outbound-1'
    assert metadata.quote_is_own_message is True
    assert cache.take(values(first)) is None
    cache.remember(first)
    assert cache.take(values(first)) is None
    cache.clear()
    cache.remember(first)
    changed = event(bot=True); changed.reply_to_message_id = 'outbound-2'
    cache.remember(changed)
    assert cache.take(values(first)) is None
    cache.clear()
    cache.remember(first)
    assert cache.take(values(event(profile='profile-b'))) is None
    assert cache.take(values(first)) is not None
    cache.clear()
    cache.remember(first)
    assert cache.take(values(event(text='rewritten body'))) is None
    assert cache.take(values(first)) is None
    cache.clear()
    cache.remember(first)
    now[0] = 10
    assert cache.take(values(first)) is None
    assert cache.pending_count() == 0
    now[0] = 0
    cache.remember(first); cache.remember(event('m2')); cache.remember(event('m3'))
    assert cache.pending_count() == 2 and cache.take(values(first)) is None
    cache.clear()
    cache.remember(first)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = tuple(pool.map(lambda _:cache.take(values(first)), range(2)))
    assert sum(item is not None for item in replies) == 1
    cache.clear()
    missing = event(message=None)
    cache.remember(missing)
    assert cache.pending_count() == 0
    # A forged bool-shaped value is not a typed author/quote flag.
    unknown = event(bot='false'); unknown.reply_to_is_own_message = 1
    cache.remember(unknown)
    value = cache.take(values(unknown))
    assert value.is_bot is None and value.quote_is_own_message is None
    cache.clear()
    assert cache.pending_count() == 0
    print('HERMES_ALIVE_ADMISSION_METADATA_CACHE_OK')


if __name__ == '__main__':
    main()
