"""Load through actual Core discovery; the probe supplies its explicit hub."""
from alive_native_completion_probe_bus import hub


def register(ctx):
    hub.install(ctx)
    ctx.on_unload(hub.close)
