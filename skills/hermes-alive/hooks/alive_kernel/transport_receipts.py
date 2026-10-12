"""Typed CLI reports, deliberately weaker than terminal host receipts.

Even correctly parsed success is a report from a process, not proof of an
external effect, human attention or benefit. Unknown fields are not persisted.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json


class CliReportKind(str, Enum):
    SUCCESS_REPORTED = "success_reported"
    ERROR_REPORTED = "error_reported"
    PARTIAL_REPORTED = "partial_reported"
    SKIP_REPORTED = "skip_reported"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CliReport:
    kind: CliReportKind
    exit_code: int | None
    json_object: bool

    def to_document(self) -> dict:
        return {"report_kind": self.kind.value, "exit_code": self.exit_code,
                "json_object": self.json_object, "external_delivery_proven": False}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(value)


def classify_cli_report(stdout: str, exit_code: int | None) -> CliReport:
    if not isinstance(stdout, str) or len(stdout.encode("utf-8")) > 65536:
        raise ValueError("CLI report must be bounded UTF-8 text")
    # POSIX negative signals and native Windows DWORD crash statuses both
    # belong in the observation; neither is a delivery acknowledgement.
    code = exit_code if type(exit_code) is int and -(2**31) <= exit_code < 2**32 else None
    try:
        payload = json.loads(stdout, object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return CliReport(CliReportKind.UNKNOWN, code, False)
    if not isinstance(payload, dict):
        return CliReport(CliReportKind.UNKNOWN, code, False)
    unknown = CliReport(CliReportKind.UNKNOWN, code, True)
    if code is None:
        return unknown
    for key in ("success", "skipped", "partial_success"):
        if key in payload and type(payload[key]) is not bool:
            return unknown
    error = payload.get("error")
    if error is not None and not isinstance(error, str):
        return unknown
    if payload.get("skipped") is True:
        if code != 0 or error or payload.get("partial_success") is True:
            return unknown
        return CliReport(CliReportKind.SKIP_REPORTED, code, True)
    if payload.get("partial_success") is True:
        return CliReport(CliReportKind.PARTIAL_REPORTED, code, True)
    if error:
        return CliReport(CliReportKind.ERROR_REPORTED, code, True)
    if code == 0 and payload.get("success") is True:
        return CliReport(CliReportKind.SUCCESS_REPORTED, code, True)
    return unknown
