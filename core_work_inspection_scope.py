"""A composition of existing Core tools for future owned-work inspection.

This registers no handler, executes nothing and grants no operation. Core keeps
its dispatch, global disabled-tool subtraction, job permissions and approvals.
"""

NAME = 'alive_core_inspection_read_v1'
TOOLS = frozenset(('read_file',))


def register(context):
    # Actual supported Core contexts expose this public job identity capability.
    # Lightweight observer-only test contexts do not install job compositions.
    if not callable(getattr(context,'current_cron_execution',None)):
        return False
    from toolsets import create_custom_toolset, get_toolset, resolve_toolset
    previous=get_toolset(NAME)
    if previous is None:
        create_custom_toolset(NAME,'Read an existing file for owned-work inspection',tools=sorted(TOOLS))
    definition=get_toolset(NAME)
    if (set(definition.get('tools',()))!=TOOLS or definition.get('includes')
            or set(resolve_toolset(NAME))!=TOOLS):
        raise ValueError('Core inspection composition conflicts with another registration')
    return True


def effective_tools():
    """Inspect the real cron selection; never bypass disabled tools or MCP scope."""
    from hermes_cli.config import load_config_readonly
    from cron.scheduler import _resolve_cron_enabled_toolsets, _resolve_cron_disabled_toolsets
    from model_tools import get_tool_definitions
    from toolsets import resolve_toolset
    if set(resolve_toolset(NAME))!=TOOLS:
        raise ValueError('Core inspection composition is missing or changed')
    configuration=load_config_readonly()
    names=_resolve_cron_enabled_toolsets({'enabled_toolsets':[NAME,'no_mcp']},configuration)
    if set(names)!={NAME}:raise ValueError('Core inspection tool scope expanded')
    definitions=get_tool_definitions(enabled_toolsets=names,
        disabled_toolsets=_resolve_cron_disabled_toolsets(configuration),
        quiet_mode=True)
    actual=frozenset(d.get('function',d)['name'] for d in definitions)
    if not actual<=TOOLS:raise ValueError('Core inspection tool scope expanded')
    return actual
