"""Hermes-native `/memory alive ...` control surface for retention consent."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from .content_vault import ContentVault
from .consolidation import ConsolidationPolicyProjection, ConsolidationValidationError
from .event_store import ExperienceJournal
from .events import Sensitivity
from .memory import (
    MemoryProjection,
    MemoryReview,
    MemoryState,
    MemoryValidationError,
    ProjectionDecisionKind,
)
from .privacy import LocalIdentityProtector
from .retention import (
    RetentionDirection,
    RetentionProjection,
    RetentionValidationError,
)
from .semantic_rendering import MeaningStore, SemanticAtomKind


USAGE = (
    "Alive 记忆与内容控制：\n"
    "- `/memory alive status`\n"
    "- `/memory alive retain on [1-365天] [inbound|outbound|both]`\n"
    "- `/memory alive retain off`（停止新增，不删除既有内容）\n"
    "- `/memory alive learn on|off`（是否允许模型提出长期记忆）\n"
    "- `/memory alive proposals`（查看待审记忆）\n"
    "- `/memory alive accept <id>` 或 `/memory alive reject <id>`\n"
    "- `/memory alive retract <id>`（撤回已接受记忆）\n"
    "- `/memory alive message <meaning-event-id>`（查看主动消息依据）\n"
    "- `/memory alive withdraw-message <meaning-event-id>`（撤回待用消息内容）\n"
    "- `/memory alive correct-message <meaning-event-id> <atom-id> <kind>` 后换行输入修正内容\n"
    "- `/memory alive forget`（擦除该用户的 Alive 加密内容）"
)


def _runtime(shared_dir: str | Path) -> tuple[
    LocalIdentityProtector, RetentionProjection, ConsolidationPolicyProjection, MemoryProjection
]:
    kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
    protector = LocalIdentityProtector(kernel_dir / "identity.key")
    journal = ExperienceJournal(kernel_dir / "experience.sqlite3")
    vault = ContentVault(
        kernel_dir / "content-vault", backup_root=kernel_dir / "content-backups"
    )
    return (
        protector,
        RetentionProjection(journal, content_vault=vault),
        ConsolidationPolicyProjection(journal),
        MemoryProjection(journal, content_vault=vault),
    )


def _subject(
    context: Mapping[str, Any], protector: LocalIdentityProtector
) -> str | None:
    return protector.pseudonym("user", context.get("user_id"))


def _policy_message(
    projection: RetentionProjection,
    learning: ConsolidationPolicyProjection,
    subject: str,
) -> str:
    policy = projection.policy(subject)
    learning_policy = learning.policy(subject)
    learning_state = "已授权（仅生成待审提案）" if learning_policy and learning_policy.enabled else "未授权（默认关闭）"
    if policy is None:
        return (
            "Alive 长期内容保留：**未授权（默认关闭）**。\n\n"
            f"Alive 模型记忆学习：**{learning_state}**。\n\n"
            "当前只记录匿名化结构事件，不保存消息或回复正文。"
            "即使开启学习，没有获准保留的证据也不能产生记忆提案。\n\n" + USAGE
        )
    directions = ", ".join(sorted(value.value for value in policy.directions))
    state = "已开启" if policy.enabled else "已关闭"
    return (
        f"Alive 长期内容保留：**{state}**\n\n"
        f"- 范围：`{directions}`\n"
        f"- 保留：`{policy.retention_days}` 天\n"
        f"- 级别：`{policy.sensitivity.value}`\n"
        f"- 授权事件：`{policy.consent_event_id}`\n\n"
        f"Alive 模型记忆学习：**{learning_state}**。\n\n"
        + USAGE
    )


def _proposals_message(memory: MemoryProjection, subject: str) -> str:
    records = memory.retrieve(
        subject=subject,
        states=(MemoryState.PROPOSED,),
        clearance=Sensitivity.RESTRICTED,
        limit=10,
    )
    if not records:
        return "当前没有可用的待审记忆提案。"
    lines = ["Alive 待审记忆（最多显示 10 条）："]
    for record in records:
        rendered = json.dumps(record.value, ensure_ascii=False, separators=(",", ":"))
        if len(rendered) > 240:
            rendered = rendered[:237] + "…"
        lines.append(
            f"- `{record.memory_id}` · `{record.kind.value}` · "
            f"`{record.predicate}`：{rendered}"
        )
    lines.append("\n使用 `/memory alive accept <id>` 或 `/memory alive reject <id>`。")
    return "\n".join(lines)


def handle_memory_command(
    shared_dir: str | Path, context: Mapping[str, Any] | None
) -> dict[str, str] | None:
    """Handle only the `alive` namespace; leave normal `/memory` untouched."""

    values = context if isinstance(context, Mapping) else {}
    raw_args = str(values.get("args") or values.get("raw_args") or "").strip()
    tokens = raw_args.split()
    if not tokens or tokens[0].lower() != "alive":
        return None
    protector, projection, learning, memory = _runtime(shared_dir)
    subject = _subject(values, protector)
    if subject is None:
        return {
            "decision": "handled",
            "message": "无法确认当前 Hermes 用户身份，未更改 Alive 内容保留设置。",
        }
    action = tokens[1].lower() if len(tokens) > 1 else "status"
    try:
        if action in {"status", "show"}:
            message = _policy_message(projection, learning, subject)
        elif action == "retain":
            mode = tokens[2].lower() if len(tokens) > 2 else ""
            current = projection.policy(subject)
            if mode == "off":
                days = current.retention_days if current else 30
                directions = current.directions if current else frozenset(
                    {RetentionDirection.INBOUND, RetentionDirection.OUTBOUND}
                )
                record = projection.append_consent(
                    subject=subject, enabled=False, retention_days=days,
                    directions=directions,
                    sensitivity=current.sensitivity if current else Sensitivity.RESTRICTED,
                    actor=subject,
                )
                projection.apply(record)
                message = (
                    "已停止新增 Alive 消息/回复正文。既有加密内容会按原期限保留；"
                    "如需立即擦除，请发送 `/memory alive forget`。"
                )
            elif mode == "on":
                try:
                    days = int(tokens[3]) if len(tokens) > 3 else 30
                except ValueError as exc:
                    raise RetentionValidationError("保留天数必须是 1 到 365 的整数") from exc
                scope = tokens[4].lower() if len(tokens) > 4 else "both"
                direction_map = {
                    "inbound": {RetentionDirection.INBOUND},
                    "outbound": {RetentionDirection.OUTBOUND},
                    "both": {RetentionDirection.INBOUND, RetentionDirection.OUTBOUND},
                }
                if scope not in direction_map:
                    raise RetentionValidationError("范围必须是 inbound、outbound 或 both")
                record = projection.append_consent(
                    subject=subject, enabled=True, retention_days=days,
                    directions=direction_map[scope], sensitivity=Sensitivity.RESTRICTED,
                    actor=subject,
                )
                projection.apply(record)
                message = (
                    "已明确授权 Alive 保留加密正文："
                    f"`{scope}`，`{days}` 天。工具参数与结果仍不会被保留。"
                )
            else:
                message = USAGE
        elif action == "learn":
            mode = tokens[2].lower() if len(tokens) > 2 else ""
            if mode not in {"on", "off"}:
                message = USAGE
            else:
                record = learning.append_consent(
                    subject=subject, actor=subject, enabled=mode == "on"
                )
                learning.apply(record)
                if mode == "on":
                    retention = projection.policy(subject)
                    suffix = (
                        " 已保留的合格证据可用于生成待审提案；任何提案都不会自动生效。"
                        if retention and retention.enabled
                        else " 目前内容保留未开启，因此仍没有正文证据可供学习。"
                    )
                    message = "已授权 Alive 提出长期记忆候选。" + suffix
                else:
                    message = "已停止 Alive 生成新的模型记忆提案；既有待审或已接受记忆不变。"
        elif action == "proposals":
            message = _proposals_message(memory, subject)
        elif action in {"message", "withdraw-message", "correct-message"}:
            header, separator, body = raw_args.partition("\n")
            correction_tokens = header.split()
            invalid_correction = action == "correct-message" and (
                len(correction_tokens) != 5 or not separator or not body.strip()
            )
            if invalid_correction or (action != "correct-message" and len(tokens) != 3):
                message = USAGE
            else:
                meanings = MeaningStore(
                    projection.journal, content_vault=projection.content_vault,
                    protector=protector,
                )
                if action == "correct-message":
                    corrected = meanings.correct_atom(
                        correction_tokens[2], subject=subject, actor=subject,
                        atom_id=correction_tokens[3], kind=SemanticAtomKind(correction_tokens[4]),
                        text=body,
                    )
                    message = (
                        f"已修正该消息内容，新版本：`{corrected.event.event_id}`。"
                        "旧版本不再可用；新版本仍需重新决策和审阅，不会自动发送。"
                    )
                elif action == "withdraw-message":
                    meanings.retract(tokens[2], subject=subject, actor=subject)
                    message = (
                        "已撤回该消息内容，相关表达与审阅结果不再可用。"
                        "已经送达的消息不会因此从接收端删除。"
                    )
                else:
                    document = meanings.inspect_for_user(tokens[2], subject=subject)
                    lines = [f"Alive 消息依据：`{tokens[2]}`",
                             f"有效期至：`{document.expires_at.isoformat()}`"]
                    for atom in document.atoms:
                        lines.append(f"\n`{atom.atom_id}` · {atom.kind.value}：{atom.text}")
                        lines.append("依据事件：" + ", ".join(atom.evidence_event_ids))
                    lines.append("\n这些是定义的消息内容及其引用，引用本身不证明事实正确。")
                    message = "\n".join(lines)
        elif action in {"accept", "reject", "retract"}:
            if len(tokens) != 3:
                message = USAGE
            else:
                review = {
                    "accept": MemoryReview.ACCEPT,
                    "reject": MemoryReview.REJECT,
                    "retract": MemoryReview.RETRACT,
                }[action]
                record = memory.append_review(
                    tokens[2], review=review, subject=subject, actor=subject
                )
                decision = memory.apply(record)
                if decision.decision is ProjectionDecisionKind.REJECTED:
                    message = f"未更改记忆：`{decision.reason}`。"
                else:
                    labels = {"accept": "已接受", "reject": "已拒绝", "retract": "已撤回"}
                    message = f"{labels[action]}记忆 `{tokens[2]}`。"
        elif action == "forget":
            request = projection.append_erasure_request(
                subject=subject, actor=subject
            )
            memory.forget_subject(
                subject,
                actor=subject,
                request_id=request.event.event_id,
            )
            result, _completion = projection.execute_erasure(request)
            message = (
                "Alive 内容擦除已完成："
                f"请求 `{result.requested}` 项，新擦除 `{result.newly_erased}` 项，"
                f"受管备份清理 `{result.managed_backups_removed}` 份。"
                "保留授权状态未改变；如需停止新增，请再发送 "
                "`/memory alive retain off`。"
            )
        else:
            message = USAGE
    except (
        ConsolidationValidationError,
        MemoryValidationError,
        RetentionValidationError,
        ValueError,
    ) as error:
        message = f"未更改设置：{error}\n\n{USAGE}"
    return {"decision": "handled", "message": message}


def resume_retention_maintenance(shared_dir: str | Path) -> dict[str, int]:
    """Resume erasure/expiry even when the decision kernel shadow is paused."""

    kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
    if not (kernel_dir / "experience.sqlite3").is_file():
        return {"erasures_resumed": 0, "expired_erased": 0}
    _protector, projection, _learning, _memory = _runtime(shared_dir)
    resumed = projection.resume_pending_erasures()
    # A crash after the durable erasure/forget event but before projection must
    # converge on startup: content is erased and logical memories are retracted.
    _memory.project_new()
    expired = projection.content_vault.erase_expired(now=datetime.now(timezone.utc))
    return {
        "erasures_resumed": resumed,
        "expired_erased": expired.newly_erased,
    }
