# Experimental kernel configuration guide

Development branch only. This guide describes configuration choices; it does
not establish live functionality, migration, fleet or production acceptance.
The stable README must be aligned with the final engine before release.

## Guide the owner before staging setup

Use Hermes' existing profile, models, authentication and channels. Do not copy
the developer's interests, provider names, addresses or schedule. Ask which
authorized conversation should receive shares; the one-time `/alive confirm`
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
