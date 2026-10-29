"""Whole-source budgeting follows the actual share, without changing read indices."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.conversation_continuity import continuation_context


def test_cited_source_before_background():
    background = {'url': 'https://example.invalid/background', 'title': 'Background',
                  'excerpt': 'background evidence ' * 100, 'reading_status': 'retained_excerpt'}
    cited = {'url': 'https://example.invalid/result', 'title': 'Actual result',
             'excerpt': 'direct evidence ' * 100, 'reading_status': 'retained_excerpt'}
    for sources in ([background, cited], [cited, background]):
        share = {'prepared_at': '2026-01-01T00:00:00+00:00',
                 'text': 'One [reported result](https://example.invalid/result).', 'sources': sources}
        original = json.dumps(share)
        # Room for either complete excerpt, but not both.
        context = continuation_context([share], max_chars=4000)
        packed = json.loads(context.split('\n', 1)[1])['alive_shares'][0]
        assert len(context) <= 4000 and packed['text'] == share['text']
        assert [s['url'] for s in packed['sources']] == [s['url'] for s in sources]
        assert [s['source_index'] for s in packed['sources']] == [0, 1]
        by_url = {s['url']: s for s in packed['sources']}
        assert by_url[cited['url']]['excerpt'] == cited['excerpt']
        assert by_url[background['url']]['excerpt_in_context'] is False
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
    assert len(packed['sources']) == 1
    assert packed['sources'][0]['source_index'] == 1
    assert packed['sources'][0]['url'] == sources[1]['url']
    assert packed['sources'][0]['excerpt_in_context'] is False
    assert 'excerpt' not in packed['sources'][0]  # Never silently truncate it.


if __name__ == '__main__':
    test_cited_source_before_background()
    test_catalog_pressure_and_whole_excerpt()
    print('CONVERSATION_SOURCE_PACKING_OK')
