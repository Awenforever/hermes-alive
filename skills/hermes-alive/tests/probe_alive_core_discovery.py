"""Actual Core scoped dispatch -> encrypted discovery; controlled tools, no IO."""
import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import threading
from unittest.mock import patch

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,mode=0o700,exist_ok=False)
home=a.output/'profile';home.mkdir(mode=0o700)
os.environ['HERMES_HOME']=str(home)
sys.path[:0]=[str(a.core.resolve(strict=True)),str(Path(__file__).resolve().parents[1]/'hooks')]


async def main():
    from hermes_cli.plugins import PluginContext,PluginManifest,PluginManager
    from alive_kernel import ExperienceJournal,DiscoveryOpportunityIngestor
    from alive_kernel.core_discovery_tools import CoreDiscoveryTools
    from alive_kernel.host_discovery import HostDiscoveryReader,HostReadUncertainError
    from tools.registry import registry
    # Controlled handlers, actual Core's sync and async dispatch bridging.
    manager=PluginManager(scope_key=str(home))
    context=PluginContext(PluginManifest(name='alive-discovery-probe'),manager)
    calls=[];held=threading.Event();release=threading.Event()
    def search(args):
        calls.append('search')
        if args['query']=='HELD_PUBLIC_QUERY':
            held.set()
            assert release.wait(5),'fixture did not release physical read'
            return json.dumps(dict(success=True,data=dict(web=[])))
        assert args==dict(query='APPROVED_PUBLIC_QUERY',limit=1)
        return json.dumps(dict(success=True,data=dict(web=[dict(title='PUBLIC_TITLE',
            url='https://public.invalid/article',description='PUBLIC_DESCRIPTION')])))
    async def extract(args):
        calls.append('extract')
        await asyncio.sleep(.001)
        assert args==dict(urls=['https://public.invalid/article'],char_limit=6000)
        return json.dumps(dict(results=[dict(title='PUBLIC_TITLE',url=args['urls'][0],
            content='PUBLIC_SOURCE_BODY')]))
    for name,handler,is_async in (('web_search',search,False),('web_extract',extract,True)):
        assert registry.get_entry(name,scope=manager.scope_key) is None
        assert context.register_tool(name,'synthetic-discovery',dict(name=name),handler,is_async=is_async)
    tools=CoreDiscoveryTools(context,read_binding=lambda:'owner:revision1',
        approved_queries=('APPROVED_PUBLIC_QUERY',))
    journal=ExperienceJournal(home/'plugin-data/hermes-alive/runtime/kernel/experience.sqlite3')
    reader=HostDiscoveryReader(DiscoveryOpportunityIngestor(journal),subject='user:synthetic',
        search=tools.search,extract=tools.extract,allow_url=tools.allow_url,is_current=lambda:True)
    async def public_only(url):return url=='https://public.invalid/article'
    # Only DNS safety is synthetic; call Core's real URL secret/shape validation.
    with patch('tools.url_safety.async_is_safe_url',public_only):
        assert not await tools.allow_url('https://public.invalid/?key=sk-'+ 'x'*48)
        assert not await tools.allow_url('http://127.0.0.1/')
        params=dict(operation_id='actual-core-controlled',queries=('APPROVED_PUBLIC_QUERY',),
            read_urls=('https://public.invalid/article',),limit=1)
        result=await reader.collect(**params)
        assert len(result.observation_ids)==2 and result.failures==0
        assert await reader.collect(**params)==result
        assert calls==['search','extract']
    uncertain_tools=CoreDiscoveryTools(context,read_binding=lambda:'owner:revision1',
        approved_queries=('HELD_PUBLIC_QUERY',),timeout_seconds=.03)
    uncertain=HostDiscoveryReader(reader.ingestor,subject=reader.subject,
        search=uncertain_tools.search,extract=uncertain_tools.extract,
        allow_url=uncertain_tools.allow_url,is_current=lambda:True)
    completed=len(journal.read(event_type='discovery.host_read_completed'))
    try:
        try:await uncertain.collect(operation_id='physical-pending',queries=('HELD_PUBLIC_QUERY',),limit=1)
        except HostReadUncertainError:pass
        else:raise AssertionError('pending physical read treated as completed failure')
        assert held.is_set() and uncertain_tools.pending
        assert len(journal.read(event_type='discovery.host_read_completed'))==completed
    finally:release.set()
    assert (await uncertain_tools.reap_pending(timeout_seconds=2))['remaining']==0
    await tools.reap_pending()
    tools.close()
    for path in home.rglob('experience.sqlite3*'):
        raw=path.read_bytes()
        for value in (b'APPROVED_PUBLIC_QUERY',b'PUBLIC_SOURCE_BODY',b'PUBLIC_DESCRIPTION'):
            assert value not in raw
    report=dict(result=asdict(result),actual_core_dispatch=True,
        actual_network=False,controlled_tools=True,model_calls=0,sends=0,
        query_approval_checked=True,encrypted_request_and_observations=True,
        replay_physical_reads=0,production_changed=False,
        pending_read_never_marked_completed=True,
        automatic_discovery_or_quality_qualified=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('HERMES_ALIVE_ACTUAL_CORE_DISCOVERY_OK')


asyncio.run(main())
