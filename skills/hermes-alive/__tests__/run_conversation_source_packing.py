"""Whole-source budgeting follows the actual share, without changing read indices."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.conversation_continuity import continuation_context


def test_cited_source_before_background():
    background = {'url': 'https://example.invalid/background', 'title': 'Background',
                  'excerpt': 'background evidence ' * 100, 'reading_status': 'retained_excerpt',
                  'linked_in_share':False}
    cited = {'url': 'https://example.invalid/result', 'title': 'Actual result',
             'excerpt': 'direct evidence ' * 100, 'reading_status': 'retained_excerpt',
             'linked_in_share':True}
    for sources in ([background, cited], [cited, background]):
        share = {'prepared_at': '2026-01-01T00:00:00+00:00',
                 'text': 'One [reported result](https://example.invalid/result).', 'sources': sources}
        original = json.dumps(share)
        # Room for either complete excerpt, but not both.
        context = continuation_context([share], max_chars=4000)
        packed = json.loads(context.split('\n', 1)[1])['alive_shares'][0]
        assert len(context) <= 4000 and packed['text'] == share['text']
        assert [s['url'] for s in packed['sources_linked_in_share']] == [cited['url']]
        assert [s['url'] for s in packed['background_sources']] == [background['url']]
        combined = packed['sources_linked_in_share'] + packed['background_sources']
        assert [s['source_index'] for s in combined] == [sources.index(cited), sources.index(background)]
        by_url = {s['url']: s for s in combined}
        assert by_url[cited['url']]['excerpt'] == cited['excerpt']
        assert by_url[background['url']]['excerpt_in_context'] is False
        assert by_url[cited['url']]['linked_in_share'] is True
        assert by_url[background['url']]['linked_in_share'] is False
        full=json.loads(continuation_context([share]).split('\n',1)[1])['alive_shares'][0]
        assert [s['url'] for s in full['sources_linked_in_share']] == [cited['url']]
        assert [s['url'] for s in full['background_sources']] == [background['url']]
        assert json.dumps(share) == original


def test_catalog_pressure_and_whole_excerpt():
    sources = [{'url': 'https://example.invalid/background', 'title': 'B' * 2000,
                'excerpt': 'Background', 'reading_status': 'retained_excerpt'},
               {'url': 'https://example.invalid/result', 'title': 'Result',
                'excerpt': 'R' * 8000, 'reading_status': 'retained_excerpt'}]
    share = {'prepared_at': '2026-01-01T00:00:00+00:00',
             'text': '[Result][r]\n\n[r]: https://example.invalid/result', 'sources': sources}
    context = continuation_context([share], max_chars=2000)
    packed = json.loads(context.split('\n', 1)[1])['alive_shares'][0]
    assert len(context) <= 2000
    assert not packed['background_sources']
    cited, = packed['sources_linked_in_share']
    assert cited['source_index'] == 1
    assert cited['url'] == sources[1]['url']
    assert cited['excerpt_in_context'] is False
    assert 'excerpt' not in cited  # Never silently truncate it.


def test_real_replay_shape_keeps_document_identity():
    urls = ['https://example.invalid/archive', 'https://example.invalid/news',
            'https://example.invalid/release']
    text = 'Here is the [release](' + urls[2] + ').'
    # A directory and a clipped news extract preceded the actual citation in
    # the failed replay. A stale flag must not put either in the citation group.
    share = {'text': text, 'reference': 'ar_replay',
             'sources': [{'url': url, 'linked_in_share': index == 0,
                          'excerpt': 'Page fragment', 'reading_status': 'retained_excerpt'}
                         for index, url in enumerate(urls)]}
    projected = continuation_context([share], inline_source_excerpts=False)
    result = json.loads(projected.split('\n', 1)[1])['alive_shares'][0]
    assert result['text'] == text
    assert [(s['source_index'], s['url']) for s in result['sources_linked_in_share']] == [(2, urls[2])]
    assert [(s['source_index'], s['url']) for s in result['background_sources']] == list(enumerate(urls[:2]))
    assert all('excerpt' not in s for s in result['sources_linked_in_share'] + result['background_sources'])


if __name__ == '__main__':
    test_cited_source_before_background()
    test_catalog_pressure_and_whole_excerpt()
    test_real_replay_shape_keeps_document_identity()
    print('CONVERSATION_SOURCE_PACKING_OK')
