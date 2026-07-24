# Runtime Policies

## Activity and interruption

A proactive-social message requires an idle-enough session, a safe
last-speaker/activity state, cooldown eligibility, and an interruption decision
that permits the message class. Activity and context are rechecked before each
send.

Interruption policy does not send by itself. It returns a bounded disposition,
semantic-act preferences, and a bubble upper bound. Bubble count is selected from
1–5 according to independent semantic needs; the default is the fewest bubbles
that express the message completely.

## Sleep and quiet time

The Circadian engine tracks planned and observed sleep/wake behavior, winding
down, sleep phases, forced awake state, sleep debt, oversleep, and recovery.
Learning is slow and bounded.

Current live behavior:

- fixed quiet hours remain authoritative;
- Circadian is `shadow`;
- dynamic Sleep/Quiet integration is `observe_only`;
- hard-exempt system, security, control, reminder, Email Watchdog, and
  business-critical classes remain outside social sleep gates.

The dual-key isolated guard is for acceptance testing, not production status.

## Unanswered interaction evidence

`ignored_proactive_count` is a raw observation derived from delivered proactive
messages newer than the latest user reply. It is not a normal fixed toggle and
must not be manually reset in state files.

The disposition model combines:

- unanswered pressure derived from interaction evidence;
- relationship temperature and reply quality;
- current flow and focus lock;
- mood and voice profile;
- cooldown and user activity;
- whether a genuinely new Discovery item is available.

Ordinary inbound messages are new evidence, not a mechanical “clear all” event.
A hard upper safety ceiling prevents endless persistence, but normal behavior is
not defined by “two messages means permanent silent mode”.

When Hermes chooses to speak after non-response, it must not continue the old
prompt. It may only offer an independently valuable new topic, usually with a
smaller bubble budget. Repeated pressure, disappearance accusations, and
unsupported task-state claims are rejected.

## Proactive quality governor

Managed modes:

- `off`: no quality audit enforcement;
- `shadow`: audit and log without changing delivery;
- `enforce`: filter rejected candidates before delivery and commit only
  successfully delivered, allowed candidates.

Lifecycle default is `enforce`.

The governor checks:

- exact repeats and semantic near-duplicates;
- repeated opener and speech-act families;
- repeated affect from one silence episode;
- task-state claims without fresh structured evidence;
- stale topic continuation;
- weather wording that fabricates robot location or bodily experience;
- missing or mismatched audit evidence.

## Discovery novelty

A collection cache may be read across several watcher ticks. Each read removes
delivered, reserved, and duplicate topic units from the eligible view without
mutating the full cached batch. One successful share commits one topic. Failed
sends release reservations. Exhausted caches stay silent.

## Style and emoji

Emoji has no global numeric hard cap. It is used only when it fits the sentence,
relationship, and context. Decorative stacking and repetitive emoji are avoided.
Debug, audit, production-operation, and serious contexts normally use fewer.

Content sharing identifies what the item is, why it is relevant or unusual, and
includes a source link when available. Unknown content references are ignored.

## Interest learning

Interest updates are attributable, bounded, and reversible.

- Explicit positive/negative feedback creates the strongest update.
- Requests for details or a source create a mild positive update.
- One unanswered proactive message is not negative feedback.
- Repeated ignored content can create a small negative update only when delivery
  is recent, newer than the last user reply, and attributable to the same topic.
- Generic phrases are not treated as content feedback without evidence.
- Sensitive identity traits are not inferred.

## Weather perspective

Allowed wording provides facts, care, or light commentary. It must not claim that
the bot physically occupies a location or experiences bodily weather effects.
Weather stays disabled until a location profile is confirmed and contains usable
coordinates.
