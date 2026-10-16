"""Only a private worker process supplies this bus; no production global state."""
from _alive_native_worker_bus import hub


def register(ctx):
    hub.install(ctx)
    ctx.on_unload(hub.close)
