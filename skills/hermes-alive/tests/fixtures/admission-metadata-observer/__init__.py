from dataclasses import asdict
import json
from hermes_constants import get_hermes_home
from .cache import AdmissionMetadataCache

cache = AdmissionMetadataCache()


def before(**values):
    cache.remember(values['event'])
    if values['event'].text == 'synthetic-rewrite':
        return {'action':'rewrite', 'text':'synthetic rewritten by fixture'}
    return None


def after(**values):
    metadata = cache.take(values)
    with (get_hermes_home() / 'synthetic-metadata.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps(asdict(metadata) if metadata is not None else None) + '\n')
    return None


def register(ctx):
    ctx.register_hook('pre_gateway_dispatch', before)
    ctx.register_hook('post_gateway_admission', after)
