# ADR0223 — Configured Core input wake without chat retention

Date: 2026-10-24 (Asia/Shanghai), Codex.
Status: implemented; current-Core qualification in progress.

The ordinary native setup uses a canonical core-v2 owner. The old admitted-input
observer is explicitly gated by a legacy shadow environment flag and uses a
legacy principal. Installing that hook did not connect ordinary chat to the new
host. Existing shadow SDK tests and an output-continuity hook cannot prove input
integration or automatic profile learning.

Bind the configured observer to its actual plugin-generation GatewayHostBinding.
Only explicit native installation, confirmed configuration, activation and current
enabled owner policy qualify. Resolve the live receiving Core route, then compare
the exact configured profile, bot, chat/thread, owner and session key. A normal
discussion reset may change session ID, never the person or receiving realm.
Foreign traffic returns without capture. Unload and paused policy disable capture.
The configured native home fence is applied only to that engine; explicit legacy
shadow observation retains its original environment-gated behavior.

Observe Core's post-admission boundary without returning handled, rewriting text,
calling a model or dispatching anything. Independent consumers retain their own
behavior. Legacy opt-in shadow observation stays separate. No Enhance dependency,
token management, physical FIFO or cross-plugin protocol is introduced.

The current native event is conversation.inbound under the canonical owner but
with system actor, explicitly not a human/user instruction or agent turn. Keep
only keyed normalized-text revision, character count and configuration reference;
never body, chat IDs, file contents or a retention/learning grant. Same normalized
revision replays are idempotent; changed text with the same transport ID can wake
again without making an old revision's replay new work. This is normalized input
observation, not proof of raw-wire message multiplicity or edit metadata.

Current-Core integration must prove this exact event invalidates the host wait
fingerprint, not merely that a hook is installed. It also checks no body persistence,
foreign owner/thread isolation, independent consumer handling, pause and replay.
The fixture invokes the real Core consumer helper on synthetic sources; it does
not claim full Gateway authorization/daemon, real paired transport or fleet proof.
The older pure registration fixture lacked the current register_command API;
it now models that public registration contract and asserts the command exists.
Both legacy tool-receipt and admitted-input privacy tests join portable CI rather
than treating the previous selected suite list as every repository test.

Daily-chat body retention and adaptive memory remain separate explicit product
work. The current setup confirms outbound retention only. Do not borrow that
consent for inbound text or learning, infer quotation targets, or silently promote
this system observation into USER_EXPLICIT memory. No private chat is read by the
development tests or production state changed.
