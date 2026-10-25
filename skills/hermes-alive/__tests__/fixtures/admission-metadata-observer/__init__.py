from dataclasses import asdict
import json
import os
from hermes_constants import get_hermes_home
from .cache import AdmissionMetadataCache, TaskAdmissionMetadataHandoff

task_mode = os.environ.get('HERMES_ALIVE_TEST_METADATA_MODE') == 'task'
cache = TaskAdmissionMetadataHandoff() if task_mode else AdmissionMetadataCache()


def before(**values):
    if task_mode:
        cache.remember(values['event'], runtime_home=values['gateway']._resolve_profile_home_for_source(values['event'].source))
    else:
        cache.remember(values['event'])
    if values['event'].text == 'synthetic-rewrite':
        return {'action':'rewrite', 'text':'synthetic rewritten by fixture'}
    return None


def after(**values):
    metadata = cache.take(values, runtime_home=get_hermes_home()) if task_mode else cache.take(values)
    with (get_hermes_home() / 'synthetic-metadata.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps(asdict(metadata) if metadata is not None else None) + '\n')
    return None


def register(ctx):
    ctx.register_hook('pre_gateway_dispatch', before)
    ctx.register_hook('post_gateway_admission', after)
