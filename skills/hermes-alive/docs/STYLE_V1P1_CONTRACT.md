# Hermes Alive Style V1.1 Contract

Marker: `STYLE_GUARD_PROMPT_AND_POSTPROCESS_V1`

This candidate improves proactive message naturalness without changing scheduler frequency or sending policy.

## Goals

- Reduce repeated “刚……” openers.
- Make punctuation more WeChat-like and less essay-like.
- Allow low-frequency, natural emoji.
- Add light relationship emotion when proactive messages are ignored.
- Keep debug / production workflows non-intrusive by preferring ambient messages.
- Avoid turning Hermes Alive into a news bot or a monitoring panel.

## Safety

- No production modification in candidate build.
- No message sending in candidate build.
- No container restart.
- No install / uninstall.
- No Docker prune or compose down / pull.

## Runtime files read

- `/opt/data/hermes_alive_shared/proactive_log.jsonl`
- `/opt/data/hermes_alive_shared/context_queue.json`
- `/opt/data/hermes_alive_shared/voice_state.json`

The style guard reads these files only. It does not write runtime state.
