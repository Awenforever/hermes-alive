import json
from hermes_constants import get_hermes_home

def observe(**kwargs):
    with (get_hermes_home() / 'fixture-admissions.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps(kwargs, ensure_ascii=False) + '\n')
    if kwargs['text'] == 'fixture-fail':
        raise RuntimeError('synthetic observer failure')
    if kwargs['text'] == 'fixture-handle':
        return {'action':'handled', 'reply':'synthetic acknowledgement'}
    return None

def register(ctx):
    ctx.register_hook('post_gateway_admission', observe)
