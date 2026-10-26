# Experimental kernel configuration guide

Development branch only. This guide describes configuration choices; it does
not establish live functionality, migration, fleet or production acceptance.
The stable README must be aligned with the final engine before release.

## Guide the owner before staging setup

Use Hermes' existing profile, models, authentication and channels. Do not copy
the developer's interests, provider names, addresses or schedule. Ask which
authorized conversation should receive proactive contact; the one-time `/alive confirm`
command must be used in that actual conversation. Configuration does not enable
sending. Installation, guided configuration and `/alive enable` are distinct.

Model selection defaults to inheriting Hermes' main and fallback chain. A custom
selection names an existing Hermes model. Alive does not configure API keys or
install its own provider router.

Interests are optional soft preferences, with room for unfamiliar discoveries.
Ask about language and communication preferences without inventing shared
history. No developer research topic is a recommended default. Public search
topics are a separate choice: explain that those strings will be disclosed to
Hermes' configured search service. Private profile and chat text do not become
public queries automatically.

## Enable without a content feed

Public queries are optional. An owner may configure and confirm the native
kernel without `--public-query` or public-read consent. It uses the same agenda,
policy, decision and authorized channel path; an empty agenda remains quiet.
Existing admitted commitments do not need public search to become eligible.
This does not imply that ordinary chat has already been admitted as commitments,
or that all tool-action and long-term-memory integrations are complete.

Alive's role is continuous attentive assistance: remember the reason for pending
work, respond to changes and outcomes, make useful contact or stay quiet, and
carry context into subsequent conversation. Content discovery is an optional
input to that loop. Proactive contact should be a short natural contribution;
requested reports or detailed work may need a different level of detail.

## Continuing items from conversation

The target normal experience is one guided authorization, followed by direct
acceptance of clearly assigned follow-up work; ask only for unclear intentions.
An optional per-item confirmation mode remains available. As of 2026-10-26 the
implementation below is the conservative confirmation foundation; the first-grant
intake mode is still development work. Do not tell an owner it is already active.

After confirmed kernel setup, Hermes can use `alive_agenda` to propose an ongoing
item in the configured conversation. It shows the task, constraints, any explicit
dates, retention period and a `/alive agenda accept <handle>` command. The
proposal is temporary and not yet a saved obligation; use the exact command to
save it. `/alive agenda preview <handle>` shows the exact pending content.
Handles expire after ten minutes or a Gateway reload/session reset.

`/alive agenda list` shows at most eight retained items, not a complete inventory.
`/alive agenda done <item-id>` marks a known item complete; `cancel <item-id>`
ends it without claiming completion. Saving an item never grants external tool
execution or sending authority. It also does not enable Alive: the separate
`/alive enable` authorization still controls proactive work. No entire incoming
chat is retained by creating a temporary proposal. Interpretation remains the
main agent's responsibility; long-term adaptation and all action kinds have not
been qualified merely by installing these commands.

## Explain the public reading choices

| Choice | Installation flags | Scope |
|---|---|---|
| Initial public discovery | `--public-query "owner-selected public topic" --confirm-public-reads` | Search approved strings and read selected public results |
| Read actual citations too | Add `--confirm-cited-reads` | One bounded followup group, at most two actual cited targets |
| Refine public evidence too | Also add `--confirm-public-refinement` | The followup may instead perform one source-only public query and read at most two selected results |

Refinement requires the preceding public/cited-read choices. It is default off;
an earlier citation grant does not imply it. The citation and query paths share
one followup budget rather than opening a recursive crawl. The query planner
receives public material and already-public queries, excluding private profile,
conversation and inquiry bodies. This does not promise zero indirect information
about which public topics were selected.

Present the actual confirmation summary before giving the confirmation command.
It includes the model choice, approved topics, optional refinement and retention
choices. Do not hide a new reading scope behind a routine plugin upgrade.

## Keep memory and retention choices separate

Confirm retention of Alive's outbound share/source context and its duration.
This is separate from Hermes' own conversation history. It does not grant
inbound chat collection, automatic profile learning or external-provider recall.

`--confirm-hermes-profile-memory` separately permits current Core-curated USER
advice for the confirmed private conversation. It does not import it as an
explicit personal fact or authorize reading unrelated conversations. Disabling,
updating or deleting the Core profile affects subsequent reads; forgetting
retains its existing precedence. External-provider and ordinary feedback
integration remain open work.

## Verify the actual state

After scope confirmation, check that state remains configured but inactive.
The authorized `/alive enable` command starts the selected installed engine;
`/alive pause` prevents new proactive work. Already-submitted transport work is
owned by Hermes and, for Weixin, Enhance. Installing hooks, an empty error list
or a successful setup is not proof that a useful share was delivered.

Preserve existing state and key identity across update/uninstall/reinstall.
Incomplete or unknown state is a recovery condition, not permission to create
replacement keys or silently fall back to the legacy sender. Production
updates, restarts and real sends still require the concrete authorized window.
