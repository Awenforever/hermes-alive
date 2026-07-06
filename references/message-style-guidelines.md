# Message Style Guidelines for Hermes Alive

User feedback from 2026-07-05 session on Alive's message quality.

## Discovery References

**Problem**: LLM drops cryptic references like "福特那事让我笑了半天" without context. User has no idea what "福特那事" is — they didn't see the discovery content.

**Rule**: When referencing discovery content:

1. **Summarize first, then comment**: "我刚看到福特一个专利说电动车充电口能识别用户喜好，好怪的设计" — NOT "福特那事"

2. **Tease/sell it**: "我给你讲个笑话吧" — then either wait or continue. "我看到一个东西想吐槽……"

3. **Never assume shared knowledge**: The discovery content is NOT in the user's context. They haven't seen what you've seen.

4. **If it doesn't come naturally, let it go**: If you're actively searching discovery for a topic, skip it. It only works when it genuinely pops into your head.

## Multi-Message Burst

Real people sometimes send 2-3 messages in quick succession. Alive should too:

```
哎…
刚看到福特那事
笑死我了哈哈
```

Implementation: LLM uses `---` separator, watcher sends with 2-5s delay. Most of the time, one message is enough.

## Context Awareness

- Recent conversation (<5min): Alive should be likely to continue the thread
- Medium recency (5-60min): May reference if relevant
- Old conversation (1-3h): Vague recollection only
- Stale (>3h): Don't reference at all

This prevents Alive from interrupting active coding sessions with unrelated chatter while allowing natural thread continuation.

## Cooldown Intelligence (Future)

Current cooldown (120min) is purely time-based. Known limitation:
- No awareness of user activity level
- No distinction between "we were just chatting" and "nothing for hours"
- Dream consolidation is time-scheduled, not experience-accumulated

Future direction: experience-based triggers (voice delta, discovery volume, interaction recency) rather than fixed timers.
