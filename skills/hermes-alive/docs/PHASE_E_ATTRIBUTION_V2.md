# Phase E Interest Learning V1.2 Attribution

Markers:
- `INTEREST_LEARNING_IGNORED_ATTRIBUTION_V1`
- `INTEREST_LEARNING_FEEDBACK_PHRASE_V2`

Scope: `hermes-alive-v2-dev` only.

Rules:
1. Repeated ignored messages reduce a topic only when the delivered content is newer than the user's last reply.
2. The delivered content must be no older than 72 hours.
3. One unanswered sequence produces only one small negative update.
4. Generic “不错” and “无聊” are not content feedback.
5. Technical uses of `source` or `link` are not link requests.
6. Specific phrases such as “这篇不错” and “把原文链接发我” remain supported.
