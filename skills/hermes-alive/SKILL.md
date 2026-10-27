---
name: hermes-alive
description: "Gateway-native proactive companion with contextual discovery, live quality enforcement, production Circadian sleep/quiet enforcement, and reversible lifecycle management."
version: 2.9.8
---

# Hermes Alive — Hermes Installation Contract

## Distribution

Treat the complete GitHub repository as the release unit. `SKILL.md` alone is
not installable. Do not pre-copy source into the final skill or hook directory
before lifecycle installation.

## Preconditions

### Guided kernel configuration (development branch; NOT delivery activation)

This is a prerequisite for replacing shadow/manual host wiring, not a finished
production engine. Do not select it as a silent ordinary-install upgrade or claim
that configuration enables delivery. Preserve existing state and pause an
existing active runtime only after asking the operator. Migration is not automatic.

Explain and obtain separate approval for model calls, proactive delivery, and
saving the exact outbound shares for follow-up. Explain the chosen history
retention (1–365 days), that configuration/recipient metadata stays until removed,
and that inbound-history retention and automatic profile learning are NOT enabled.
Ask whether any public search topics/citation reads are approved; do not insert
the developer's interests or infer externally disclosed searches from private chat.
Model selection defaults to Hermes; only request an optional existing Core alias,
never credentials. Translate ordinary choices into flags for the user.

Before presenting kernel choices, read [the kernel setup guide](docs/ALIVE_KERNEL_SETUP.md).
It owns the distinct ongoing-item, item-management, structural-observation and
native-background-work choices. Do not infer one from another, enable new grants
on upgrade or promise autonomous result followup from a submitted Core task. Separately offer owned-work
record review only after explaining its bounded historical reads, derived-data
retention and pause behavior; use `--confirm-core-work-result-review` only for
that explicit choice. It does not grant fresh inspection or autonomous work. Separately
explain optional `--confirm-core-file-inspection` only for approved automatic
read-only checks of retained owned file targets and Core task retention. Older
grants stay off; do not promise generic autonomous work or goal completion.

Ask whether the recipient wants a particular conversation language or has an
explicit communication preference; "no customization" is valid. Optional
`--language <language-tag>` overrides only Alive's output language; otherwise
Alive follows Hermes' locale, not the source language or an inferred chat profile.
Optional `--communication-preference "<their own words>"` is retained privately
after the target owner confirms, as explicit Alive memory available to discovery
and expression. Explain it remains until updated/forgotten, independently of the
outbound-history retention period. Never invent a preference, copy the developer's
profile or silently convert sample feedback into lasting memory. These choices
grant neither additional actions nor permission to read private chats.

Also offer optional interests in the user's own words (`--interests "<their words>"`).
Leaving them unset is valid and has no developer-supplied recommendation. Explain
that these are soft preferences: valuable discoveries outside them remain welcome.
Keep them separate from approved public search queries; never disclose a private
interest in a search merely because it was saved as memory. Show the exact interest
wording and its independent until-updated-or-forgotten memory lifetime in the
confirmation summary. Only the target owner's confirmation creates explicit
`profile.interests` memory. This does not enable automatic chat learning.

Offer a separate, default-off choice to consult Hermes' existing curated personal
profile. Only if the user confirms that this Hermes profile belongs to them and
allows its curated memory to be processed, add `--confirm-hermes-profile-memory`.
Explain that the current built-in USER profile becomes advisory private context
for the configured models and protected generation records; it is not imported
as a new user-explicit fact or used to construct public searches. Core's standard
loader can read both curated memory files; this feature exposes only its user
profile, and does not initialize or recall an external memory provider. It does
not harvest chat transcripts. The target must be a private conversation; decline
this choice for groups and shared profiles. Leaving it off is fully valid.
Changes or deletions in Core are re-read rather than restored from an Alive cache.
Core can disable its user profile independently. A subject-forget in Alive blocks
the old read grant and does not delete Core's separately owned memory; any later
opt-in requires a new owner confirmation. Do not infer this permission from an
interest, a sharing grant or outbound-history retention.

After approval, stage configuration with the confirmed values:

```text
hermes alive setup --confirm-model-calls --confirm-delivery --confirm-outbound-retention --retention-days <approved-days>
```

Only when separately approved, add `--public-query "<approved text>"` (up to three)
with `--confirm-public-reads`, and optionally `--confirm-cited-reads`. For an
intentional replacement, explain that old data/grants remain separate before
using `--replace`. Show the returned confirmation_summary in the user's language,
then give that user the one-time `/alive confirm ...` command. Never persist its
actual code in shared docs/logs or send it to another user's conversation.
Show the actual staged language, exact communication/interest wording and its memory
lifecycle BEFORE asking for confirmation. Do not replace it with "configured" or
hide a developer-supplied preference behind the code. The summary is private to
this intended owner; do not copy it into shared operational logs.
The target user confirms in the intended authorized Hermes conversation; do not
ask for internal subject IDs. If Core has no existing session, ask for one ordinary
message first and retry within the 15-minute window. A changed/expired code needs
explicit new setup, not guessed routing. Installing the kernel hook and restarting
still need the operator's normal lifecycle approval.

