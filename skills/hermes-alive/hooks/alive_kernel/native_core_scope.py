"""Explicit per-cycle Core scope; no profile discovery or credential resolver."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from .native_worker_protocol import NativeWorkerError


@asynccontextmanager
async def core_profile_cycle_scope(profile_home):
    """Refresh one already-bound host profile using Core's own scope loaders.

    The embedding host supplies the authorized home. Never enter a different
    profile from this callback; a startup task cannot borrow a foreign context.
    Core owns dotenv/external-source/env precedence and credential parsing.
    """
    from hermes_constants import get_hermes_home,get_routing_process_hermes_home
    from agent.secret_scope import current_secret_scope_home
    from gateway.run import _profile_runtime_scope,_async_profile_runtime_scope
    home=Path(profile_home).resolve(strict=True)
    stamp=current_secret_scope_home()
    if (Path(get_hermes_home()).resolve()!=home
            or stamp is not None and Path(stamp).resolve()!=home):
        raise NativeWorkerError('cycle profile differs from current host context')
    if Path(get_routing_process_hermes_home()).resolve()==home:
        from tui_gateway.launch_profile_policy import launch_secret_scope
        # Core's launch loader preserves legitimate host env-only credentials.
        # Read/revalidate off loop; do not turn the startup mapping into a cache.
        secrets=await asyncio.to_thread(launch_secret_scope,home)
        with _profile_runtime_scope(home,prepared_secret_scope=secrets):
            yield
    else:
        async with _async_profile_runtime_scope(home):
            yield
