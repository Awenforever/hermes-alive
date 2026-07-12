# Runtime Policies

## Activity and interruption

A normal proactive-social message requires an idle session, a safe last-speaker
state, sufficient conversation silence, cooldown eligibility, and an
interruption-policy decision that permits the intended message class.

Interruption policy ranges from silent through ambient and proactive to a
bounded emotional mode. It does not send by itself; it constrains composition
and delivery.

## Sleep and quiet time

The Circadian engine tracks preferred sleep/wake time, winding down, drowsiness,
sleep, light sleep, forced awake, sleep debt, oversleep, and recovery. Learning
is deliberately slow and bounded so one late night cannot permanently rewrite
the schedule.

Outside isolated acceptance, fixed quiet hours remain authoritative and dynamic
sleep is observe-only. Hard-exempt classes remain allowed:

- system errors;
- service and security alerts;
- control commands;
- explicit reminders;
- Email Watchdog notifications;
- business-critical notifications.

## User silence and affect

Silence may create a human-like negative reaction, but only as a bounded affect
pulse:

- probabilistic rather than guaranteed;
- mild intensity;
- at most once per silence episode;
- rapidly decaying;
- disabled for debug, audit, script execution, and production operations;
- never followed by repeated escalation from the same silence event.

When the unanswered budget is exhausted, the recommended action is silence.

## Message novelty

The quality governor audits:

- exact repeats and semantic near-duplicates;
- repeated opener, presence-companion, task-status, poke, sulk, and
  disappearance-affect families;
- speech-act and topic cooldowns;
- task-status claims without fresh structured evidence;
- repeated affect from one silence episode;
- weather wording that fabricates a robot location or bodily experience.

A rejected shadow candidate is still delivered outside isolated acceptance; the
decision is observability only.

## Style and emoji

Emoji has no global numeric hard cap. It should be used only when it fits the
sentence, relationship, and context. Decorative stacking and repetitive use are
avoided. Debug, audit, production-operation, and serious contexts usually use
fewer emoji.

Content sharing must identify what the item is, why it is relevant or unusual,
and include a source link when available. Internal content references are
validated against the current discovery list before they can select a rich
payload.

## Interest learning

Interest updates are attributable, bounded to reversible weights, and do not
infer sensitive identity traits.

- Explicit positive/negative feedback creates the strongest update.
- Requests for details or a link create a mild positive update.
- One unanswered proactive message is not negative feedback.
- Repeated ignored content may create one small negative update only when the
  delivery is recent, newer than the user's last reply, and attributable to the
  same item/topic.
- Generic phrases are not treated as content feedback without evidence.

## Weather perspective

Allowed weather language provides facts, care, or light commentary, for example:

- “接下来一周好像都有雨。”
- “下午可能有雷暴，晚点出门记得带伞。”
- “怎么又下雨了。”

The bot must not claim a physical location or bodily sensation, such as “我这儿
在下雨” or “闷得我喘不过气”.