Status must say `configured_not_activated` after confirmation. Exact share-reader
attachment and native execution/supervision are implemented for development
validation. Activation is a separate `/alive enable` command in the confirmed
authorized conversation; the installation CLI's `enable` refuses to substitute
for that owner command. `/alive pause` revokes active sharing and `/alive status`
reports the actual host state. This development engine has not completed content,
migration, fleet or production qualification: do not silently switch an existing
installation to it, enable it for a user or restart their gateway as part of setup.
Do not edit installed flags or start a legacy sender to bypass those boundaries.

### Experimental kernel shadow mode (development branch only)

Do not silently select this mode for ordinary installs or turn it into delivery.
When an operator explicitly requests kernel shadow validation, explain that it
uses the configured model but cannot send messages. Ask for approval of model
calls and a bounded duration/cycle count. Use the current already-authorized
Hermes conversation user ID as `--user-id`; never ask the user to invent an
internal subject ID or copy another account's identity. In CLI-only installation,
ask which existing authorized user is intended if it cannot be determined.

After confirmation, run these commands with the resolved values:

```text
hermes alive kernel-setup --user-id <current-authorized-id> --confirm-model-calls --max-cycles <approved-count>
hermes alive install-runtime --engine kernel-shadow
```

Public discovery requires separate permission. Model-call consent alone does
not authorize web searches or disclosure of private profile/chat content. Explain
what public topics will be searched and obtain approval of one to three public
search phrases. Convert the user's ordinary-language choices into those phrases;
do not ask them to design flags. Never derive or expand externally disclosed
queries from private memory without separate approval. With confirmed scope,
add repeated `--public-query "<approved public search>"` and
`--confirm-public-reads` to the same `kernel-setup` command above. This authorizes
only those exact searches and bounded reading of selected public results, not
delivery. Each cycle may read at most two selected result pages. Explain the
optional cited-source follow-up separately: after approval add
`--confirm-cited-reads`, allowing one model-decided reading of at most two unread
URLs actually cited in those retained extracts. Old configurations without this
additional confirmation do not gain it on upgrade. No recursive crawl or
additional search is authorized.
The follow-up decision receives only the public extracts, not the user's profile
or the private research question. A citation is not a verification certificate.
Without both phrases and confirmation, setup does not enable reads.
Hermes still owns search availability, URL safety and tool/provider setup; report
missing prerequisites rather than installing a second search backend. The model
may choose not to read/share; a topic match is not a required message.

Do not request keys or
create a plugin model configuration: the Core auxiliary task
`hermes_alive_kernel` owns routing/auth/fallback. An optional model alias remains
subject to Core's override permission. Restart only with operator approval.
Uninstall/reinstall preserves configuration/state and the chosen engine. A
configuration/installation PASS is not live model or recommendation acceptance.
Generic403 switching and all API completion modes are not yet qualified; retain
those limitations and do not publish this experimental mode as production-ready.

Before installation:

1. confirm Hermes is installed and `HERMES_HOME` is writable;
2. confirm Hermes has a usable Provider/model;
3. never request API keys, timezone syntax, coordinates, or internal feature
   flags from the user; infer technical values from Hermes and the OS;
4. do not modify Hermes Core, `weixin.py`, production configuration, or gateway
   state as part of installation.

Provider setup remains owned by Hermes. If readiness fails, report the missing
prerequisite and stop; do not launch a second skill-specific Provider flow.

## Guided personalization

Before enabling a fresh installation, guide the user in the current chat. This
is part of installation, not optional documentation. Ask one compact natural
language question at a time and accept “use recommended defaults”. Establish:

1. which already-paired chat should receive proactive messages;
2. the user's city/district if local weather or local discovery is wanted;
3. approximate sleep/wake or do-not-disturb preferences;
4. preferred content mix and whether proactive sharing should be conservative,
   balanced, or lively.

Do not make the user translate preferences into flags. Convert their answers
to lifecycle arguments, summarize the resulting behavior, then ask for a final
confirmation before enabling and restarting Gateway. Never send a test message
without explicit approval. If the user accepts defaults, inherit Hermes' active
model, current paired chat and system timezone; use balanced discovery,
contextual emoji, dynamic sleep protection, and weather disabled until a
location is confirmed.

## Paths

Use lifecycle defaults unless the environment explicitly supplies safe paths:

```text
source: $HERMES_HOME/skills/hermes-alive
hook:   $HERMES_HOME/hooks/hermes-alive
state:  $HERMES_HOME/plugin-data/hermes-alive/runtime
```

The shared directory must be a strict child of `HERMES_HOME`.

## Install

Install or refresh the complete repository through Hermes' package manager so
its declared cryptographic runtime is resolved in the same Python environment
as Gateway:

