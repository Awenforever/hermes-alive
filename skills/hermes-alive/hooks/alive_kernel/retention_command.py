"""Hermes-native `/memory alive ...` control surface for retention consent."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .content_vault import ContentVault
from .event_store import ExperienceJournal
from .events import Sensitivity
from .privacy import LocalIdentityProtector
from .retention import (
    RetentionDirection,
    RetentionProjection,
    RetentionValidationError,
)


USAGE = (
    "Alive 内容保留控制：\n"
    "- `/memory alive status`\n"
    "- `/memory alive retain on [1-365天] [inbound|outbound|both]`\n"
    "- `/memory alive retain off`（停止新增，不删除既有内容）\n"
    "- `/memory alive forget`（擦除该用户的 Alive 加密内容）"
)


def _runtime(shared_dir: str | Path) -> tuple[
    LocalIdentityProtector, RetentionProjection
]:
    kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
    protector = LocalIdentityProtector(kernel_dir / "identity.key")
    journal = ExperienceJournal(kernel_dir / "experience.sqlite3")
    vault = ContentVault(
        kernel_dir / "content-vault", backup_root=kernel_dir / "content-backups"
    )
    return protector, RetentionProjection(journal, content_vault=vault)


def _subject(
    context: Mapping[str, Any], protector: LocalIdentityProtector
) -> str | None:
    return protector.pseudonym("user", context.get("user_id"))


def _policy_message(projection: RetentionProjection, subject: str) -> str:
    policy = projection.policy(subject)
    if policy is None:
        return (
            "Alive 长期内容保留：**未授权（默认关闭）**。\n\n"
            "当前只记录匿名化结构事件，不保存消息或回复正文。\n\n" + USAGE
        )
    directions = ", ".join(sorted(value.value for value in policy.directions))
    state = "已开启" if policy.enabled else "已关闭"
    return (
        f"Alive 长期内容保留：**{state}**\n\n"
        f"- 范围：`{directions}`\n"
        f"- 保留：`{policy.retention_days}` 天\n"
        f"- 级别：`{policy.sensitivity.value}`\n"
        f"- 授权事件：`{policy.consent_event_id}`\n\n"
        + USAGE
    )


def handle_memory_command(
    shared_dir: str | Path, context: Mapping[str, Any] | None
) -> dict[str, str] | None:
    """Handle only the `alive` namespace; leave normal `/memory` untouched."""

    values = context if isinstance(context, Mapping) else {}
    raw_args = str(values.get("args") or values.get("raw_args") or "").strip()
    tokens = raw_args.split()
    if not tokens or tokens[0].lower() != "alive":
        return None
    protector, projection = _runtime(shared_dir)
    subject = _subject(values, protector)
    if subject is None:
        return {
            "decision": "handled",
            "message": "无法确认当前 Hermes 用户身份，未更改 Alive 内容保留设置。",
        }
    action = tokens[1].lower() if len(tokens) > 1 else "status"
    try:
        if action in {"status", "show"}:
            message = _policy_message(projection, subject)
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
        elif action == "forget":
            request = projection.append_erasure_request(
                subject=subject, actor=subject
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
    except (RetentionValidationError, ValueError) as error:
        message = f"未更改设置：{error}\n\n{USAGE}"
    return {"decision": "handled", "message": message}


def resume_retention_maintenance(shared_dir: str | Path) -> dict[str, int]:
    """Resume erasure/expiry even when the decision kernel shadow is paused."""

    kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
    if not (kernel_dir / "experience.sqlite3").is_file():
        return {"erasures_resumed": 0, "expired_erased": 0}
    _protector, projection = _runtime(shared_dir)
    resumed = projection.resume_pending_erasures()
    expired = projection.content_vault.erase_expired(now=datetime.now(timezone.utc))
    return {
        "erasures_resumed": resumed,
        "expired_erased": expired.newly_erased,
    }
