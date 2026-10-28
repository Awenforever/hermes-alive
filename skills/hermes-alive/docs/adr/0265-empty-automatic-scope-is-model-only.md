# ADR 0265 — An explicit empty scope permits no tools, not no reasoning

Status: bounded actual-Core zero-tool and cold-process qualification passed.
Date: 2026-10-28.

Guidance allows an empty automatic Core toolset as model-only work. CoreWorkStore
already resolves an explicit empty list through Core and refuses any widening.
However, autonomous source discovery rejected that scope before asking the model,
and decision validation required a nonempty execute list. An owner could authorize
model-only work in guidance but never have it considered. This is a contradictory
capability contract, not a reason to silently enable file or terminal access.

Remove the two nonempty restrictions. Execute still requires a bounded nonempty
step, current source and owner scope, no blocked continuation history, and no wait
timer. Every proposed toolset remains a subset of the confirmed scope. Wait still
has no tools or step. Explain in the decision interface that execute with [] is
model-only; needing a tool outside scope still requires an owner decision.

Continue using Core's resolver, paused native job, exact-definition checks and
activation path. Core must preserve enabled_toolsets=[] through storage and the
actual worker request. No plugin-owned reasoning executor, scheduler, fallback,
implicit MCP access or new authorization is added. Old autonomous-work guidance
and source-retention requirements still apply; an empty scope is not a grant.

Qualify actual installed-Core execution against a controlled provider: retain an
authorized arithmetic explanation task, submit one native job, inspect its empty
toolsets and actual worker request with no tools, and read its result through the
owned Core evidence reader. No artifact or outward message may appear. Include
explicit owner wait, disabled autonomous grant and an out-of-scope tool proposal;
cold reading must preserve the same observations. Separately retain ordinary
file-scope/continuation controls. These are scope/lifecycle tests, not evidence of
real model arithmetic competence or broad autonomous reasoning.

r265 passed four actual-Core zero-scope cases and cold checks: model-only execute,
explicit wait, out-of-scope proposal and autonomous grant off. It also passed
three ordinary file-scope/cold controls: execute, continuation and wait. The
zero-scope worker's actual HTTP request carries no tools, its native job retains
enabled_toolsets=[], and the owned evidence reader returns the explanation
without tool calls. No artifact or outward send occurs. The original process
exited 0; container die 0/destroy/actual absence and clean Core supplier were
independently verified before reading reports. The controlled provider supplies
the arithmetic text, so this is not a real-model competence claim.