```bash
hermes plugins install Awenforever/hermes-alive --force --yes-deps --enable
hermes alive install-runtime
```

Do not replace this with a raw `git pull` or an unrelated system `pip`; Hermes'
plugin manager owns dependency consent and environment selection. From an
already package-managed repository checkout, the lifecycle implementation is:

```bash
bash scripts/install.sh
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_INSTALL_OK
```

Run the command a second time to verify idempotence. On failure, stop and surface
the lifecycle error; never report success from partial output.

On upgrade, use the same `plugins install --force --yes-deps --enable` command
rather than plain `plugins update`: the latter reports newly declared Python
dependencies but does not install them. Existing runtime state remains outside
the plugin checkout and must be preserved.

Package placement is not dependency admission. Hermes may print an installed
banner while refusing enablement after a dependency failure. Before running
`install-runtime`, require `hermes alive status` to succeed and identify the
intended profile. If Hermes reports dependency/enablement refusal, stop; do not
restart Gateway or describe the plugin as installed and working. Let Hermes
resolve its own environment, then retry. Never substitute system `pip`, disable
security scanning or alter production model/provider settings to get past it.

## Configure

Default non-interactive configuration:

```bash
scripts/hermes-alive-lifecycle configure \
  --non-interactive \
  --enable \
  --skip-weather
```

Require:

```text
HERMES_ALIVE_MANAGED_CONFIG_OK
HERMES_ALIVE_ZERO_TOUCH_CONFIG_OK
provider_ready=true
```

Default managed behavior:

```text
quality_governor_mode=enforce
quality_topic_expiry_after_unanswered=1
quality_silence_after_unanswered=2
context_flow_max_age_seconds=3600
circadian_mode=live
legacy fixed quiet hours=23:00–08:00 (comparison/rollback fallback)
```

Quality enforcement is live when the managed environment exports `enforce`.
Circadian `live` makes dynamic sleep/quiet authoritative for proactive-social
delivery: protected sleep phases block before composition, dynamic awake state
may supersede the legacy fixed quiet window, and invalid live state fails
closed. `shadow` remains an explicit observe-only rollback mode. The dual-key
isolated delivery enforcement guard remains test-only and must not be represented
as the production path.

Weather is optional. Without confirmed location, keep it disabled. When
network-assisted discovery was explicitly requested, Hermes may ask one natural
question in the existing chat to confirm, correct, or decline the suggested
district/county-level area. Never block installation waiting for that reply.
Forward geocoding uses Open-Meteo first and Nominatim as an independent
fallback. Failure of either or both providers must not block installation or
fabricate coordinates; keep weather disabled and allow correction later. An
explicit `latitude, longitude` answer is accepted as an offline escape hatch,
but installers must not require users to provide coordinates.

## Verify

```bash
bash scripts/verify.sh
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_VERIFY_RESULT=PASS
```

Verification must check source and active-hook parity, compilation, manifest,
managed configuration, Provider readiness, and safe permissions.

## Runtime controls

From the installed skill root:

```bash
scripts/hermes-alive-lifecycle status
python3 hooks/alive_control.py status
python3 hooks/alive_control.py disable
python3 hooks/alive_control.py enable
python3 scripts/logs.py --tail 20
```

`alive_control.py test` queues a real delivery request. Do not run it without
explicit approval to send a real message.

Do not manually edit runtime JSON to reset unanswered state. The raw ignored
count is evidence, not a fixed on/off switch.

## Uninstall

Preserve learning/runtime state:

```bash
bash scripts/uninstall.sh
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_UNINSTALL_OK
shared_state_preserved=true
```

Remove all Hermes Alive-owned shared state:

```bash
bash scripts/uninstall.sh --purge
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_PURGE_OK
shared_state_preserved=false
```

`purge` is destructive.

## Safety and release gates

- Never modify Hermes Core or `weixin.py`.
- Never modify or restart production without explicit approval.
- Never send real WeChat messages without explicit approval.
- A failed `SendResult` is not a delivery.
- Model-authored messages must retain the routed model in footer metadata.
- Run complete regression, fresh-container lifecycle, persistence, uninstall,
  reinstall, and purge gates before repository release.
- Isolated acceptance is not final production completion.
- Complete repository transport, real GitHub URL installation, spare-WeChat E2E,
  controlled production deployment, restart persistence, and stability
  observation remain separate gates.

When offering ongoing-task autonomy, guide the automatic operation scope first.
Separately offer the default-off autonomous first-work option; never enable it
implicitly for an old installation. Preserve original instructions to wait for
further confirmation. Explain original-request retention in Core's local work
record. Operations outside scope need confirmation. A running/completed Core job
is not proof that an agenda item has succeeded.

Offer automatic outcome management separately from direct item intake and automatic
work. Explain that Alive may close an attained owned goal from actual results,
keeps uncertainty active, and permits an explicit owner correction to reopen it.
This choice grants no new tool execution or notification. Never enable it for an
old installation implicitly.
